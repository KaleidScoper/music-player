# 在线音乐播放器

![示例图片](test.png)

一个开箱即用的 Web 音乐播放器，克隆后一条命令即可运行。支持歌词显示、多歌单播放。

如果你正打算从B站收藏夹搬运音乐用于此播放器，建议你使用项目[bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3)将视频转为Mp3音频。本项目已经内置了基于此工具的一个批量下载脚本。

## 快速开始

```bash
git clone <repo>
cd music-player
./start.sh        # Linux/macOS
# 或
start.bat         # Windows
```

启动后访问 `http://localhost:8080`。

唯一依赖：**Python 3.6+**。

## 目录结构

```
项目根目录/
├── music/
│   └── 歌单名/
│       └── 歌曲显示名/        ← 文件夹名即为歌曲显示名
│           ├── xxx.mp3        ← 至少一个音频文件
│           └── xxx.lrc        ← 可选歌词文件
├── server.py                 ← Flask 服务
├── start.sh / start.bat      ← 启动脚本
├── index.html / style.css / script.js
└── download/                 ← B站下载工具
```

添加歌曲只需在 `music/歌单名/` 下创建一个文件夹，放入音频和歌词即可。无需重命名文件。

## 歌词文件格式

使用标准 LRC 格式，支持翻译（同一时间戳的前一行视为原文，后一行视为翻译）：

```
[00:00:00]Hello World!
[00:00:00]你好世界!
```

歌词文件放在对应歌曲文件夹内，播放器自动加载。

## B站视频批量下载脚本

脚本为 [bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3) 设计。

### 环境要求
- Python 3.6+
- Node.js（下载工具运行环境）
- FFmpeg（下载工具格式转换）

### 使用方法
```bash
python download/download.py              # 正常模式
python download/download.py --skip-check # 跳过环境检查
python download/download.py --debug      # 调试模式
```

下载完成后音频文件会自动放入对应歌单的歌曲文件夹中。

## 主要功能

- 支持多种音频格式（MP3、M4A、AAC 等）
- 自动歌词显示和翻译支持
- 多歌单自由选择播放
- 单曲循环 / 顺序播放 / 随机播放
- 歌词预加载和缓存

## 技术栈

- 前端：HTML5、CSS3、JavaScript
- 后端：Python Flask
- 音频：HTML5 Audio API

## 许可证

MIT License
