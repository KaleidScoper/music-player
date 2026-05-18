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

## 四、文件变更清单

### 4.1 新增文件

| 文件 | 说明 |
|------|------|
| `server.py` | Flask 应用，替代 backend.php，提供 API + 静态文件服务 + 音频流 |
| `requirements.txt` | `flask` |
| `start.sh` | Linux/macOS 启动脚本 |
| `start.bat` | Windows 启动脚本 |

### 4.2 修改文件

| 文件 | 变更内容 |
|------|----------|
| `script.js` | API 请求路径从 `backend.php?action=...` 改为 `/api/...` |
| `README.md` | 更新快速开始部分，去掉 nginx/PHP 要求 |

### 4.3 删除文件

| 文件 | 原因 |
|------|------|
| `backend.php` | 功能迁移至 `server.py` |
| `debug.php` | 诊断功能合并到 `server.py` 启动日志中 |

---

## 五、server.py 设计

### 5.1 路由表

```
GET  /                    → 返回 index.html
GET  /style.css           → 静态文件
GET  /script.js           → 静态文件
GET  /background.jpg      → 静态文件
GET  /music/<path>        → 音频文件流（支持 Range 请求，用于 seek）
GET  /api/folders         → 获取所有歌单文件夹名
GET  /api/songs           → 获取指定歌单的歌曲列表  (?folder=xxx)
GET  /api/lyrics          → 获取单首歌词              (?folder=xxx&song=xxx)
GET  /api/batch-lyrics    → 批量获取歌词              (?folder=xxx&songs=json)
POST /api/clear-cache     → 清除歌词缓存
```

### 5.2 核心模块

```
server.py
├── LyricsCache      → 内存歌词索引 + LRU 缓存（原 PHP LyricsCache 的 Python 移植）
├── get_folders()    → 扫描 music/ 目录
├── get_songs()      → 扫描指定歌单下的音频文件
├── get_lyrics()     → 按优先级匹配歌词文件并返回内容
├── serve_music()    → 流式返回音频，支持 Range 头（HTML5 Audio seek 必需）
└── main()           → 解析命令行参数，启动 Flask
```

### 5.3 Range 请求支持

HTML5 `<audio>` 的 seek 功能依赖 HTTP Range 请求。Flask 的 `send_file` 默认不支持 Range，需手动实现或使用 `werkzeug` 的 `Range` 中间件。方案：

```python
from flask import request, Response

def serve_music(path):
    # 手动解析 Range 头，返回 206 Partial Content
    # 确保 Chrome/Safari 等浏览器的 seek 正常工作
```

### 5.4 命令行参数

```
python server.py                 # 默认 0.0.0.0:8080
python server.py --port 3000     # 自定义端口
python server.py --host 127.0.0.1 # 仅本地访问
python server.py --debug          # 开发模式（热重载）
```

---

## 六、启动脚本设计

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

## 七、前后端对接变更

script.js 中的变更点（6处 fetch 调用）：

| 原调用 | 新调用 |
|--------|--------|
| `backend.php?action=getFolders` | `/api/folders` |
| `backend.php?action=getSongs&folder=...` | `/api/songs?folder=...` |
| `backend.php?action=getLyrics&folder=...&song=...` | `/api/lyrics?folder=...&song=...` |
| `backend.php?action=getBatchLyrics&folder=...&songs=...` | `/api/batch-lyrics?folder=...&songs=...` |
| `backend.php?action=clearLyricsCache` | `/api/clear-cache` (POST) |

audio `src` 属性不变：`music/...` 路径由 Flask 统一处理。

---

## 八、不涉及的部分

以下模块保持不变：
- `download/download.py` — 已是独立 Python 脚本，无 PHP 依赖
- `music/` 和 `lyrics/` 目录结构 — 完全兼容
- `index.html`, `style.css` — 无需改动
- `doc/`, `LICENSE` — 照旧

---

## 九、实施步骤

1. 创建 `server.py`，实现全部 API 和静态文件服务
2. 创建 `requirements.txt`
3. 创建 `start.sh` 和 `start.bat`
4. 修改 `script.js` 中的 API 路径
5. 删除 `backend.php` 和 `debug.php`
6. 更新 `README.md` 的快速开始章节
7. 全流程测试：克隆 → `./start.sh` → 浏览器播放
