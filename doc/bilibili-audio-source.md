# B 站音频获取方案调研

> 目标：替换 `download/download.py` 里「npx bv2mp3」这条链路，让「B 站视频 → `music/<歌单>/<歌曲>/<音频>`」变成一条命令、可重复执行、音质不打折。
>
> 调研时间：2026-10-27。所有「实测」数据均在本机（Windows / Python 3.12 / Node 24）对 `BV1uv411q7Mv` 运行得到。

## 一、现状：现在是怎么拿到音频的

### 1.1 调用链

```
python download/download.py
  └─ 交互式收集 URL（逐个 input）→ 选择保存目录 → 确认
  └─ subprocess.run('npx bv2mp3 --url="..." --url="..."', shell=True)
        └─ npm 包 bv2mp3@4.0.1
              ├─ GET api.bilibili.com/x/player/playurl?fnval=80&cid=&bvid=   → dash.audio[0].baseUrl
              ├─ 下载到当前目录，文件名 .flv（内容其实是 m4a）
              └─ ffmpeg -y -i xxx.flv -q:a 0 xxx.mp3
  └─ 把当前目录里所有音频文件挪进 music/<歌单>/<文件名>/
```

`download/COMPLETE_INTEGRATION_SOLUTION.md` 里的 PHP 集成方案只是把同一句 `npx bv2mp3` 包进 PHP，引擎没变，且仓库里并没有对应的 `.php` 文件（未实现）。

### 1.2 实测结果

| 项目 | 结果 |
| --- | --- |
| 同一视频，`bv2mp3 --skip-mp3` | `爆肝９８小时！在MC中还原糖调小镇.flv`，**2,635,113 字节** |
| 该文件真实格式 | 头部为 `ftypiso5` → ISO-BMFF（m4a/AAC），扩展名是错的 |
| 对应音轨 | `dash.audio[0]` = id 30216 ≈ **64 kbps**（`dash.audio` 顺序为 30216/30232/30280，取 [0] 即最低档） |
| 同一视频，`yt-dlp -f 30280` | **12,343,454 字节** m4a（315 kbps），同样的画面/时长 |
| 旧版 `interface.bilibili.com/v2/playurl`（bv2mp3 1.x 用的接口） | 实测 **HTTP 403**；该接口属 appkey + md5 签名时代，早已停用 |
| `x/player/playurl`（不签名） | 仍返回 `code: 0`，可见 3 条音轨 30216/30232/30280 |

也就是说：**现在拿到的是最低档 64 kbps 音频，再被 `-q:a 0`（LAME V0，平均约 245 kbps）转码成体积大得多的 MP3**，属于「码率上去了、音质没上去」的二次损失。歌单里已有的 `.m4a` 文件应该不是这条链路产出的。

### 1.3 麻烦在哪（按痛感排序）

1. **音质被截断**：只用 `dash.audio[0]`（64 kbps），没有选码率的逻辑，也没有登录。
2. **强依赖 Node + FFmpeg**：`npx` 要联网装包，`ffmpeg` 缺失就直接退出（`check_environment`），而播放器本身已经支持 `.m4a`，理论上不需要转码。
3. **文件名污染**：bv2mp3 默认命名是 `TITLE-AUTHOR-DATE`，脚本没有覆盖，于是歌曲文件夹名变成「标题-UP主-2020-7-20」，只能手动改名 —— 而文件夹名就是播放器里的显示名。
4. **交互式、不可批处理**：URL 逐条 `input()`、选目录、二次确认；跑在 VPS 上只能靠 `--skip-check` 绕过检查。
5. **`shell=True` 拼接 URL**：有引号/空格转义问题，也有命令注入隐患。
6. **搬运逻辑会误伤**：`move_files_to_target_directory()` 扫描的是**当前目录所有音频**，不只本次下载的；重名时加 `_1` 后缀。
7. **没有幂等/去重**：同一 BV 重复执行会重复下载；没有记录「已下载过哪些」。
8. **没有歌词、没有封面/元数据**：`.lrc` 全靠手工。
9. **没有歌单级批量**：只能一次粘一个视频；bv2mp3 的「视频集」仅指同稿件分 P，不支持收藏夹。

## 二、候选方案

| 方案 | 维护状态（2026-10） | 依赖 | 音质控制 | 歌单/收藏夹批量 | 字幕/歌词 | 许可 | 适配本项目 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **yt-dlp** | 活跃，202k★，2026-10-26 有提交 | Python（可作库），转码才要 FFmpeg | 按 format id 精确选，30280=320k | 收藏夹/合集/视频列表/稍后再看/UP 主空间 | CC 字幕可转 `.lrc`；也能下弹幕 XML | Unlicense | ★★★★★ |
| **yutto** | 活跃，2.1k★，2026-10-25 有提交 | Python ≥3.11 + **FFmpeg 必需** | `-aq 30280` 等码率档位 | 同上，且更细（`-b`、`-p` 选集） | 字幕/弹幕/封面/元数据齐全 | GPL-3.0 | ★★★★ |
| bilibili-api-python | 活跃，17.4.2（2026-06） | Python ≥3.10 + aiohttp/httpx | 自己解析 playurl | 需自己实现 | 有字幕接口 | GPL-3.0 | ★★（要写很多胶水） |
| BBDown | **已归档**（archived），C# | .NET 运行时 | 好 | 好 | 好 | MIT | ★（不再维护） |
| lux | 活跃，31.8k★，Go | 单二进制 | 一般 | 一般 | 一般 | MIT | ★★（非 Python 生态） |
| bv2mp3（现状） | 4.0.1，Node ≥20.12 | Node + FFmpeg | **固定最低档** | 仅同稿件分 P | 无 | MIT | —— |
| 自己写 API 调用 | —— | 无 | 完全可控 | 自己实现 | 自己实现 | —— | ★（WBI 签名/风控要长期跟） |

### 2.1 为什么推荐 yt-dlp 打底

- **纯 Python、可当库用**：`pip install yt-dlp` 进项目 venv 即可，不需要 Node；`YoutubeDL().download()` 直接嵌进脚本，比 `subprocess` + 拼命令稳。
- **不需要 FFmpeg 也能出成品**：B 站 DASH 的音轨本身就是 m4a，`-f bestaudio` 直接落盘 `.m4a`，播放器的 `AUDIO_EXTENSIONS` 已经支持。要 MP3/FLAC 才用 FFmpeg。
- **音质可控**：实测 `-F` 能看到 `30216 / 30232 / 30280`（67k/133k/315k），`-f 30280` 或 `-f bestaudio` 取最高档；带 `SESSDATA` 后还能拿到 1080P60 等会员档。
- **收藏夹/合集原生支持**：2023-09 合入的 `BilibiliFavoritesListIE / BilibiliSeriesListIE / BilibiliPlaylistIE / BilibiliWatchlaterIE` 让「粘一个收藏夹链接 → 整张歌单」成立。私有收藏夹会提示需要登录，传 cookie 即可。
- **幂等**：`--download-archive` 按 BV 号记账，重复跑自动跳过 —— 正好治「不知道下过没有」。
- **歌词**：`--write-subs --sub-langs zh,ai-zh --convert-subs lrc` 可直接产出 `.lrc`（`MEDIA_EXTENSIONS.subtitles` 实测为 `ass/lrc/srt/vtt`）。注意 CC 字幕是 UP 主上传的，不是每首都有；实测三个翻唱视频都只有弹幕、没有字幕，所以歌词仍以手工 `.lrc` 为主、能自动抓算 bonus。
- **风控已内建**：yt-dlp 会自己做 WBI 签名、补 `buvid3`；裸 `urllib` 首次请求实测吃过 412，工具链不用自己处理。

### 2.2 yutto 适合什么场景

如果更看重「B 站专属功能」（选集、弹幕 ASS、封面、`yutto serve` 的 JSON-RPC 任务接口），yutto 更顺手：

```bash
yutto --audio-only -aq 30280 --no-danmaku --subtitle-languages zh \
      -d "music/1-活全家歌单" -tp "{name}/{name}" "https://www.bilibili.com/video/BVxxxx"
yutto -b --audio-only -aq 30280 -d "music/1-活全家歌单" \
      "https://space.bilibili.com/<uid>/favlist?fid=<fid>"
```

代价：FFmpeg 是硬依赖、Python ≥3.11、GPL-3.0，且必须作为外部命令/独立环境安装（pipx 更合适），不像 yt-dlp 那样能当一个普通依赖塞进 venv。

## 三、建议的落地方案

### 3.1 已实施：`download/download.py`（GUI + CLI）

脚本已按此方案重写，替换掉原来的 `npx bv2mp3` 链路，并附带一个 CustomTkinter 图形界面：

```bash
pip install -r download/requirements.txt   # yt-dlp + customtkinter
python download/download.py                # 图形界面
python download/download.py -p "1-活全家歌单" BV1xx <收藏夹链接>
```

![下载器界面（示意数据）](bilibili-downloader-gui.png)

- 输出目录 `music/<歌单>/<标题>/<标题>.<ext>`，文件夹名即播放器显示名（不再带作者和日期）。
- 默认取 `30251/30280/bestaudio`（Hi-Res → 320k → 最高可用）直接落 `.m4a`，不转码；`--mp3` 才调 FFmpeg。
- 去重：`music/<歌单>/.bili-archive.txt`，按歌单记录（同一 BV 可以出现在多个歌单）。
- 同名不同 BV：文件夹追加 ` [BV号]`；`--force` 强制重下。
- `--lrc`：有 CC 字幕就转 `.lrc`（同时间戳写两行 = 原文 + 翻译），没有就跳过。
- 收藏夹走 `x/v3/fav/resource/list` 逐页取标题（20 条/请求），接口失败再退回 yt-dlp 解析。
- 依赖：yt-dlp（pip 安装）；FFmpeg 只有转码时才需要；GUI 用标准库 tkinter。

### 3.2 未做：接进播放器

按需求，网页端不集成下载功能。若以后想自动同步，可以在 VPS 上用 cron 跑
`python download/download.py -p 歌单 <收藏夹链接>`，播放器侧无需改动。

## 四、风险与对策

| 风险 | 对策 |
| --- | --- |
| 412 / 风控 | 用 yt-dlp 内置签名与 `buvid3`；`--sleep-requests 1`；必要时 `--proxy` |
| 未登录只有低码率 | 传 `cookies.txt`（浏览器导出 SESSDATA），VPS 上放在仓库外 |
| 标题重名 / 含 `/`、`:` 等 | 交给 yt-dlp 的 filename sanitization，冲突再追加 BV 号 |
| CC 字幕不是每首都有 | 不把「自动歌词」当硬需求；缺失时保留手工 `.lrc` |
| 版权与站点条款 | 仅个人自用收藏，不公开分发；控制请求频率 |

## 五、参考

- yt-dlp：<https://github.com/yt-dlp/yt-dlp>（B 站 extractor：`yt_dlp/extractor/bilibili.py`）
- yt-dlp 收藏夹/合集支持 PR：<https://github.com/yt-dlp/yt-dlp/pull/7518>
- yt-dlp cookie 用法：<https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp>
- yutto：<https://github.com/yutto-dev/yutto>，文档 <https://yutto.nyakku.moe/>
- yutto 资源选择参数：<https://yutto.nyakku.moe/guide/cli/resource.md>
- yutto 支持的链接（收藏夹等）：<https://yutto.nyakku.moe/guide/supported-links.md>
- BBDown（已归档）：<https://github.com/nilaoda/BBDown>
- bilibili-api-python：<https://pypi.org/project/bilibili-api-python/>
- lux：<https://github.com/iawia002/lux>
- bv2mp3（现状依赖）：<https://www.npmjs.com/package/bv2mp3>
