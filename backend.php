<?php
header('Content-Type: application/json; charset=utf-8');

if ($_GET['action'] === 'getFolders') {
    try {
        $folders = array_filter(glob('music/*'), 'is_dir');
        $folderNames = array_map('basename', $folders);
        echo json_encode($folderNames, JSON_UNESCAPED_UNICODE);
    } catch (Exception $e) {
        echo json_encode(['error' => '获取文件夹失败: ' . $e->getMessage()]);
    }
    exit;
}

if ($_GET['action'] === 'getSongs') {
    try {
        $folder = $_GET['folder'];
        $folderPath = "music/$folder";
        
        // 检查文件夹是否存在
        if (!is_dir($folderPath)) {
            echo json_encode(['error' => '文件夹不存在: ' . $folderPath]);
            exit;
        }
        
        // 获取所有文件
        $allFiles = scandir($folderPath);
        $audioFiles = [];
        
        foreach ($allFiles as $file) {
            if ($file === '.' || $file === '..') continue;
            
            $filePath = $folderPath . '/' . $file;
            if (is_file($filePath)) {
                // 检查是否为音频文件
                $extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
                if (in_array($extension, ['mp3', 'm4a', 'aac', 'wav', 'ogg'])) {
                    // 确保文件名编码正确
                    $fileName = mb_convert_encoding($file, 'UTF-8', 'auto');
                    $audioFiles[] = $fileName;
                }
            }
        }
        
        // 按文件名排序
        sort($audioFiles);
        
        echo json_encode($audioFiles, JSON_UNESCAPED_UNICODE);
        
    } catch (Exception $e) {
        echo json_encode(['error' => '获取歌曲列表失败: ' . $e->getMessage()]);
    }
    exit;
}

if ($_GET['action'] === 'getLyrics') {
    try {
        $folder = $_GET['folder'];
        $songName = $_GET['song'];
        
        // 移除文件扩展名
        $baseName = pathinfo($songName, PATHINFO_FILENAME);
        
        // 尝试多个可能的歌词文件位置
        $possibleLyricsFiles = [
            "music/$folder/$baseName.lrc",                    // 同文件夹
            "music/$folder/lyrics/$baseName.lrc",             // 子歌词文件夹
            "lyrics/$folder/$baseName.lrc",                   // 独立歌词文件夹
            "music/lyrics/$folder/$baseName.lrc"              // 全局歌词文件夹
        ];
        
        $lyricsFile = null;
        foreach ($possibleLyricsFiles as $file) {
            if (file_exists($file)) {
                $lyricsFile = $file;
                break;
            }
        }
        
        if ($lyricsFile) {
            $lyrics = file_get_contents($lyricsFile);
            // 确保编码为UTF-8
            $lyrics = mb_convert_encoding($lyrics, 'UTF-8', 'auto');
            echo json_encode(['success' => true, 'lyrics' => $lyrics], JSON_UNESCAPED_UNICODE);
        } else {
            echo json_encode([
                'success' => false, 
                'message' => '歌词文件不存在',
                'searched_paths' => $possibleLyricsFiles
            ]);
        }
    } catch (Exception $e) {
        echo json_encode(['error' => '获取歌词失败: ' . $e->getMessage()]);
    }
    exit;
}

// 如果没有匹配的action，返回错误
echo json_encode(['error' => '无效的请求']);
?>
