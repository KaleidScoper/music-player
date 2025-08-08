<?php
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>调试页面</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .error { color: red; }
        .success { color: green; }
        .info { color: blue; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>音乐播放器调试页面</h1>
    
    <div class="section">
        <h2>PHP 配置信息</h2>
        <p><strong>PHP 版本:</strong> <?php echo phpversion(); ?></p>
        <p><strong>当前目录:</strong> <?php echo getcwd(); ?></p>
        <p><strong>文件权限:</strong> <?php echo is_readable('music') ? '可读' : '不可读'; ?></p>
    </div>
    
    <div class="section">
        <h2>Music 文件夹检查</h2>
        <?php
        $musicDir = 'music';
        if (is_dir($musicDir)) {
            echo '<p class="success">✓ music 文件夹存在</p>';
            
            $folders = scandir($musicDir);
            echo '<h3>子文件夹列表:</h3>';
            echo '<ul>';
            foreach ($folders as $folder) {
                if ($folder !== '.' && $folder !== '..' && is_dir($musicDir . '/' . $folder)) {
                    echo '<li>' . htmlspecialchars($folder) . '</li>';
                    
                    // 检查每个文件夹中的文件
                    $files = scandir($musicDir . '/' . $folder);
                    $audioFiles = [];
                    $lyricsFiles = [];
                    
                    foreach ($files as $file) {
                        if ($file !== '.' && $file !== '..' && is_file($musicDir . '/' . $folder . '/' . $file)) {
                            $ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
                            if (in_array($ext, ['mp3', 'm4a', 'aac', 'wav', 'ogg'])) {
                                $audioFiles[] = $file;
                            } elseif ($ext === 'lrc') {
                                $lyricsFiles[] = $file;
                            }
                        }
                    }
                    
                    echo '<ul>';
                    echo '<li>音频文件 (' . count($audioFiles) . '): ' . implode(', ', array_slice($audioFiles, 0, 5));
                    if (count($audioFiles) > 5) echo '...';
                    echo '</li>';
                    echo '<li>歌词文件 (' . count($lyricsFiles) . '): ' . implode(', ', array_slice($lyricsFiles, 0, 5));
                    if (count($lyricsFiles) > 5) echo '...';
                    echo '</li>';
                    echo '</ul>';
                }
            }
            echo '</ul>';
        } else {
            echo '<p class="error">✗ music 文件夹不存在</p>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>API 测试</h2>
        <h3>获取文件夹列表:</h3>
        <?php
        $folders = array_filter(glob('music/*'), 'is_dir');
        $folderNames = array_map('basename', $folders);
        echo '<pre>' . json_encode($folderNames, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . '</pre>';
        ?>
        
        <h3>获取歌曲列表 (第一个文件夹):</h3>
        <?php
        if (!empty($folderNames)) {
            $firstFolder = $folderNames[0];
            $folderPath = "music/$firstFolder";
            $allFiles = scandir($folderPath);
            $audioFiles = [];
            
            foreach ($allFiles as $file) {
                if ($file === '.' || $file === '..') continue;
                
                $filePath = $folderPath . '/' . $file;
                if (is_file($filePath)) {
                    $extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
                    if (in_array($extension, ['mp3', 'm4a', 'aac', 'wav', 'ogg'])) {
                        $fileName = mb_convert_encoding($file, 'UTF-8', 'auto');
                        $audioFiles[] = $fileName;
                    }
                }
            }
            
            sort($audioFiles);
            echo '<pre>' . json_encode($audioFiles, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . '</pre>';
        } else {
            echo '<p class="error">没有找到文件夹</p>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>文件编码测试</h2>
        <?php
        if (!empty($folderNames)) {
            $firstFolder = $folderNames[0];
            $folderPath = "music/$firstFolder";
            $allFiles = scandir($folderPath);
            
            echo '<h3>文件名编码检查:</h3>';
            echo '<ul>';
            foreach ($allFiles as $file) {
                if ($file === '.' || $file === '..') continue;
                
                $originalEncoding = mb_detect_encoding($file);
                $utf8File = mb_convert_encoding($file, 'UTF-8', 'auto');
                
                echo '<li>';
                echo '原始: ' . htmlspecialchars($file) . ' (编码: ' . $originalEncoding . ')<br>';
                echo 'UTF-8: ' . htmlspecialchars($utf8File);
                echo '</li>';
            }
            echo '</ul>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>权限检查</h2>
        <?php
        echo '<p><strong>music 文件夹权限:</strong> ' . substr(sprintf('%o', fileperms('music')), -4) . '</p>';
        echo '<p><strong>backend.php 权限:</strong> ' . substr(sprintf('%o', fileperms('backend.php')), -4) . '</p>';
        echo '<p><strong>可读性:</strong> ' . (is_readable('music') ? '是' : '否') . '</p>';
        echo '<p><strong>可执行性:</strong> ' . (is_executable('music') ? '是' : '否') . '</p>';
        ?>
    </div>
</body>
</html> 