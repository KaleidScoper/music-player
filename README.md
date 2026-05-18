# 音乐播放器

部署在 VPS 上的轻量 Web 音乐播放器，以 popup 窗口形式嵌入其他站点使用。

![示例图片](test.png)

## 应用场景

- 在个人网站中嵌入一个 popup 音乐播放器
- VPS 持久运行，随时访问
- 支持多歌单管理和歌词显示

## 部署

**唯一依赖：Python 3.6+**

```bash
git clone <repo>
cd music-player
./start.sh        # Linux/macOS
# 或
start.bat         # Windows
```

启动后访问 `http://<host>:8080`。

### 自定义端口

```bash
./start.sh --port 3000
```

### 持久运行（VPS）

```bash
# systemd 示例
sudo tee /etc/systemd/system/music-player.service << 'EOF'
[Unit]
Description=Music Player
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/music-player
ExecStart=/path/to/music-player/venv/bin/python server.py --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now music-player
```

### 嵌入为 popup

```html
<a href="#" onclick="window.open('http://<host>:8080','music','width=420,height=640');return false">
  打开播放器
</a>
```

## 使用

### 添加歌曲

在 `music/歌单名/` 下为每首歌创建一个文件夹，放入音频文件：

```
music/
└── 我的歌单/
    ├── 追光者-岑宁儿/
    │   ├── 追光者.mp3
    │   └── 追光者.lrc
    └── 起风了-买辣椒也用券/
        └── qifengle.m4a       ← 文件名随意，文件夹名决定显示名
```

- 音频格式支持：MP3、M4A、AAC、WAV、OGG、FLAC
- 文件夹名即为歌曲显示名
- 歌词文件（`.lrc`）可选，放入同一文件夹即可

### 歌词格式

标准 LRC 格式。同一时间戳出现两行时，前一行视为原文、后一行视为翻译：

```
[00:15.28]曾羡慕闲云野鹤 作客人间
[00:15.28]I once envied the wandering clouds and wild cranes
[00:18.28]寄情于天地有灵 草木无邪
[00:18.28]Entrusting feelings to the spirits of heaven and earth
```

### B站下载工具

内置批量下载脚本，用于从B站收藏夹搬运音乐。需额外安装 Node.js 和 FFmpeg。

```bash
python download/download.py
```

详见 `download/` 目录。

## 技术栈

- 前端：HTML5、CSS3、JavaScript（零外部依赖）
- 后端：Python Flask
- 音频：HTML5 Audio API

## 许可证

MIT License
