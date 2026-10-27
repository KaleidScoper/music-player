# 音乐播放器B站下载功能完整集成方案

> **已废弃**：本文是早期「PHP 集成 + npx bv2mp3」方案，未实施，也不建议再采用。
> 现行方案见 [`download/download.py`](download.py)（yt-dlp 版）与 [`doc/bilibili-audio-source.md`](../doc/bilibili-audio-source.md)。

## 📋 项目概述

将现有的独立Python下载脚本(`download.py`)集成到Web音乐播放器中，实现图形化的B站视频下载功能，同时保留原脚本作为备用方案。

## 🎯 设计目标

- ✅ 保留原Python脚本的独立性
- ✅ 用PHP重写核心下载逻辑
- ✅ 提供友好的Web界面
- ✅ 支持VPS部署环境
- ✅ 与现有播放器无缝集成
- ✅ 整合为单个文件方案

## 🏗 技术架构

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面       │    │   PHP后端API    │    │   下载服务       │
│                 │    │                 │    │                 │
│ • 添加歌曲按钮   │◄──►│ • 环境检查      │◄──►│ • bv2mp3工具    │
│ • URL输入表单    │    │ • 下载管理      │    │ • FFmpeg转换    │
│ • 进度显示      │    │ • 文件管理      │    │ • 文件移动      │
│ • 歌单选择      │    │ • 错误处理      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 文件结构

```
music_player/
├── download/
│   ├── download.py              # 原Python脚本（保留）
│   └── download_integration.php # 新增：完整集成文件
├── music/                       # 音乐文件目录
├── backend.php                 # 现有后端API
├── index.html                   # 主页面（需要修改）
├── script.js                    # 前端脚本（需要修改）
└── style.css                    # 样式文件（需要修改）
```

## 🔧 完整实现方案

### 1. 创建 `download/download_integration.php`

这个文件包含所有后端逻辑、前端代码和样式，实现完整功能：

```php
<?php
/**
 * 音乐播放器B站下载功能完整集成
 * 包含后端API、前端界面和样式
 */

// 如果是API请求，处理API逻辑
if (isset($_GET['action']) || isset($_POST['action'])) {
    header('Content-Type: application/json; charset=utf-8');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    
    // 处理预检请求
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        exit(0);
    }
    
    // API处理逻辑
    $api = new DownloadAPI();
    $response = $api->handleRequest();
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit;
}

// 如果是页面请求，输出HTML页面
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B站下载功能测试</title>
    <style>
        /* 完整样式代码 */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 28px;
        }
        
        .content {
            padding: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress-container {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 15px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .result-container {
            margin-top: 20px;
            padding: 20px;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 10px;
            display: none;
        }
        
        .error-container {
            margin-top: 20px;
            padding: 20px;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 10px;
            display: none;
        }
        
        .playlist-selector {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .playlist-selector select {
            flex: 1;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .url-count {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #28a745;
        }
        
        .status-dot.error {
            background: #dc3545;
        }
        
        .status-dot.warning {
            background: #ffc107;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fa fa-download"></i> B站视频下载功能</h1>
            <p>为音乐播放器添加B站视频下载功能</p>
        </div>
        
        <div class="content">
            <!-- 环境检查 -->
            <div class="form-group">
                <label>环境检查</label>
                <div class="status-indicator">
                    <div class="status-dot" id="env-status"></div>
                    <span id="env-text">检查中...</span>
                </div>
            </div>
            
            <!-- 下载表单 -->
            <form id="download-form">
                <div class="form-group">
                    <label for="video-urls">B站视频链接：</label>
                    <textarea 
                        id="video-urls" 
                        placeholder="请输入B站视频链接，每行一个&#10;支持格式：&#10;• https://www.bilibili.com/video/BV1xxx&#10;• https://b23.tv/xxx&#10;• 直接粘贴分享文本"
                        rows="6"
                    ></textarea>
                    <div class="url-count">已输入 0 个链接</div>
                </div>
                
                <div class="form-group">
                    <label for="target-playlist">保存到歌单：</label>
                    <div class="playlist-selector">
                        <select id="target-playlist">
                            <option value="">选择歌单</option>
                        </select>
                        <button type="button" id="create-playlist-btn" class="btn-secondary">
                            <i class="fa fa-plus"></i> 新建歌单
                        </button>
                    </div>
                </div>
                
                <div class="form-group">
                    <button type="submit" id="start-download" class="btn" disabled>
                        <i class="fa fa-download"></i> 开始下载
                    </button>
                </div>
            </form>
            
            <!-- 进度显示 -->
            <div id="download-progress" class="progress-container">
                <h4>下载进度</h4>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div class="progress-text">准备中...</div>
            </div>
            
            <!-- 结果显示 -->
            <div id="download-result" class="result-container">
                <h4>下载结果</h4>
                <div class="result-content"></div>
            </div>
            
            <!-- 错误显示 -->
            <div id="download-error" class="error-container">
                <h4>错误信息</h4>
                <div class="error-content"></div>
            </div>
        </div>
    </div>

    <script>
        // 完整JavaScript代码
        class DownloadManager {
            constructor() {
                this.isDownloading = false;
                this.init();
            }
            
            init() {
                this.bindEvents();
                this.checkEnvironment();
                this.loadPlaylists();
            }
            
            bindEvents() {
                // 表单提交
                document.getElementById('download-form').addEventListener('submit', (e) => this.handleSubmit(e));
                
                // URL输入监听
                document.getElementById('video-urls').addEventListener('input', () => this.updateUrlCount());
                
                // 歌单选择监听
                document.getElementById('target-playlist').addEventListener('change', () => this.updateSubmitButton());
                
                // 新建歌单按钮
                document.getElementById('create-playlist-btn').addEventListener('click', () => this.showCreatePlaylistDialog());
            }
            
            async checkEnvironment() {
                try {
                    const response = await fetch('?action=checkEnvironment');
                    const result = await response.json();
                    
                    const statusDot = document.getElementById('env-status');
                    const statusText = document.getElementById('env-text');
                    
                    if (result.success && result.data.allPassed) {
                        statusDot.className = 'status-dot';
                        statusText.textContent = '环境检查通过';
                    } else {
                        statusDot.className = 'status-dot warning';
                        statusText.textContent = '部分依赖缺失，可能影响下载功能';
                    }
                } catch (error) {
                    const statusDot = document.getElementById('env-status');
                    const statusText = document.getElementById('env-text');
                    statusDot.className = 'status-dot error';
                    statusText.textContent = '环境检查失败';
                }
            }
            
            async loadPlaylists() {
                try {
                    const response = await fetch('?action=getPlaylists');
                    const result = await response.json();
                    
                    if (result.success) {
                        const select = document.getElementById('target-playlist');
                        select.innerHTML = '<option value="">选择歌单</option>';
                        
                        result.data.forEach(playlist => {
                            const option = document.createElement('option');
                            option.value = playlist;
                            option.textContent = playlist;
                            select.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('加载歌单失败：', error);
                }
            }
            
            async handleSubmit(e) {
                e.preventDefault();
                
                const urls = this.getUrls();
                const playlist = document.getElementById('target-playlist').value;
                
                if (urls.length === 0) {
                    this.showError('请输入至少一个视频链接');
                    return;
                }
                
                if (!playlist) {
                    this.showError('请选择目标歌单');
                    return;
                }
                
                await this.startDownload(urls, playlist);
            }
            
            getUrls() {
                const text = document.getElementById('video-urls').value;
                const lines = text.split('\n').map(line => line.trim()).filter(line => line);
                
                const urls = [];
                const urlPatterns = [
                    /https?:\/\/(www\.)?bilibili\.com\/video\/[A-Za-z0-9_\-]+/g,
                    /https?:\/\/(www\.)?b23\.tv\/[A-Za-z0-9_\-]+/g
                ];
                
                lines.forEach(line => {
                    urlPatterns.forEach(pattern => {
                        const matches = line.match(pattern);
                        if (matches) {
                            urls.push(...matches);
                        }
                    });
                });
                
                return [...new Set(urls)];
            }
            
            async startDownload(urls, playlist) {
                this.isDownloading = true;
                this.showProgress();
                this.updateProgress(0, '准备下载...');
                
                try {
                    const response = await fetch('', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            action: 'download',
                            urls: urls,
                            playlist: playlist
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.updateProgress(100, '下载完成！');
                        this.showResult(result.data);
                    } else {
                        this.showError('下载失败：' + result.message);
                    }
                } catch (error) {
                    console.error('下载错误：', error);
                    this.showError('下载过程中出现错误：' + error.message);
                } finally {
                    this.isDownloading = false;
                    this.hideProgress();
                }
            }
            
            showCreatePlaylistDialog() {
                const name = prompt('请输入新歌单名称：');
                if (name && name.trim()) {
                    this.createPlaylist(name.trim());
                }
            }
            
            async createPlaylist(name) {
                try {
                    const response = await fetch('', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            action: 'createPlaylist',
                            name: name
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        await this.loadPlaylists();
                        document.getElementById('target-playlist').value = result.data.name;
                        this.updateSubmitButton();
                        alert('歌单创建成功！');
                    } else {
                        this.showError('创建歌单失败：' + result.message);
                    }
                } catch (error) {
                    console.error('创建歌单错误：', error);
                    this.showError('创建歌单时出现错误');
                }
            }
            
            updateUrlCount() {
                const urls = this.getUrls();
                const countElement = document.querySelector('.url-count');
                countElement.textContent = `已输入 ${urls.length} 个链接`;
                this.updateSubmitButton();
            }
            
            updateSubmitButton() {
                const urls = this.getUrls();
                const playlist = document.getElementById('target-playlist').value;
                const submitBtn = document.getElementById('start-download');
                
                const canSubmit = urls.length > 0 && playlist;
                submitBtn.disabled = !canSubmit;
            }
            
            showProgress() {
                document.getElementById('download-progress').style.display = 'block';
                this.hideResult();
                this.hideError();
            }
            
            hideProgress() {
                document.getElementById('download-progress').style.display = 'none';
            }
            
            updateProgress(percent, text) {
                const progressFill = document.querySelector('.progress-fill');
                const progressText = document.querySelector('.progress-text');
                
                progressFill.style.width = percent + '%';
                progressText.textContent = text;
            }
            
            showResult(data) {
                const container = document.getElementById('download-result');
                const content = container.querySelector('.result-content');
                
                let html = `<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <i class="fa fa-check-circle" style="color: #28a745; font-size: 20px;"></i>
                    <h4 style="margin: 0; color: #155724;">下载完成！</h4>
                </div>
                <p>成功下载 ${data.count} 个文件</p>`;
                
                if (data.files && data.files.length > 0) {
                    html += '<div style="margin-top: 15px;"><h5>下载的文件：</h5><ul>';
                    data.files.forEach(file => {
                        html += `<li><i class="fa fa-music" style="color: #667eea; margin-right: 8px;"></i> ${file}</li>`;
                    });
                    html += '</ul></div>';
                }
                
                content.innerHTML = html;
                container.style.display = 'block';
            }
            
            hideResult() {
                document.getElementById('download-result').style.display = 'none';
            }
            
            showError(message) {
                const container = document.getElementById('download-error');
                const content = container.querySelector('.error-content');
                
                content.innerHTML = `<div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fa fa-exclamation-circle" style="color: #dc3545; font-size: 20px;"></i>
                    <span style="color: #721c24;">${message}</span>
                </div>`;
                
                container.style.display = 'block';
                this.hideResult();
            }
            
            hideError() {
                document.getElementById('download-error').style.display = 'none';
            }
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            new DownloadManager();
        });
    </script>
</body>
</html>

<?php
/**
 * PHP后端API类
 */
class DownloadAPI {
    private $musicDir;
    private $tempDir;
    private $logFile;
    
    public function __construct() {
        $this->musicDir = '../music/';
        $this->tempDir = './temp/';
        $this->logFile = './download.log';
        
        // 确保临时目录存在
        if (!is_dir($this->tempDir)) {
            mkdir($this->tempDir, 0755, true);
        }
    }
    
    public function handleRequest() {
        try {
            $action = $_GET['action'] ?? $_POST['action'] ?? '';
            
            switch ($action) {
                case 'checkEnvironment':
                    return $this->checkEnvironment();
                    
                case 'download':
                    return $this->handleDownload();
                    
                case 'getPlaylists':
                    return $this->getPlaylists();
                    
                case 'createPlaylist':
                    return $this->createPlaylist();
                    
                default:
                    return $this->errorResponse('无效的操作');
            }
        } catch (Exception $e) {
            $this->logError('API错误: ' . $e->getMessage());
            return $this->errorResponse('服务器内部错误: ' . $e->getMessage());
        }
    }
    
    private function checkEnvironment() {
        $checks = [
            'node' => $this->checkCommand('node --version'),
            'npm' => $this->checkCommand('npm --version'),
            'ffmpeg' => $this->checkCommand('ffmpeg -version'),
            'python' => $this->checkCommand('python --version')
        ];
        
        $allPassed = array_reduce($checks, function($carry, $check) {
            return $carry && $check['success'];
        }, true);
        
        return $this->successResponse([
            'environment' => $checks,
            'allPassed' => $allPassed,
            'message' => $allPassed ? '环境检查通过' : '部分依赖缺失'
        ]);
    }
    
    private function handleDownload() {
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input) {
            return $this->errorResponse('无效的请求数据');
        }
        
        $urls = $input['urls'] ?? [];
        $playlist = $input['playlist'] ?? '';
        
        if (empty($urls)) {
            return $this->errorResponse('请提供至少一个视频链接');
        }
        
        if (empty($playlist)) {
            return $this->errorResponse('请选择目标歌单');
        }
        
        // 验证URL格式
        $validUrls = [];
        foreach ($urls as $url) {
            if ($this->validateBilibiliUrl($url)) {
                $validUrls[] = trim($url);
            }
        }
        
        if (empty($validUrls)) {
            return $this->errorResponse('没有有效的B站视频链接');
        }
        
        // 检查目标歌单
        $playlistPath = $this->musicDir . $playlist;
        if (!is_dir($playlistPath)) {
            return $this->errorResponse('目标歌单不存在');
        }
        
        // 执行下载
        return $this->executeDownload($validUrls, $playlist);
    }
    
    private function executeDownload($urls, $playlist) {
        $this->logInfo('开始下载: ' . implode(', ', $urls));
        
        try {
            // 构建下载命令
            $command = $this->buildDownloadCommand($urls);
            
            // 执行下载
            $output = [];
            $returnCode = 0;
            exec($command . ' 2>&1', $output, $returnCode);
            
            if ($returnCode !== 0) {
                $this->logError('下载命令执行失败: ' . implode("\n", $output));
                return $this->errorResponse('下载失败: ' . implode("\n", $output));
            }
            
            // 移动文件到目标歌单
            $movedFiles = $this->moveFilesToPlaylist($playlist);
            
            if (empty($movedFiles)) {
                return $this->errorResponse('未找到下载的音频文件');
            }
            
            $this->logInfo('下载完成: ' . implode(', ', $movedFiles));
            
            return $this->successResponse([
                'message' => '下载完成',
                'files' => $movedFiles,
                'count' => count($movedFiles)
            ]);
            
        } catch (Exception $e) {
            $this->logError('下载过程出错: ' . $e->getMessage());
            return $this->errorResponse('下载失败: ' . $e->getMessage());
        }
    }
    
    private function buildDownloadCommand($urls) {
        $command = 'npx bv2mp3';
        
        foreach ($urls as $url) {
            $command .= ' --url="' . escapeshellarg($url) . '"';
        }
        
        return $command;
    }
    
    private function moveFilesToPlaylist($playlist) {
        $targetDir = $this->musicDir . $playlist;
        $movedFiles = [];
        
        // 支持的音频格式
        $audioExtensions = ['mp3', 'm4a', 'aac', 'wav', 'flac', 'ogg'];
        
        // 扫描当前目录的音频文件
        $files = scandir('.');
        foreach ($files as $file) {
            if ($file === '.' || $file === '..') continue;
            
            $extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
            if (in_array($extension, $audioExtensions)) {
                $targetPath = $targetDir . '/' . $file;
                
                // 如果文件已存在，添加序号
                $counter = 1;
                $baseName = pathinfo($file, PATHINFO_FILENAME);
                $ext = pathinfo($file, PATHINFO_EXTENSION);
                
                while (file_exists($targetPath)) {
                    $newName = $baseName . '_' . $counter . '.' . $ext;
                    $targetPath = $targetDir . '/' . $newName;
                    $counter++;
                }
                
                // 移动文件
                if (rename($file, $targetPath)) {
                    $movedFiles[] = basename($targetPath);
                    $this->logInfo('文件已移动: ' . $file . ' -> ' . basename($targetPath));
                } else {
                    $this->logError('文件移动失败: ' . $file);
                }
            }
        }
        
        return $movedFiles;
    }
    
    private function getPlaylists() {
        try {
            $folders = array_filter(glob($this->musicDir . '*'), 'is_dir');
            $playlists = array_map('basename', $folders);
            sort($playlists);
            
            return $this->successResponse($playlists);
        } catch (Exception $e) {
            return $this->errorResponse('获取歌单失败: ' . $e->getMessage());
        }
    }
    
    private function createPlaylist() {
        $input = json_decode(file_get_contents('php://input'), true);
        $name = $input['name'] ?? '';
        
        if (empty($name)) {
            return $this->errorResponse('歌单名称不能为空');
        }
        
        // 清理名称
        $cleanName = preg_replace('/[<>:"\/\\|?*]/', '_', $name);
        $playlistPath = $this->musicDir . $cleanName;
        
        if (is_dir($playlistPath)) {
            return $this->errorResponse('歌单已存在');
        }
        
        if (mkdir($playlistPath, 0755, true)) {
            return $this->successResponse(['name' => $cleanName, 'message' => '歌单创建成功']);
        } else {
            return $this->errorResponse('歌单创建失败');
        }
    }
    
    private function checkCommand($command) {
        try {
            $output = [];
            $returnCode = 0;
            exec($command . ' 2>&1', $output, $returnCode);
            
            return [
                'success' => $returnCode === 0,
                'output' => implode("\n", $output),
                'command' => $command
            ];
        } catch (Exception $e) {
            return [
                'success' => false,
                'output' => $e->getMessage(),
                'command' => $command
            ];
        }
    }
    
    private function validateBilibiliUrl($url) {
        $patterns = [
            '/^https?:\/\/(www\.)?bilibili\.com\/video\/[A-Za-z0-9_\-]+$/',
            '/^https?:\/\/(www\.)?b23\.tv\/[A-Za-z0-9_\-]+$/'
        ];
        
        foreach ($patterns as $pattern) {
            if (preg_match($pattern, $url)) {
                return true;
            }
        }
        
        return false;
    }
    
    private function logInfo($message) {
        $this->writeLog('INFO', $message);
    }
    
    private function logError($message) {
        $this->writeLog('ERROR', $message);
    }
    
    private function writeLog($level, $message) {
        $log = date('Y-m-d H:i:s') . " [$level] $message\n";
        file_put_contents($this->logFile, $log, FILE_APPEND | LOCK_EX);
    }
    
    private function successResponse($data = null, $message = '操作成功') {
        $response = ['success' => true, 'message' => $message];
        if ($data !== null) {
            $response['data'] = $data;
        }
        return $response;
    }
    
    private function errorResponse($message, $code = 400) {
        http_response_code($code);
        return ['success' => false, 'message' => $message];
    }
}
?>
```

## 🚀 集成到现有项目

### 1. 修改 `index.html`

在 `</head>` 标签前添加：

```html
<!-- 下载功能样式 -->
<link rel="stylesheet" href="download/download_integration.php">
```

在 `</body>` 标签前添加：

```html
<!-- 下载功能脚本 -->
<script src="download/download_integration.php"></script>
```

### 2. 修改 `script.js`

在文件末尾添加：

```javascript
// 下载功能集成
class DownloadIntegration {
    constructor() {
        this.init();
    }
    
    init() {
        // 添加下载按钮
        this.addDownloadButton();
    }
    
    addDownloadButton() {
        const addSongBtn = document.createElement('button');
        addSongBtn.id = 'add-song-btn';
        addSongBtn.className = 'add-song-btn';
        addSongBtn.innerHTML = '<i class="fa fa-plus"></i> 添加歌曲';
        addSongBtn.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin: 20px 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            display: inline-flex;
            align-items: center;
            gap: 8px;
        `;
        
        // 插入到播放器容器中
        const playerContainer = document.querySelector('.player-container');
        if (playerContainer) {
            playerContainer.insertBefore(addSongBtn, playerContainer.firstChild);
        }
        
        // 绑定点击事件
        addSongBtn.addEventListener('click', () => {
            window.open('download/download_integration.php', '_blank', 'width=800,height=600');
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new DownloadIntegration();
});
```

## 🔧 部署配置

### 1. 服务器环境要求

```bash
# 必需软件
- PHP 7.4+ (支持exec函数)
- Node.js 16+
- npm
- FFmpeg
- Python 3.7+ (备用方案)

# 检查命令
php --version
node --version
npm --version
ffmpeg -version
python --version
```

### 2. 目录权限设置

```bash
# 设置目录权限
chmod 755 music/
chmod 755 music/*/
chmod 755 download/
chmod 644 download/*.php

# 设置文件权限
chmod 666 download/download.log
chmod 755 download/temp/
```

### 3. PHP配置

在 `php.ini` 中确保以下设置：

```ini
# 允许执行外部命令
allow_url_fopen = On
allow_url_include = Off

# 内存和时间限制
memory_limit = 256M
max_execution_time = 300
max_input_time = 300

# 文件上传限制
upload_max_filesize = 100M
post_max_size = 100M
```

## 🧪 测试方案

### 1. 功能测试

1. **环境检查**: 访问 `download/download_integration.php` 检查环境状态
2. **URL验证**: 输入各种B站链接格式测试
3. **下载功能**: 测试单个和批量下载
4. **文件移动**: 验证文件是否正确移动到目标歌单
5. **错误处理**: 测试各种错误情况

### 2. 集成测试

1. **按钮显示**: 检查"添加歌曲"按钮是否正常显示
2. **模态框打开**: 测试点击按钮是否正常打开下载界面
3. **歌单同步**: 验证下载后歌单是否正确更新
4. **播放器集成**: 确保新下载的歌曲可以正常播放

## 🔒 安全考虑

### 1. 输入验证

```php
// URL格式验证
private function validateBilibiliUrl($url) {
    $patterns = [
        '/^https?:\/\/(www\.)?bilibili\.com\/video\/[A-Za-z0-9_\-]+$/',
        '/^https?:\/\/(www\.)?b23\.tv\/[A-Za-z0-9_\-]+$/'
    ];
    
    foreach ($patterns as $pattern) {
        if (preg_match($pattern, $url)) {
            return true;
        }
    }
    
    return false;
}
```

### 2. 文件路径安全

```php
// 路径清理
private function sanitizePath($path) {
    return preg_replace('/[^a-zA-Z0-9\/\-_]/', '', $path);
}
```

### 3. 权限控制

```php
// 目录权限检查
private function checkDirectoryPermission($dir) {
    return is_writable($dir) && is_dir($dir);
}
```

## 📊 性能优化

### 1. 前端优化

- 防抖处理URL输入
- 异步加载歌单列表
- 进度显示优化
- 错误处理优化

### 2. 后端优化

- 命令执行超时控制
- 内存使用监控
- 文件操作优化
- 日志记录优化

### 3. 服务器优化

- PHP配置优化
- 目录权限优化
- 缓存机制
- 监控和报警

## 🔄 维护和监控

### 1. 日志记录

```php
// 日志记录
private function writeLog($level, $message) {
    $log = date('Y-m-d H:i:s') . " [$level] $message\n";
    file_put_contents($this->logFile, $log, FILE_APPEND | LOCK_EX);
}
```

### 2. 定期清理

```bash
# 清理临时文件
find download/temp/ -type f -mtime +7 -delete

# 清理日志文件
find download/ -name "*.log" -size +10M -exec truncate -s 0 {} \;
```

### 3. 监控和报警

```php
// 系统健康检查
private function checkSystemHealth() {
    $checks = [
        'disk_space' => disk_free_space('.') > 1024 * 1024 * 1024,
        'memory_usage' => memory_get_usage() < 128 * 1024 * 1024,
        'api_accessible' => $this->checkAPIHealth()
    ];
    
    return $checks;
}
```

## 📞 技术支持

### 1. 常见问题

**问题1**: 下载失败
- 检查网络连接
- 验证URL格式
- 查看错误日志

**问题2**: 权限错误
- 检查文件权限
- 验证目录权限
- 确认PHP执行权限

**问题3**: 环境问题
- 检查依赖软件
- 验证PATH环境变量
- 测试命令执行

### 2. 调试方法

```php
// 启用调试模式
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 查看日志
tail -f download/download.log
```

### 3. 联系支持

如遇到问题，请提供：
1. 错误日志内容
2. 服务器环境信息
3. 复现步骤
4. 浏览器控制台错误

---

**这个方案将整个B站下载功能整合为单个文件，包含所有必要的代码、样式和逻辑，可以直接部署使用。**

**文档版本**: v1.0  
**最后更新**: 2024年12月  
**维护者**: 项目开发团队
