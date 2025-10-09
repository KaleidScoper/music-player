# B站视频批量下载工具

由于原PowerShell脚本存在编码问题，现提供Python和批处理两个版本的替代方案。

## 使用方法

### 方案一：Python版本（推荐）

**要求：**
- Python 3.6+
- Node.js 和 npm
- FFmpeg（可选，用于格式转换）

**运行：**
```bash
# 正常模式（检查环境）
python download.py

# 跳过环境检查模式
python download.py --skip-check

# 调试模式
python download.py --debug

# 显示帮助
python download.py --help
```

**优点：**
- 跨平台兼容性好
- 错误处理更完善
- 用户交互更友好

### 方案二：批处理版本

**要求：**
- Windows系统
- Node.js 和 npm
- FFmpeg（可选，用于格式转换）

**运行：**
```bash
download.bat
```

**优点：**
- 无需Python环境
- 在Windows上运行简单

## 环境准备

1. **安装Node.js**
   - 访问 https://nodejs.org/
   - 下载并安装最新LTS版本

2. **安装FFmpeg（推荐）**
   - 访问 https://ffmpeg.org/download.html
   - 下载并配置到系统PATH

3. **安装下载工具**
   ```bash
   npm install -g bilibili-video2mp3
   ```

## 启动模式

### 1. 正常模式（默认）
```bash
python download.py
```
- 检查Node.js、npm、FFmpeg环境
- 推荐首次使用

### 2. 跳过环境检查模式
```bash
python download.py --skip-check
# 或
python download.py -s
```
- 跳过环境检查，直接开始下载
- 适用于已知环境完整的情况
- 节省启动时间

### 3. 调试模式
```bash
python download.py --debug
# 或
python download.py -d
```
- 显示详细的环境检测信息
- 帮助诊断环境问题
- 显示每个命令的执行结果

### 4. 帮助模式
```bash
python download.py --help
# 或
python download.py -h
```
- 显示所有可用参数和使用方法

## 使用步骤

1. 运行脚本
2. 按提示输入B站视频URL（每行一个）
3. 输入完成后直接按回车
4. 确认下载列表
5. 等待下载完成

## 注意事项

- 确保网络连接正常
- 某些视频可能需要登录B站账号
- 下载速度取决于网络状况
- 音频文件将保存到当前目录

## 故障排除

### 常见问题

1. **"请先安装 Node.js"**
   - 确保已正确安装Node.js
   - 检查环境变量PATH是否包含Node.js路径

2. **"未检测到 FFmpeg"**
   - 可以继续使用，但可能无法正确转换格式
   - 建议安装FFmpeg以获得最佳体验

3. **下载失败**
   - 检查网络连接
   - 确认视频URL有效
   - 某些视频可能需要登录B站账号

### 技术支持

如遇到问题，请检查：
- Node.js版本是否为最新
- 网络连接是否正常
- 视频URL是否有效
- 是否需要登录B站账号
