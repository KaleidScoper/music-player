#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 站音频下载器（yt-dlp 版）

把 B 站视频/收藏夹/合集里的音频直接取下来，按播放器要求放到
``music/<歌单>/<标题>/<标题>.<扩展名>``。

特点：
  * 依赖 yt-dlp 与 customtkinter（都是纯 pip 包），不需要 Node.js，也不需要 FFmpeg（m4a 直取）
  * 默认取最高音质（320k，有 Hi-Res 时优先），不像旧脚本固定拿 64k
  * 支持单视频、多 P、收藏夹、合集、视频列表、稍后再看、UP 主空间
  * 按 BV 号记录下载历史，重复执行自动跳过
  * 无参数运行时打开图形界面（CustomTkinter，Windows / macOS / Linux 通用）

用法::

    python download/download.py                    # 打开 GUI
    python download/download.py -p "自用歌单" BV1xx  # 命令行下载
    python download/download.py -p "自用歌单" --list "https://space.bilibili.com/1/favlist?fid=2"
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MUSIC_DIR = (BASE_DIR.parent / "music").resolve()

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".flac", ".aac", ".wav", ".ogg"}
ARCHIVE_NAME = ".bili-archive.txt"
SUBTITLE_LANGS = ("zh-CN", "zh-Hans", "zh-Hant", "zh", "ai-zh", "en", "en-US", "en-GB")
MAX_NAME_LENGTH = 100
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
BROWSERS = ("chrome", "edge", "firefox", "chromium", "brave")

# 音质档位 → yt-dlp 格式选择表达式
# 直接写音轨 id（30251 Hi-Res / 30280 320k / 30232 132k / 30216 64k），
# 不存在时回退到 bestaudio；注意 bestaudio[format_id=...] 这种写法会先选最高再过滤，达不到降档目的。
QUALITY_FORMATS = {
    "auto": "30251/30280/bestaudio",
    "320": "30280/bestaudio",
    "132": "30232/bestaudio",
    "64": "30216/bestaudio",
}
QUALITY_LABELS = {"auto": "自动（最高可用）", "320": "320k", "132": "132k", "64": "64k"}

EVENT = Callable[..., None]

yt_dlp = None
DownloadError = None
DownloadCancelled = None


# ---------------------------------------------------------------------------
# 依赖
# ---------------------------------------------------------------------------

def load_ytdlp() -> bool:
    """导入 yt-dlp，成功返回 True。"""
    global yt_dlp, DownloadError, DownloadCancelled
    if yt_dlp is not None:
        return True
    try:
        import yt_dlp as _yt_dlp
        from yt_dlp.utils import DownloadCancelled as _cancelled
        from yt_dlp.utils import DownloadError as _error
    except ImportError:
        return False
    yt_dlp, DownloadError, DownloadCancelled = _yt_dlp, _error, _cancelled
    return True


def install_packages(packages: Iterable[str], log: Optional[EVENT] = None) -> bool:
    """用当前解释器的 pip 安装依赖。"""
    names = list(packages)
    if not names:
        return True
    if log:
        log(f"正在安装 {'、'.join(names)} ...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *names],
            capture_output=True, text=True, timeout=900,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        if log:
            log(f"安装失败：{exc}")
        return False
    if result.returncode != 0:
        if log:
            log((result.stderr or result.stdout or "").strip()[-800:])
        return False
    if log:
        log("依赖安装完成")
    return True


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# 文本与路径工具
# ---------------------------------------------------------------------------

URL_RE = re.compile(r"https?://[^\s<>\"'）)】，,。]+")
BV_RE = re.compile(r"(?<![0-9A-Za-z])(BV[0-9A-Za-z]{10})(?![0-9A-Za-z])")
AV_RE = re.compile(r"(?<![0-9A-Za-z])[aA][vV](\d{1,12})(?![0-9])")
FAV_RE = re.compile(
    r"(?:space\.bilibili\.com/\d+/favlist\?[^\s]*?\bfid=(?P<fid>\d+)"
    r"|bilibili\.com/medialist/(?:detail|play)/ml(?P<ml>\d+))"
)
ILLEGAL_NAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_name(name: str, fallback: str = "未命名") -> str:
    """把视频标题变成安全的文件夹/文件名（播放器的显示名就是这个）。"""
    cleaned = ILLEGAL_NAME_CHARS.sub("_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if len(cleaned) > MAX_NAME_LENGTH:
        cleaned = cleaned[:MAX_NAME_LENGTH].rstrip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def favorites_fid(url: str) -> Optional[str]:
    match = FAV_RE.search(url)
    if not match:
        return None
    return match.group("fid") or match.group("ml")


def normalize_inputs(text: str) -> List[str]:
    """从任意粘贴文本里提取可用的下载目标（兼容分享文案）。"""
    targets: List[str] = []
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        found = [u.rstrip(".,;:!?，。；：！？、") for u in URL_RE.findall(line)]
        if not found:
            found = [f"https://www.bilibili.com/video/{bvid}" for bvid in BV_RE.findall(line)]
        if not found:
            found = [f"https://www.bilibili.com/video/av{aid}" for aid in AV_RE.findall(line)]
        targets.extend(found)
    # 去重但保持顺序
    seen, ordered = set(), []
    for target in targets:
        if target not in seen:
            seen.add(target)
            ordered.append(target)
    return ordered


def format_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "--:--"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def human_size(size: Optional[int]) -> str:
    if not size:
        return "-"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return "-"


def read_archive(path: Path) -> set:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    return {line.split()[-1] for line in text.splitlines() if line.strip()}


def write_archive(path: Path, bvid: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"bilibili {bvid}\n")
    except OSError:
        pass


def has_audio(directory: Path) -> bool:
    try:
        return any(
            child.is_file() and child.suffix.lower() in AUDIO_EXTENSIONS
            for child in directory.iterdir()
        )
    except OSError:
        return False


def open_in_file_manager(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # noqa: S606 - 桌面环境打开目录
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


def list_playlists(music_dir: Path) -> List[str]:
    try:
        return sorted(
            child.name for child in music_dir.iterdir()
            if child.is_dir() and not child.name.startswith(".")
        )
    except OSError:
        return []


# ---------------------------------------------------------------------------
# B 站收藏夹接口（用于快速拿到标题，失败则退回 yt-dlp 解析）
# ---------------------------------------------------------------------------

def cookie_header_from_file(path: Path) -> str:
    """从 Netscape cookies.txt 里取 bilibili 域的 Cookie 头。"""
    pairs = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    for line in lines:
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7 and "bilibili.com" in parts[0]:
            pairs.append(f"{parts[5]}={parts[6]}")
    return "; ".join(pairs)


def http_json(url: str, cookie_header: str = "") -> Optional[dict]:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
    }
    if cookie_header:
        headers["Cookie"] = cookie_header
    else:
        headers["Cookie"] = f"buvid3={uuid.uuid4()}infoc"
    for attempt in range(3):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 412 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, ValueError, OSError):
            return None
    return None


def fetch_favorites(fid: str, cookie_header: str = "", page_limit: int = 100) -> Optional[List[dict]]:
    """分页取收藏夹条目；失败（私有/风控）返回 None 交给 yt-dlp 处理。"""
    items: List[dict] = []
    for page in range(1, page_limit + 1):
        url = (
            "https://api.bilibili.com/x/v3/fav/resource/list"
            f"?media_id={fid}&pn={page}&ps=20&platform=web&order=mtime&type=0"
        )
        payload = http_json(url, cookie_header)
        if not payload or payload.get("code") != 0:
            return None
        data = payload.get("data") or {}
        for media in data.get("medias") or []:
            if media.get("attr"):  # 已失效稿件
                continue
            bvid = media.get("bvid")
            if not bvid:
                continue
            items.append({
                "bvid": bvid,
                "title": (media.get("title") or "").strip(),
                "duration": media.get("duration"),
            })
        if not data.get("has_more"):
            break
    return items


# ---------------------------------------------------------------------------
# 下载核心
# ---------------------------------------------------------------------------

@dataclass
class Song:
    url: str
    bvid: str = ""
    title: str = ""
    duration: Optional[float] = None
    selected: bool = True
    status: str = "待处理"
    target: str = ""
    index: int = -1


class _Logger:
    """把 yt-dlp 的日志转发到回调；非 verbose 时滤掉解析器闲聊。"""

    def __init__(self, emit: EVENT, verbose: bool = False):
        self._emit = emit
        self._verbose = verbose

    def debug(self, msg):
        if self._verbose and not msg.startswith("[debug] "):
            self._emit("log", message=msg)

    def info(self, msg):
        if self._verbose or not msg.startswith("["):
            self._emit("log", message=msg)

    def warning(self, msg):
        self._emit("log", message=f"警告：{msg}")

    def error(self, msg):
        # 失败会由调用方翻译成可读提示，这里只在 -v 时输出原始信息
        if self._verbose:
            self._emit("log", message=f"错误：{msg}")


class Downloader:
    """把一组 Song 下载到 music/<歌单>/<标题>/ 下。"""

    def __init__(
        self,
        music_dir: Path,
        playlist: str,
        quality: str = "auto",
        audio_format: str = "m4a",
        lrc: bool = False,
        cookies: Optional[Path] = None,
        browser: Optional[str] = None,
        force: bool = False,
        use_archive: bool = True,
        sleep_requests: float = 0.5,
        verbose: bool = False,
        emit: Optional[EVENT] = None,
    ):
        self.music_dir = Path(music_dir)
        self.playlist = sanitize_name(playlist, fallback="新歌单")
        self.playlist_dir = self.music_dir / self.playlist
        self.quality = quality if quality in QUALITY_FORMATS else "auto"
        self.audio_format = "mp3" if audio_format == "mp3" else "m4a"
        self.lrc = bool(lrc)
        self.cookies = Path(cookies) if cookies else None
        self.browser = browser or None
        self.force = bool(force)
        self.use_archive = bool(use_archive)
        self.sleep_requests = max(0.0, float(sleep_requests))
        self.verbose = bool(verbose)
        self.cancel = threading.Event()
        self.archive_path = self.playlist_dir / ARCHIVE_NAME
        self._archive: set = set()
        self._progress_base = 0.0
        self._progress_span = 1.0
        self._emit = emit or (lambda *a, **k: None)
        self._cookie_header = ""

    # -- 事件 -------------------------------------------------------------
    def _log(self, message: str) -> None:
        self._emit("log", message=message)

    # -- 解析 -------------------------------------------------------------
    def plan(self, text_or_urls) -> List[Song]:
        raw = text_or_urls if isinstance(text_or_urls, str) else "\n".join(str(item) for item in text_or_urls)
        targets = normalize_inputs(raw)
        if not targets:
            raise ValueError("没有识别到 B 站链接")
        if self.cookies and self.cookies.exists():
            self._cookie_header = cookie_header_from_file(self.cookies)
        songs: List[Song] = []
        for target in targets:
            fid = favorites_fid(target)
            if fid:
                self._log(f"解析收藏夹 {fid} ...")
                items = fetch_favorites(fid, self._cookie_header)
                if items is not None:
                    self._log(f"收藏夹共 {len(items)} 个稿件")
                    for item in items:
                        songs.append(Song(
                            url=f"https://www.bilibili.com/video/{item['bvid']}",
                            bvid=item["bvid"],
                            title=item["title"] or item["bvid"],
                            duration=item.get("duration"),
                        ))
                    continue
                self._log("收藏夹接口不可用（可能是私有收藏夹），改用 yt-dlp 解析")
            songs.extend(self._plan_with_ytdlp(target))
        # 同一 BV 只保留一次
        seen, unique = set(), []
        for song in songs:
            key = song.bvid or song.url
            if key in seen:
                continue
            seen.add(key)
            unique.append(song)
        return unique

    def _plan_with_ytdlp(self, url: str) -> List[Song]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "logger": _Logger(self._emit, self.verbose),
        }
        if self.cookies and self.cookies.exists():
            opts["cookiefile"] = str(self.cookies)
        if self.browser:
            opts["cookiesfrombrowser"] = (self.browser,)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError(f"无法解析：{url}")
        entries = list(info.get("entries") or []) if info.get("entries") is not None else []
        if not entries:
            bvid = info.get("id") or ""
            return [Song(
                url=info.get("webpage_url") or url,
                bvid=bvid,
                title=info.get("title") or bvid or url,
                duration=info.get("duration"),
            )]
        songs = []
        for entry in entries:
            if not entry:
                continue
            bvid = entry.get("id") or ""
            page_url = entry.get("url") or entry.get("webpage_url") or (
                f"https://www.bilibili.com/video/{bvid}" if bvid else ""
            )
            if not page_url:
                continue
            songs.append(Song(
                url=page_url,
                bvid=bvid,
                title=entry.get("title") or bvid,
                duration=entry.get("duration"),
            ))
        self._log(f"{url} → {len(songs)} 个条目")
        return songs

    # -- 下载 -------------------------------------------------------------
    def _ydl_opts(self, staging: Path) -> dict:
        opts = {
            "format": QUALITY_FORMATS[self.quality],
            "outtmpl": {"default": str(staging / "%(id)s.%(ext)s")},
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "logger": _Logger(self._emit, self.verbose),
            "progress_hooks": [self._progress_hook],
            "retries": 3,
            "fragment_retries": 3,
            "sleep_interval_requests": self.sleep_requests,
            "noplaylist": True,
            "overwrites": True,
            "continuedl": True,
        }
        if self.cookies and self.cookies.exists():
            opts["cookiefile"] = str(self.cookies)
        if self.browser:
            opts["cookiesfrombrowser"] = (self.browser,)
        if self.use_archive and not self.force:
            opts["download_archive"] = str(self.archive_path)
        if self.audio_format == "mp3":
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }]
        if self.lrc:
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = list(SUBTITLE_LANGS)
            opts["subtitlesformat"] = "srt"
        return opts

    def _progress_hook(self, data: dict) -> None:
        if self.cancel.is_set():
            raise DownloadCancelled("已取消")
        if data.get("status") == "downloading":
            self._emit(
                "progress",
                downloaded=data.get("downloaded_bytes") or 0,
                total=data.get("total_bytes") or data.get("total_bytes_estimate") or 0,
                base=self._progress_base,
                span=self._progress_span,
            )

    def download(self, songs: List[Song]) -> List[Song]:
        pending = [song for song in songs if song.selected]
        if not pending:
            return songs
        self.playlist_dir.mkdir(parents=True, exist_ok=True)
        self._archive = read_archive(self.archive_path)
        staging = Path(tempfile.mkdtemp(prefix="bili-audio-"))
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts(staging)) as ydl:
                for index, song in enumerate(pending, 1):
                    if self.cancel.is_set():
                        song.status = "已取消"
                        continue
                    self._progress_base = (index - 1) / len(pending)
                    self._progress_span = 1 / len(pending)
                    self._emit("item", song=song, progress=(index - 1) / len(pending))
                    try:
                        self._download_one(ydl, song, staging)
                    except DownloadCancelled:
                        song.status = "已取消"
                    except DownloadError as exc:
                        song.status = "失败"
                        self._log(f"✗ {song.title or song.bvid}：{_short_error(exc)}")
                    except Exception as exc:  # noqa: BLE001 - 单个失败不影响批次
                        song.status = "失败"
                        self._log(f"✗ {song.title or song.bvid}：{_friendly_error(exc).replace(chr(10), ' ')}")
                    self._emit("item", song=song, progress=index / len(pending))
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return songs

    def _download_one(self, ydl, song: Song, staging: Path) -> None:
        if not self.force and song.bvid and song.bvid in self._archive:
            song.status = "跳过（已下载）"
            return

        info = ydl.extract_info(song.url, download=True)
        if not info:
            song.status = "失败"
            self._log(f"✗ {song.url}：解析失败")
            return

        bvid = info.get("id") or song.bvid
        title = info.get("title") or song.title or bvid
        song.bvid = bvid or song.bvid
        song.title = title
        song.duration = info.get("duration") or song.duration

        downloaded = list(info.get("requested_downloads") or [])
        if not downloaded:
            song.status = "跳过（已存在）"
            if bvid:
                self._archive.add(bvid)
            return

        audio = self._find_audio(staging, bvid)
        if audio is None:
            song.status = "失败"
            self._log(f"✗ {title}：没有找到下载产物")
            return

        base = sanitize_name(title, fallback=bvid or "未命名")
        target_dir = self.playlist_dir / base
        if has_audio(target_dir):
            if not self.force:
                song.status = "跳过（已存在同名歌曲）"
                song.target = str(target_dir)
                if bvid and bvid not in self._archive:
                    write_archive(self.archive_path, bvid)
                    self._archive.add(bvid)
                self._log(f"↷ {title}：{target_dir.name} 已存在，登记后跳过")
                return
            target_dir = self.playlist_dir / sanitize_name(f"{base} [{bvid}]", fallback=f"未命名 {bvid}")

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{target_dir.name}{audio.suffix.lower()}"
        if target_file.exists() and self.force:
            target_file = target_dir / f"{target_dir.name} (2){audio.suffix.lower()}"
        shutil.move(str(audio), str(target_file))
        song.target = str(target_file)
        if bvid:
            self._archive.add(bvid)

        if self.lrc:
            self._save_lrc(staging, bvid, target_dir, target_dir.name)

        size = target_file.stat().st_size if target_file.exists() else None
        song.status = f"完成 · {human_size(size)}"
        self._log(f"✓ {title} → {self.playlist}/{target_dir.name}/{target_file.name}")

    @staticmethod
    def _find_audio(staging: Path, bvid: str) -> Optional[Path]:
        try:
            candidates = [
                path for path in staging.iterdir()
                if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
            ]
        except OSError:
            return None
        if bvid:
            matched = [path for path in candidates if path.name.startswith(bvid)]
            if matched:
                return max(matched, key=lambda p: p.stat().st_mtime)
        return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None

    def _save_lrc(self, staging: Path, bvid: str, target_dir: Path, base: str) -> None:
        tracks = []
        for path in sorted(staging.glob(f"{bvid}.*.srt")):
            language = path.name[len(bvid) + 1:-len(".srt")]
            try:
                tracks.append((language, path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
        if not tracks:
            self._log(f"  （{base} 没有可用字幕，跳过歌词）")
            return
        tracks.sort(key=lambda item: _language_rank(item[0]))
        lrc = srt_tracks_to_lrc([text for _, text in tracks[:2]])
        if not lrc:
            return
        try:
            (target_dir / f"{base}.lrc").write_text(lrc, encoding="utf-8")
            self._log(f"  ↳ 已生成歌词（{', '.join(lang for lang, _ in tracks[:2])}）")
        except OSError as exc:
            self._log(f"  ↳ 歌词写入失败：{exc}")


def _short_error(exc: Exception) -> str:
    text = str(exc).strip().splitlines()
    message = text[0] if text else exc.__class__.__name__
    message = re.sub(r"^ERROR:\s*", "", message)
    return message[:200]


def _friendly_error(exc: Exception) -> str:
    """把常见异常翻译成用户能照着做的提示。"""
    message = _short_error(exc)
    lowered = message.lower()
    if "cookie" in lowered:
        return (
            "读取 Cookie 失败（浏览器数据库可能正被占用，或当前账号没有权限）。\n"
            "可以关闭浏览器后重试，或改用 --cookies cookies.txt。"
        )
    if "412" in message or "precondition failed" in lowered:
        return "被 B 站风控拦截（HTTP 412），稍等几分钟再试，或降低频率（--sleep 2）。"
    if "login" in lowered or "登录" in message:
        return f"{message}\n该内容需要登录：请提供 --cookies cookies.txt 或 --cookies-from-browser。"
    return message


def _language_rank(language: str) -> int:
    try:
        return SUBTITLE_LANGS.index(language)
    except ValueError:
        return len(SUBTITLE_LANGS) + (1 if language.startswith("en") else 2)


# ---------------------------------------------------------------------------
# 字幕 → LRC
# ---------------------------------------------------------------------------

SRT_TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def parse_srt(text: str) -> List[tuple]:
    """返回 [(起始毫秒, 文本)]。"""
    entries = []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if not lines:
            continue
        time_index = next((i for i, line in enumerate(lines) if SRT_TIME_RE.search(line)), None)
        if time_index is None:
            continue
        match = SRT_TIME_RE.search(lines[time_index])
        start = (
            int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
        ) * 1000 + int(match.group(4).ljust(3, "0"))
        content = " ".join(line for line in lines[time_index + 1:] if not line.isdigit())
        content = re.sub(r"<[^>]+>", "", content).strip()
        if content:
            entries.append((start, content))
    return entries


def srt_tracks_to_lrc(tracks: List[str], max_lines: int = 4000) -> str:
    """把一或两条 SRT 合成 LRC；同时间戳的第二条作为翻译行。"""
    if not tracks:
        return ""
    primary = parse_srt(tracks[0])
    if not primary:
        return ""
    translations = {}
    if len(tracks) > 1:
        for start, text in parse_srt(tracks[1]):
            translations.setdefault(start, text)

    lines = []
    for start, text in primary[:max_lines]:
        minutes, remainder = divmod(max(0, start), 60000)
        seconds, millis = divmod(remainder, 1000)
        stamp = f"[{minutes:02d}:{seconds:02d}.{millis // 10:02d}]"
        lines.append(f"{stamp}{text}")
        translation = translations.get(start)
        if translation and translation != text:
            lines.append(f"{stamp}{translation}")
    return "\n".join(lines) + ("\n" if lines else "")


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------

def _print_event(verbose: bool = False) -> EVENT:
    state = {"last": 0.0, "inline": False}

    def newline():
        if state["inline"]:
            print()
            state["inline"] = False

    def emit(kind: str, **payload) -> None:
        if kind == "log":
            message = payload.get("message", "")
            if message:
                newline()
                print(message)
        elif kind == "item" and verbose:
            song = payload.get("song")
            newline()
            print(f"[{payload.get('progress', 0) * 100:3.0f}%] {song.status} · {song.title or song.bvid}")
        elif kind == "progress" and verbose:
            total = payload.get("total") or 0
            if not total:
                return
            now = time.monotonic()
            if now - state["last"] < 0.5:
                return
            state["last"] = now
            print(f"\r    下载中 {payload.get('downloaded', 0) * 100 // total:3d}%", end="", flush=True)
            state["inline"] = True

    return emit


def run_cli(args) -> int:
    if not load_ytdlp():
        print("缺少依赖 yt-dlp。请运行：pip install -r download/requirements.txt")
        if not args.install:
            return 2
        if not install_packages(["yt-dlp"], print) or not load_ytdlp():
            return 1

    music_dir = Path(args.music_dir).resolve() if args.music_dir else DEFAULT_MUSIC_DIR
    playlist = args.playlist
    if not playlist and not args.list:
        print("请用 -p/--playlist 指定歌单（music/ 下的目录名，不存在会自动创建）")
        return 2

    downloader = Downloader(
        music_dir=music_dir,
        playlist=playlist or "未指定",
        quality=args.quality,
        audio_format="mp3" if args.mp3 else "m4a",
        lrc=args.lrc,
        cookies=Path(args.cookies) if args.cookies else None,
        browser=args.cookies_from_browser,
        force=args.force,
        use_archive=not args.no_archive,
        sleep_requests=args.sleep,
        verbose=args.verbose,
        emit=_print_event(verbose=not args.quiet),
    )
    if args.mp3 and not ffmpeg_available():
        print("需要转 MP3，但没有找到 FFmpeg。请安装 FFmpeg，或去掉 --mp3 直接保存 m4a。")
        return 2

    try:
        songs = downloader.plan(args.urls)
    except Exception as exc:  # noqa: BLE001 - 解析失败统一给出可读提示
        print(f"解析失败：{_friendly_error(exc)}")
        return 1
    if not songs:
        print("没有解析到任何条目")
        return 1

    if args.list:
        print(f"共 {len(songs)} 个条目：\n")
        for index, song in enumerate(songs, 1):
            print(f"{index:>3}. [{format_duration(song.duration):>5}] {song.bvid:<14} {song.title}")
        return 0

    print(f"目标：{music_dir / sanitize_name(playlist)}（{len(songs)} 首）")
    results = downloader.download(songs)
    done = sum(1 for s in results if s.status.startswith("完成"))
    skipped = sum(1 for s in results if s.status.startswith("跳过"))
    failed = sum(1 for s in results if s.status == "失败")
    print(f"\n完成 {done} · 跳过 {skipped} · 失败 {failed}")
    return 0 if failed == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="download.py",
        description="B 站音频下载器：把视频/收藏夹里的音频按播放器目录结构下载下来",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python download/download.py                                # 打开图形界面\n"
            "  python download/download.py -p 自用歌单 BV1xxBV1yy         # 下载单个视频\n"
            "  python download/download.py -p 自用歌单 --list <收藏夹链接>  # 只看清单\n"
            "  python download/download.py -p 自用歌单 --mp3 --lrc <链接>\n"
        ),
    )
    parser.add_argument("urls", nargs="*", help="B 站链接或 BV 号（可多个，也支持整段分享文案）")
    parser.add_argument("-p", "--playlist", help="music/ 下的歌单目录名，不存在会自动创建")
    parser.add_argument("--music-dir", help="音乐根目录（默认：项目下的 music/）")
    parser.add_argument("--quality", choices=list(QUALITY_FORMATS), default="auto", help="音质档位（默认 auto）")
    parser.add_argument("--mp3", action="store_true", help="转成 MP3（需要 FFmpeg；默认直接保存 m4a）")
    parser.add_argument("--lrc", action="store_true", help="尝试用 CC 字幕生成 .lrc 歌词")
    parser.add_argument("--cookies", help="cookies.txt 路径（登录后才有的内容/高码率）")
    parser.add_argument("--cookies-from-browser", choices=BROWSERS, help="从浏览器读取 Cookie")
    parser.add_argument("--force", action="store_true", help="忽略下载记录，重新下载")
    parser.add_argument("--no-archive", action="store_true", help="不写下载记录文件")
    parser.add_argument("--sleep", type=float, default=0.5, help="请求间隔秒数（默认 0.5，批量可调大）")
    parser.add_argument("--list", action="store_true", help="只列出将下载的条目，不下载")
    parser.add_argument("--gui", action="store_true", help="打开图形界面")
    parser.add_argument("--install", action="store_true", help="缺少 yt-dlp 时自动安装")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示 yt-dlp 的详细日志")
    parser.add_argument("-q", "--quiet", action="store_true", help="只显示最终结果")
    return parser


# ---------------------------------------------------------------------------
# 图形界面（CustomTkinter）
# ---------------------------------------------------------------------------

COLOR_BG = "#101014"
COLOR_CARD = "#17171E"
COLOR_ROW_ALT = "#1B1B23"
COLOR_INPUT = "#1F1F28"
COLOR_BORDER = "#2A2A35"
COLOR_TEXT = "#ECECF2"
COLOR_MUTED = "#8D93A1"
COLOR_ACCENT = "#5B8CFF"
COLOR_ACCENT_HOVER = "#4A78E6"
COLOR_BORDER_HOVER = "#3A3A48"
COLOR_DANGER = "#F0616D"
COLOR_DANGER_HOVER = "#D9505C"
COLOR_SUCCESS = "#3DDC84"

FONT_CANDIDATES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "Segoe UI",
    "DejaVu Sans",
)


def _pick_font(tkfont) -> str:
    available = set(tkfont.families())
    for name in FONT_CANDIDATES:
        if name in available:
            return name
    return "Sans"


def _status_color(status: str) -> str:
    if status.startswith("完成"):
        return COLOR_SUCCESS
    if status.startswith("失败"):
        return COLOR_DANGER
    if status.startswith(("跳过", "已取消")):
        return COLOR_MUTED
    return COLOR_TEXT


def _import_customtkinter():
    try:
        import customtkinter as ctk
        return ctk
    except ImportError:
        return None


def _install_customtkinter_interactive():
    """缺少界面库时，用标准 tkinter 弹窗询问是否安装。"""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("缺少 customtkinter，且当前 Python 没有 tkinter，无法打开图形界面。")
        print("请运行：pip install -r download/requirements.txt")
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        confirmed = messagebox.askyesno(
            "缺少界面库",
            "图形界面需要 customtkinter（约 1MB）。\n\n是否现在安装？",
        )
    finally:
        root.destroy()
    if not confirmed:
        return None
    if not install_packages(["customtkinter"], print):
        return None
    return _import_customtkinter()


def run_gui() -> int:
    ctk = _import_customtkinter()
    if ctk is None:
        ctk = _install_customtkinter_interactive()
        if ctk is None:
            print("未安装 customtkinter。可以运行：pip install -r download/requirements.txt")
            return 2

    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
        from tkinter import font as tkfont
    except ImportError:
        print("当前 Python 缺少 tkinter，无法打开图形界面。")
        print("请使用带 tkinter 的 Python，或改用命令行：python download/download.py -p 歌单 <链接>")
        return 2

    class App:
        def __init__(self, root):
            self.root = root
            self.music_dir = DEFAULT_MUSIC_DIR
            self.songs: List[Song] = []
            self.rows: List[dict] = []
            self.downloader: Optional[Downloader] = None
            self.worker: Optional[threading.Thread] = None
            self.queue: "queue.Queue[tuple]" = queue.Queue()
            self.busy = False
            self.font = _pick_font(tkfont)

            root.title("B 站音频下载器")
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            width = min(1040, max(760, screen_w - 60))
            height = min(840, max(600, screen_h - 100))
            left = max(0, (screen_w - width) // 2)
            top = max(0, (screen_h - height) // 2 - 20)
            root.geometry(f"{width}x{height}+{left}+{top}")
            root.minsize(min(820, width), min(600, height))
            root.configure(fg_color=COLOR_BG)
            self._build()
            self._load_playlists()
            self._show_empty()
            if height < 720:
                self._toggle_log(hide=True)
            root.after(120, self._pump)

        # -- 外观工具 -----------------------------------------------------
        def _card(self, parent):
            card = ctk.CTkFrame(
                parent, fg_color=COLOR_CARD, corner_radius=14,
                border_width=1, border_color=COLOR_BORDER,
            )
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=12, pady=10)
            return card, body

        def _muted(self, parent, text, size=12, **kwargs):
            return ctk.CTkLabel(
                parent, text=text, font=(self.font, size), text_color=COLOR_MUTED, **kwargs)

        def _ghost_button(self, parent, text, command, width=78):
            return ctk.CTkButton(
                parent, text=text, width=width, height=32, corner_radius=8,
                fg_color="transparent", hover_color=COLOR_INPUT,
                border_width=1, border_color=COLOR_BORDER,
                text_color=COLOR_MUTED, font=(self.font, 12), command=command,
            )

        # -- 布局 ---------------------------------------------------------
        def _build(self):
            F = self.font
            shell = ctk.CTkFrame(self.root, fg_color=COLOR_BG, corner_radius=0)
            shell.pack(fill="both", expand=True, padx=18, pady=14)
            shell.grid_columnconfigure(0, weight=1)
            shell.grid_rowconfigure(3, weight=1)

            header = ctk.CTkFrame(shell, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew")
            ctk.CTkLabel(header, text="B 站音频下载器", font=(F, 22, "bold"),
                         text_color=COLOR_TEXT).pack(side="left")
            self._muted(header, "粘贴链接 → 解析清单 → 下载到 music/<歌单>/<标题>/").pack(
                side="left", padx=(14, 0), pady=(8, 0))

            # -- 设置 --
            settings_card, settings = self._card(shell)
            settings_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            settings.grid_columnconfigure(1, weight=1)
            self._muted(settings, "歌单").grid(row=0, column=0, sticky="w")
            self.playlist_box = ctk.CTkComboBox(
                settings, values=[""], height=34, corner_radius=8,
                border_width=1, fg_color=COLOR_INPUT, border_color=COLOR_BORDER,
                button_color=COLOR_INPUT, button_hover_color=COLOR_BORDER_HOVER,
                text_color=COLOR_TEXT, font=(F, 13), dropdown_font=(F, 13),
            )
            self.playlist_box.grid(row=0, column=1, sticky="ew", padx=(8, 18))

            self._muted(settings, "音质").grid(row=0, column=2, sticky="w")
            self.quality_menu = ctk.CTkOptionMenu(
                settings, width=152, height=34, corner_radius=8, dynamic_resizing=False,
                values=[QUALITY_LABELS[key] for key in ("auto", "320", "132", "64")],
                fg_color=COLOR_INPUT, button_color=COLOR_INPUT,
                button_hover_color=COLOR_BORDER_HOVER, text_color=COLOR_TEXT,
                font=(F, 12), dropdown_font=(F, 12),
            )
            self.quality_menu.set(QUALITY_LABELS["auto"])
            self.quality_menu.grid(row=0, column=3, sticky="w", padx=(8, 18))

            self._muted(settings, "格式").grid(row=0, column=4, sticky="w")
            self.format_seg = ctk.CTkSegmentedButton(
                settings, values=["m4a", "mp3"] if ffmpeg_available() else ["m4a"],
                height=32, corner_radius=8,
                selected_color=COLOR_ACCENT, selected_hover_color=COLOR_ACCENT_HOVER,
                unselected_color=COLOR_INPUT, unselected_hover_color=COLOR_BORDER_HOVER,
                text_color=COLOR_TEXT, font=(F, 12),
            )
            self.format_seg.set("m4a")
            self.format_seg.grid(row=0, column=5, sticky="w", padx=(8, 0))

            checks = ctk.CTkFrame(settings, fg_color="transparent")
            checks.grid(row=1, column=0, columnspan=6, sticky="w", pady=(12, 0))
            self.lrc_var = tk.BooleanVar(value=False)
            self.keep_var = tk.BooleanVar(value=True)
            self.force_var = tk.BooleanVar(value=False)
            for text, variable in (
                ("用 CC 字幕生成歌词", self.lrc_var),
                ("跳过已下载", self.keep_var),
                ("强制重新下载", self.force_var),
            ):
                ctk.CTkCheckBox(
                    checks, text=text, variable=variable, font=(F, 12),
                    text_color=COLOR_MUTED, checkbox_width=20, checkbox_height=20,
                    corner_radius=5, border_width=2, border_color=COLOR_BORDER_HOVER,
                    fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                ).pack(side="left", padx=(0, 22))

            self._muted(settings, "Cookie 文件").grid(row=2, column=0, sticky="w", pady=(12, 0))
            self.cookie_entry = ctk.CTkEntry(
                settings, height=34, corner_radius=8, placeholder_text="可选：cookies.txt",
                fg_color=COLOR_INPUT, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, font=(F, 12),
            )
            self.cookie_entry.grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=(12, 0))
            ctk.CTkButton(
                settings, text="浏览…", width=70, height=34, corner_radius=8,
                fg_color=COLOR_INPUT, hover_color=COLOR_BORDER_HOVER,
                text_color=COLOR_TEXT, font=(F, 12), command=self._pick_cookie,
            ).grid(row=2, column=2, sticky="w", pady=(12, 0))
            self._muted(settings, "或读浏览器").grid(row=2, column=3, sticky="w", pady=(12, 0))
            self.browser_menu = ctk.CTkOptionMenu(
                settings, width=118, height=34, corner_radius=8, dynamic_resizing=False,
                values=["不使用", *BROWSERS], fg_color=COLOR_INPUT, button_color=COLOR_INPUT,
                button_hover_color=COLOR_BORDER_HOVER, text_color=COLOR_TEXT,
                font=(F, 12), dropdown_font=(F, 12),
            )
            self.browser_menu.set("不使用")
            self.browser_menu.grid(row=2, column=4, columnspan=2, sticky="w", padx=(8, 0), pady=(12, 0))

            # -- 链接 --
            link_card, link_body = self._card(shell)
            link_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
            link_body.grid_columnconfigure(0, weight=1)
            self.url_box = ctk.CTkTextbox(
                link_body, height=64, corner_radius=10, border_width=1,
                fg_color=COLOR_INPUT, border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                font=(F, 12), wrap="word",
            )
            self.url_box.grid(row=0, column=0, sticky="ew")

            actions = ctk.CTkFrame(link_body, fg_color="transparent")
            actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            self.resolve_btn = ctk.CTkButton(
                actions, text="解析清单", width=104, height=32, corner_radius=8,
                fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                text_color="#0B0B0F", font=(F, 12, "bold"), command=self.on_resolve,
            )
            self.resolve_btn.pack(side="left")
            self._ghost_button(actions, "清空", self._clear_urls, width=64).pack(side="left", padx=(8, 0))
            self.status_label = self._muted(actions, "就绪")
            self.status_label.pack(side="right")

            # -- 列表 --
            list_card, list_body = self._card(shell)
            list_card.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
            list_body.grid_rowconfigure(1, weight=1)
            list_body.grid_columnconfigure(0, weight=1)

            head = tk.Frame(list_body, bg=COLOR_CARD, height=22)
            head.grid(row=0, column=0, sticky="ew", padx=(0, 12))
            head.grid_columnconfigure(2, weight=1)
            for column, (text, width, anchor) in enumerate((
                ("", 2, "w"), ("#", 4, "w"), ("标题", 0, "w"),
                ("BV 号", 13, "w"), ("时长", 6, "e"), ("状态", 16, "e"),
            )):
                tk.Label(
                    head, text=text, bg=COLOR_CARD, fg=COLOR_MUTED,
                    font=(F, 10), width=width, anchor=anchor,
                ).grid(row=0, column=column, sticky="ew", padx=(6 if column == 0 else 2, 4))

            self.list_frame = ctk.CTkScrollableFrame(
                list_body, fg_color=COLOR_CARD, corner_radius=0, height=100,
                scrollbar_button_color=COLOR_BORDER,
                scrollbar_button_hover_color=COLOR_BORDER_HOVER,
            )
            self.list_frame.grid(row=1, column=0, sticky="nsew")
            self.list_frame.grid_columnconfigure(0, weight=1)

            # -- 工具条 --
            tools = ctk.CTkFrame(shell, fg_color="transparent")
            tools.grid(row=4, column=0, sticky="ew", pady=(10, 0))
            self._ghost_button(tools, "全选", lambda: self._select_all(True)).pack(side="left")
            self._ghost_button(tools, "全不选", lambda: self._select_all(False)).pack(
                side="left", padx=(8, 0))
            self.log_toggle = self._ghost_button(tools, "隐藏日志", self._toggle_log, width=86)
            self.log_toggle.pack(side="left", padx=(8, 0))
            self.start_btn = ctk.CTkButton(
                tools, text="开始下载", width=120, height=34, corner_radius=8,
                fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                text_color="#0B0B0F", font=(F, 13, "bold"), command=self.on_start,
            )
            self.start_btn.pack(side="right")
            self.cancel_btn = ctk.CTkButton(
                tools, text="取消", width=76, height=34, corner_radius=8,
                fg_color="transparent", hover_color=COLOR_INPUT,
                border_width=1, border_color=COLOR_DANGER,
                text_color=COLOR_DANGER, font=(F, 12), state="disabled",
                command=self.on_cancel,
            )
            self.cancel_btn.pack(side="right", padx=(0, 8))
            self._ghost_button(tools, "打开音乐目录", self._open_music, width=112).pack(
                side="right", padx=(0, 8))

            # -- 进度 --
            progress_row = ctk.CTkFrame(shell, fg_color="transparent")
            progress_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
            progress_row.grid_columnconfigure(0, weight=1)
            self.progress = ctk.CTkProgressBar(
                progress_row, height=6, corner_radius=3,
                fg_color=COLOR_INPUT, progress_color=COLOR_ACCENT,
            )
            self.progress.set(0)
            self.progress.grid(row=0, column=0, sticky="ew")
            self.detail_label = self._muted(progress_row, "", size=11)
            self.detail_label.grid(row=0, column=1, sticky="e", padx=(12, 0))

            # -- 日志 --
            self.log_card, log_body = self._card(shell)
            self.log_card.grid(row=6, column=0, sticky="ew", pady=(10, 0))
            self.log_box = ctk.CTkTextbox(
                log_body, height=84, corner_radius=10, border_width=1,
                fg_color="#0C0C11", border_color=COLOR_BORDER,
                text_color=COLOR_MUTED, font=(F, 11), wrap="word",
            )
            self.log_box.pack(fill="both", expand=True)
            self.log_box.configure(state="disabled")

        # -- 列表 ---------------------------------------------------------
        def _show_empty(self):
            for child in self.list_frame.winfo_children():
                child.destroy()
            self.rows = []
            hint = tk.Frame(self.list_frame, bg=COLOR_CARD)
            hint.pack(fill="x", pady=26)
            tk.Label(
                hint, text="粘贴链接后点「解析清单」，支持收藏夹整张解析",
                bg=COLOR_CARD, fg=COLOR_MUTED, font=(self.font, 12),
            ).pack()

        def _build_row(self, position: int, song: Song) -> dict:
            background = COLOR_CARD if position % 2 == 0 else COLOR_ROW_ALT
            row = tk.Frame(self.list_frame, bg=background, height=30)
            row.pack(fill="x")
            row.pack_propagate(False)
            row.grid_rowconfigure(0, weight=1)
            row.grid_columnconfigure(2, weight=1)

            check = tk.Label(
                row, text="☑" if song.selected else "☐", bg=background,
                fg=COLOR_ACCENT if song.selected else COLOR_MUTED,
                font=(self.font, 13), width=2, cursor="hand2",
            )
            check.grid(row=0, column=0, sticky="w", padx=(6, 0))
            check.bind("<Button-1>", lambda event, index=position: self._toggle(index))

            tk.Label(
                row, text=str(position + 1), bg=background, fg=COLOR_MUTED,
                font=(self.font, 10), width=4, anchor="w",
            ).grid(row=0, column=1, sticky="w")

            title = tk.Label(
                row, text=song.title or song.bvid or song.url, bg=background,
                fg=COLOR_TEXT, font=(self.font, 11), anchor="w",
            )
            title.grid(row=0, column=2, sticky="ew", padx=(2, 8))

            bvid = tk.Label(
                row, text=song.bvid or "—", bg=background, fg=COLOR_MUTED,
                font=(self.font, 10), width=13, anchor="w",
            )
            bvid.grid(row=0, column=3, sticky="w")

            duration = tk.Label(
                row, text=format_duration(song.duration), bg=background, fg=COLOR_MUTED,
                font=(self.font, 10), width=6, anchor="e",
            )
            duration.grid(row=0, column=4, sticky="e")

            status = tk.Label(
                row, text=song.status, bg=background, fg=_status_color(song.status),
                font=(self.font, 10), width=16, anchor="e",
            )
            status.grid(row=0, column=5, sticky="e", padx=(6, 8))

            return {"frame": row, "bg": background, "check": check, "title": title,
                    "bvid": bvid, "duration": duration, "status": status}

        def _fill_list(self, songs: List[Song]):
            for child in self.list_frame.winfo_children():
                child.destroy()
            self.songs = songs
            self.rows = []
            for position, song in enumerate(songs):
                song.index = position
                self.rows.append(self._build_row(position, song))
            if not songs:
                self._show_empty()
            self.status_label.configure(text=f"共 {len(songs)} 个条目")

        def _refresh_row(self, song: Song):
            if not (0 <= song.index < len(self.rows)):
                return
            row = self.rows[song.index]
            row["check"].configure(
                text="☑" if song.selected else "☐",
                fg=COLOR_ACCENT if song.selected else COLOR_MUTED,
            )
            row["title"].configure(text=song.title or song.bvid or song.url)
            row["bvid"].configure(text=song.bvid or "—")
            row["duration"].configure(text=format_duration(song.duration))
            row["status"].configure(text=song.status, fg=_status_color(song.status))

        def _toggle(self, position: int):
            if not (0 <= position < len(self.songs)):
                return
            song = self.songs[position]
            song.selected = not song.selected
            self._refresh_row(song)
            selected = sum(1 for item in self.songs if item.selected)
            self.status_label.configure(text=f"已选 {selected}/{len(self.songs)}")

        def _select_all(self, value: bool):
            for song in self.songs:
                song.selected = value
                self._refresh_row(song)
            if self.songs:
                self.status_label.configure(
                    text=f"已选 {len(self.songs) if value else 0}/{len(self.songs)}")

        # -- 设置读取 -----------------------------------------------------
        def _load_playlists(self):
            names = list_playlists(self.music_dir)
            self.playlist_box.configure(values=names or [""])
            if names and not self.playlist_box.get():
                self.playlist_box.set(names[0])

        def _pick_cookie(self):
            path = filedialog.askopenfilename(
                title="选择 cookies.txt", filetypes=[("Cookies", "*.txt"), ("所有文件", "*.*")])
            if path:
                self.cookie_entry.delete(0, "end")
                self.cookie_entry.insert(0, path)

        def _clear_urls(self):
            self.url_box.delete("1.0", "end")

        def _open_music(self):
            open_in_file_manager(self.music_dir)

        def _toggle_log(self, hide: Optional[bool] = None):
            """收起/展开日志卡；小屏幕上默认为收起，避免内容被裁掉。"""
            if hide is None:
                hide = bool(self.log_card.winfo_ismapped())
            if hide:
                self.log_card.grid_remove()
                self.log_toggle.configure(text="显示日志")
            else:
                self.log_card.grid()
                self.log_toggle.configure(text="隐藏日志")

        def _current_playlist(self) -> str:
            return sanitize_name(self.playlist_box.get().strip())

        def _make_downloader(self) -> Downloader:
            browser = None if self.browser_menu.get() == "不使用" else self.browser_menu.get()
            cookie_path = self.cookie_entry.get().strip()
            quality_label = self.quality_menu.get()
            quality = next(
                (key for key, label in QUALITY_LABELS.items() if label == quality_label), "auto")
            return Downloader(
                music_dir=self.music_dir,
                playlist=self._current_playlist(),
                quality=quality,
                audio_format=self.format_seg.get(),
                lrc=self.lrc_var.get(),
                cookies=Path(cookie_path) if cookie_path else None,
                browser=browser,
                force=self.force_var.get(),
                use_archive=self.keep_var.get(),
                emit=self._emit,
            )

        # -- 事件循环 -----------------------------------------------------
        def _emit(self, kind: str, **payload):
            self.queue.put((kind, payload))

        def _pump(self):
            try:
                while True:
                    kind, payload = self.queue.get_nowait()
                    self._handle(kind, payload)
            except queue.Empty:
                pass
            self.root.after(120, self._pump)

        def _handle(self, kind: str, payload: dict):
            if kind == "log":
                self._append_log(payload.get("message", ""))
            elif kind == "plan":
                self._fill_list(payload["songs"])
            elif kind == "progress":
                downloaded = payload.get("downloaded") or 0
                total = payload.get("total") or 0
                base = payload.get("base", 0.0)
                span = payload.get("span", 1.0)
                fraction = (downloaded / total) if total else 0.0
                self.progress.set(base + fraction * span)
            elif kind == "item":
                song = payload["song"]
                self._refresh_row(song)
                overall = payload.get("progress", 0.0)
                self.progress.set(overall)
                self.detail_label.configure(
                    text=f"{int(overall * len(self.songs))}/{len(self.songs)} · {song.title or song.bvid}")
            elif kind == "done":
                self._set_busy(False)
                self.status_label.configure(text=payload.get("message", "就绪"))
                self.detail_label.configure(text="")
                self._load_playlists()
            elif kind == "error":
                self._set_busy(False)
                self.status_label.configure(text="出错")
                messagebox.showerror("出错了", payload.get("message", ""))

        def _append_log(self, message: str):
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{time.strftime('%H:%M:%S')}  {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        def _set_busy(self, busy: bool):
            self.busy = busy
            self.resolve_btn.configure(state="disabled" if busy else "normal")
            self.start_btn.configure(state="disabled" if busy else "normal")
            self.cancel_btn.configure(state="normal" if busy else "disabled")

        # -- 行为 ---------------------------------------------------------
        def on_resolve(self):
            if self.busy:
                return
            text = self.url_box.get("1.0", "end").strip()
            if not text:
                messagebox.showinfo("提示", "先粘贴 B 站链接或 BV 号")
                return
            if not load_ytdlp():
                self._offer_install()
                return
            downloader = self._make_downloader()  # Tk 变量只能在主线程读
            self._set_busy(True)
            self.status_label.configure(text="解析中…")
            self.songs = []

            def work():
                try:
                    songs = downloader.plan(text)
                    if not songs:
                        raise RuntimeError("没有解析到任何条目")
                    self._emit("plan", songs=songs)
                    self._emit("done", message=f"解析到 {len(songs)} 个条目")
                except Exception as exc:  # noqa: BLE001 - 反馈给界面
                    self._emit("error", message=_friendly_error(exc))

            self.worker = threading.Thread(target=work, daemon=True)
            self.worker.start()

        def on_start(self):
            if self.busy:
                return
            selected = [song for song in self.songs if song.selected]
            if not selected:
                messagebox.showinfo("提示", "先点「解析清单」，并至少勾选一首")
                return
            if not self.playlist_box.get().strip():
                messagebox.showinfo("提示", "先填写歌单名")
                return
            if self.format_seg.get() == "mp3" and not ffmpeg_available():
                messagebox.showerror("缺少 FFmpeg", "转 MP3 需要 FFmpeg。请改为 m4a，或先安装 FFmpeg。")
                return
            if not load_ytdlp():
                self._offer_install()
                return

            self._set_busy(True)
            self.status_label.configure(text="下载中…")
            downloader = self._make_downloader()
            self.downloader = downloader

            def work():
                try:
                    results = downloader.download(selected)
                    done = sum(1 for song in results if song.status.startswith("完成"))
                    skipped = sum(1 for song in results if song.status.startswith("跳过"))
                    failed = sum(1 for song in results if song.status == "失败")
                    self._emit("done", message=f"完成 {done} · 跳过 {skipped} · 失败 {failed}")
                except Exception as exc:  # noqa: BLE001 - 反馈给界面
                    self._emit("error", message=_friendly_error(exc))

            self.worker = threading.Thread(target=work, daemon=True)
            self.worker.start()

        def on_cancel(self):
            if self.downloader:
                self.downloader.cancel.set()
                self.status_label.configure(text="正在取消…")
                self._append_log("已请求取消")

        def _offer_install(self):
            if self.busy:
                return
            answer = messagebox.askyesno(
                "缺少依赖",
                "需要 yt-dlp 才能下载。\n\n是否现在用 pip 安装？（需要联网，约几 MB）",
            )
            if not answer:
                self._append_log("未安装 yt-dlp，无法下载")
                return
            self._set_busy(True)
            self.status_label.configure(text="正在安装 yt-dlp…")

            def work():
                ok = install_packages(["yt-dlp"], lambda message: self._emit("log", message=message))
                if ok:
                    ok = load_ytdlp()
                self._emit("done", message="yt-dlp 已就绪" if ok else "yt-dlp 安装失败")
                if not ok:
                    self._emit("error", message="yt-dlp 安装失败，请手动运行：pip install yt-dlp")

            self.worker = threading.Thread(target=work, daemon=True)
            self.worker.start()

    try:
        root = ctk.CTk()
    except Exception as exc:  # noqa: BLE001 - 无显示环境
        print(f"无法打开图形界面：{exc}")
        print("如果是无桌面的服务器，请改用命令行：python download/download.py -p 歌单 <链接>")
        return 2

    app = App(root)
    if not load_ytdlp():
        root.after(300, app._offer_install)
    root.mainloop()
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main(argv: Optional[Iterable[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.gui or not args.urls:
        return run_gui()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
