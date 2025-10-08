# 在线音乐播放器

![示例图片](test.png)

一个功能丰富的Web音乐播放器，支持歌词显示、自选歌单播放和多种配色方案。

如果你正打算从B站收藏夹搬运音乐用于此播放器，建议你使用项目[bilibili-video2mp3](https://github.com/wxsms/bilibili-video2mp3)将视频转为Mp3音频。

## 主要功能

- 🎵 支持多种音频格式（MP3、M4A、AAC等）
- 📄 自动歌词显示和翻译支持
- 🎨 8种配色方案，实时切换
- 📱 分页浏览，每页10首歌曲
- 🌐 自选歌单播放功能

## 快速开始

1. 克隆本项目至您的网站（要求具有能运行PHP的后端）
2. 将音乐文件放入 `music/` 文件夹下的子文件夹中
3. 如需显示歌词，创建与歌曲同名的 `.lrc` 文件
4. 重新启动Web服务器
5. 访问 `index.html` 开始使用

## 歌词文件格式

使用标准LRC格式，支持翻译：

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
