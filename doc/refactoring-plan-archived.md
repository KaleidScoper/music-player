# 重构方案：去除 Nginx 依赖，实现开箱即用

## 一、现状分析

当前项目架构为 **nginx + PHP-FPM** 模式：

```
浏览器 → nginx (静态文件 + PHP 反向代理) → PHP-FPM (backend.php)
```

| 组件 | 文件 | 职责 |
|------|------|------|
| 前端 | `index.html`, `style.css`, `script.js` | 单页音乐播放器 UI |
| API | `backend.php` | 扫描目录、返回歌曲/歌词列表、歌词缓存 |
| 调试 | `debug.php` | 环境诊断页面 |
| 下载工具 | `download/download.py` | B站视频批量下载（Python，独立脚本） |

**痛点**：用户克隆后必须配置 nginx + PHP-FPM 才能运行，门槛高。

---

## 二、目标架构

用 Python 内置 Web 框架替代 nginx + PHP，一个命令启动：

```
浏览器 → Python Flask Server (静态文件 + API + 音频流)
```

**开箱即用流程**：
```bash
git clone <repo>
cd music-player
./start.sh        # Linux/macOS
# 或
start.bat         # Windows
```

---

## 三、技术选型：Flask

| 候选 | 结论 |
|------|------|
| Python http.server | 无依赖但需手写大量路由/范围请求逻辑，不选 |
| **Flask** | 依赖极少（仅 Flask），路由/静态文件/JSON 开箱即用，**选择此项** |
| FastAPI | 依赖链重（fastapi + uvicorn + pydantic），对此项目过度 |
| Node.js Express | 引入 npm 生态，依赖体积大，不选 |

依赖清单只有一行：`flask`。

---

## 四、目录结构重构

### 4.1 现状

```
music/
├── 歌单名1/
│   ├── 歌曲1.mp3
│   └── 歌曲2.m4a
└── 歌单名2/
    └── 歌曲3.mp3

lyrics/                          ← 镜像目录，手动维护一致性
├── 歌单名1/
│   ├── 歌曲1.lrc
│   └── 歌曲2.lrc
└── 歌单名2/
    └── 歌曲3.lrc
```

**问题**：
- `music/` 和 `lyrics/` 是镜像目录，增删歌曲要操作两处，无约束机制保证一致性
- 歌词匹配需要三级 fallback：完整文件名 → 截取 `-` 前缀 → 找不到；匹配逻辑 30+ 行，是结构缺陷的补偿
- `music/` 下残留 `.lrc` 文件，说明最初混放后来拆出，有历史包袱
- 用户必须将音频和歌词重命名为同一基础名

### 4.2 目标

```
music/
└── 歌单名/
    └── 歌曲显示名/              ← 文件夹名即为歌曲名，无需重命名文件
        ├── *.mp3 / *.m4a / ...  ← 至少一个音频文件（取第一个）
        └── *.lrc                ← 可选，有则自动加载（取第一个）
```

**优势**：
- **免重命名**：用户下载的文件名是什么就是什么，文件夹名决定显示名
- **自包含**：一首歌的音频和歌词在同一文件夹内，拖入即完成，删文件夹即删除
- **无镜像目录**：取消独立 `lyrics/` 目录，不再需要维护两套目录树的一致性
- **匹配退化为 glob**：同目录下 `*.lrc` 即歌词，`*.mp3/*.m4a/...` 即音频，不需要任何文件名匹配逻辑

### 4.3 迁移注意事项

重构后**不向后兼容**旧目录结构。现有 `music/` 下的歌曲需要整理为新格式。迁移脚本逻辑：

```
旧 music/歌单/xxx.mp3  →  新 music/歌单/xxx/xxx.mp3（或任意命名.mp3）
旧 lyrics/歌单/xxx.lrc  →  新 music/歌单/xxx/xxx.lrc（或任意命名.lrc）
```

可提供一次性迁移脚本 `migrate.sh`（可选），也可直接在 README 中说明新结构让用户自行整理。

---

## 五、文件变更清单

### 5.1 新增文件

| 文件 | 说明 |
|------|------|
| `server.py` | Flask 应用，替代 backend.php，提供 API + 静态文件服务 + 音频流 |
| `requirements.txt` | `flask` |
| `start.sh` | Linux/macOS 启动脚本 |
| `start.bat` | Windows 启动脚本 |

### 5.2 修改文件

| 文件 | 变更内容 |
|------|----------|
| `script.js` | API 路径改为 `/api/...`；歌曲数据结构适配新目录结构 |
| `download/download.py` | 下载后文件放入新目录结构（创建歌曲子文件夹） |
| `README.md` | 更新目录结构说明、快速开始章节 |

### 5.3 删除文件

| 文件 | 原因 |
|------|------|
| `backend.php` | 功能迁移至 `server.py` |
| `debug.php` | 诊断功能合并到 `server.py` 启动日志中 |
| `lyrics/` 目录 | 歌词与音频合并到歌曲文件夹内 |

---

## 六、server.py 设计

### 6.1 路由表

```
GET  /                    → 返回 index.html
GET  /style.css           → 静态文件
GET  /script.js           → 静态文件
GET  /background.jpg      → 静态文件
GET  /music/<path>        → 音频文件流（支持 Range 请求，用于 seek）
GET  /api/folders         → 获取所有歌单文件夹名
GET  /api/songs           → 获取指定歌单的歌曲列表  (?folder=xxx)
GET  /api/lyrics          → 获取指定歌曲的歌词      (?folder=xxx&song=xxx)
GET  /api/batch-lyrics    → 批量获取歌词             (?folder=xxx&songs=json)
POST /api/clear-cache     → 清除歌词缓存
```

### 6.2 核心逻辑简化

#### 获取歌单（get_folders）
```python
# 仅需列出 music/ 下的子目录
os.listdir('music')
```

#### 获取歌曲（get_songs）
```python
# 列出 music/歌单/ 下的子目录，每个子目录是一首歌
# 检查子目录内是否有音频文件，有则返回
for entry in os.listdir(f'music/{folder}'):
    song_dir = f'music/{folder}/{entry}'
    if os.path.isdir(song_dir) and has_audio(song_dir):
        songs.append(entry)
```

#### 获取歌词（get_lyrics）
```python
# 退化为同目录下 glob *.lrc，取第一个
lrc_files = glob.glob(f'music/{folder}/{song_name}/*.lrc')
if lrc_files:
    return read_file(lrc_files[0])
```

**旧代码中约 30 行的三级 fallback 匹配逻辑全部消失。**

### 6.3 Range 请求支持

HTML5 `<audio>` 的 seek 功能依赖 HTTP Range 请求。实现方案：

```python
from flask import request, Response

def serve_music(path):
    # 手动解析 Range 头，返回 206 Partial Content
    # 确保 Chrome/Safari 等浏览器的 seek 正常工作
```

### 6.4 命令行参数

```
python server.py                 # 默认 0.0.0.0:8080
python server.py --port 3000     # 自定义端口
python server.py --host 127.0.0.1 # 仅本地访问
python server.py --debug          # 开发模式（热重载）
```

---

## 七、启动脚本设计

### start.sh (Linux/macOS)

```bash
#!/bin/bash
# 1. 检查 Python 3 是否安装
# 2. 创建虚拟环境（若不存在）
# 3. 安装依赖
# 4. 启动 server.py
# 5. 自动打开浏览器（可选）
```

### start.bat (Windows)

```bat
@echo off
REM 同等逻辑，适配 Windows 命令
```

---

## 八、前后端对接变更

### script.js 中的 fetch 调用

| 原调用 | 新调用 |
|--------|--------|
| `backend.php?action=getFolders` | `/api/folders` |
| `backend.php?action=getSongs&folder=...` | `/api/songs?folder=...` |
| `backend.php?action=getLyrics&folder=...&song=...` | `/api/lyrics?folder=...&song=...` |
| `backend.php?action=getBatchLyrics&folder=...&songs=...` | `/api/batch-lyrics?folder=...&songs=...` |
| `backend.php?action=clearLyricsCache` | `/api/clear-cache` (POST) |

### 歌曲数据结构变化

```
旧: { name: "吹灭小山河-法里达.mp3", folder: "歌单", fullPath: "歌单/吹灭小山河-法里达.mp3" }
新: { name: "吹灭小山河-法里达",      folder: "歌单", audioPath: "歌单/吹灭小山河-法里达/xxx.mp3" }
```

显示名直接使用文件夹名，不再需要从文件名剥离扩展名。

---

## 九、实施步骤

1. 整理现有 `music/` 目录为新结构（歌曲文件夹化，移入对应 `.lrc`）
2. 删除 `lyrics/` 目录
3. 创建 `server.py`，实现全部 API 和静态文件服务
4. 创建 `requirements.txt`
5. 创建 `start.sh` 和 `start.bat`
6. 修改 `script.js`：API 路径 + 数据结构适配
7. 修改 `download/download.py`：下载后创建歌曲子文件夹
8. 更新 `README.md`
9. 删除 `backend.php` 和 `debug.php`
10. 全流程测试：克隆 → `./start.sh` → 浏览器播放
