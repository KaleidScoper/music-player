# 在线音乐播放器

![示例图片](test.png)

一个功能丰富的Web音乐播放器，支持歌词显示、自选歌单播放和多种配色方案。

如果你正打算从B站收藏夹搬运音乐用于此播放器，建议你使用项目[bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3)将视频转为Mp3音频。本项目已经内置了基于此工具的一个批量下载脚本。

## B站视频批量下载脚本

脚本为[bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3)设计。

### 环境要求
- Python 3.6+（运行环境）
- Node.js（下载工具运行环境）
- FFmpeg（下载工具格式转换）

### 安装依赖

前往[bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3)安装下载工具。

### 使用方法
```bash
# 正常模式（检查环境）
python download/download.py

# 跳过环境检查
python download/download.py --skip-check

# 调试模式
python download/download.py --debug
```

### 使用步骤
1. 运行脚本
2. 直接粘贴B站分享文本（如：【视频标题】 https://www.bilibili.com/video/...），脚本会自动提取URL
3. 选择保存目录（download目录、现有歌单目录或创建新歌单）
4. 确认下载
5. 等待下载完成

音频文件将保存到当前目录，可直接放入 `music/` 文件夹使用。

## 主要功能

- 🎵 支持多种音频格式（MP3、M4A、AAC等）
- 📄 自动歌词显示和翻译支持
- 🎨 8种配色方案，流畅动画
- 📱 分页加载，每页10首歌曲
- 🌐 自由多选歌单播放功能

## 待完成功能

- 允许播放器主体以悬浮窗形式在所部署的网站的其他页面打开；
- 将爬取B站歌单功能图形化，集成入播放器页面；

## 快速开始

1. 克隆本项目至您的网站（要求具有能运行PHP的后端）
2. 将音乐文件放入 `music/` 文件夹下的子文件夹中
3. 如需显示歌词，创建与歌曲同名的 `.lrc` 文件
4. 重新启动Web服务器
5. 访问 `index.html` 开始使用

## 歌词文件格式

使用标准LRC格式，支持翻译（同时间戳的后一句会被认为是翻译）：

```
[00:00:00]Hello World!
[00:00:00]你好世界!
```

## 文件结构

```
music_player/
├── index.html
├── style.css
├── script.js
├── backend.php
└── music/
    ├── 歌单1/
    │   ├── 歌曲1.mp3
    │   └── lyrics/
    │       └── 歌曲1.lrc
    └── 歌单2/
        └── 歌曲2.mp3
```

## 技术栈

- 前端：HTML5、CSS3、JavaScript
- 后端：PHP
- 音频：HTML5 Audio API

## 许可证

MIT License
