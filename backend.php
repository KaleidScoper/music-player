<?php
header('Content-Type: application/json; charset=utf-8');

// 歌词缓存配置
define('LYRICS_CACHE_ENABLED', true);
define('LYRICS_CACHE_DURATION', 300); // 5分钟缓存
define('LYRICS_INDEX_CACHE_FILE', 'lyrics_index_cache.json');

// 歌词缓存类
class LyricsCache {
    private static $cache = [];
    private static $indexCache = null;
    
    public static function get($key) {
        if (!LYRICS_CACHE_ENABLED) return null;
        
        if (isset(self::$cache[$key])) {
            $data = self::$cache[$key];
            if (time() - $data['timestamp'] < LYRICS_CACHE_DURATION) {
                return $data['content'];
            }
            unset(self::$cache[$key]);
        }
        return null;
    }
    
    public static function set($key, $content) {
        if (!LYRICS_CACHE_ENABLED) return;
        
        self::$cache[$key] = [
            'content' => $content,
            'timestamp' => time()
        ];
    }
    
    public static function getLyricsIndex($folder) {
        if (self::$indexCache === null) {
            self::loadLyricsIndex();
        }
        
        return isset(self::$indexCache[$folder]) ? self::$indexCache[$folder] : [];
    }
    
    private static function loadLyricsIndex() {
        if (file_exists(LYRICS_INDEX_CACHE_FILE)) {
            $cacheData = json_decode(file_get_contents(LYRICS_INDEX_CACHE_FILE), true);
            if ($cacheData && time() - $cacheData['timestamp'] < LYRICS_CACHE_DURATION) {
                self::$indexCache = $cacheData['index'];
                return;
            }
        }
        
        // 重新构建索引
        self::buildLyricsIndex();
    }
    
    private static function buildLyricsIndex() {
        $index = [];
        
        // 仅扫描统一歌词目录
        if (is_dir('lyrics')) {
            $folders = array_filter(glob('lyrics/*'), 'is_dir');
            foreach ($folders as $folder) {
                $folderName = basename($folder);
                $index[$folderName] = [];
                
                $lrcFiles = glob($folder . '/*.lrc');
                foreach ($lrcFiles as $lrcFile) {
                    $fileName = basename($lrcFile, '.lrc');
                    $index[$folderName][$fileName] = $lrcFile;
                }
            }
        }
        
        self::$indexCache = $index;
        
        // 保存到缓存文件
        $cacheData = [
            'timestamp' => time(),
            'index' => $index
        ];
        file_put_contents(LYRICS_INDEX_CACHE_FILE, json_encode($cacheData, JSON_UNESCAPED_UNICODE));
    }
    
    public static function clearCache() {
        self::$cache = [];
        self::$indexCache = null;
        if (file_exists(LYRICS_INDEX_CACHE_FILE)) {
            unlink(LYRICS_INDEX_CACHE_FILE);
        }
    }
}

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
        
        // 生成缓存键
        $cacheKey = "lyrics_{$folder}_{$songName}";
        
        // 尝试从缓存获取
        $cachedResult = LyricsCache::get($cacheKey);
        if ($cachedResult !== null) {
            echo json_encode($cachedResult, JSON_UNESCAPED_UNICODE);
            exit;
        }
        
        // 移除文件扩展名
        $baseName = pathinfo($songName, PATHINFO_FILENAME);
        
        // 提取歌曲名称部分（第一个"-"之前的部分）
        $songTitle = explode('-', $baseName)[0];
        
        // 使用索引快速查找歌词文件（仅查找统一歌词目录）
        $lyricsIndex = LyricsCache::getLyricsIndex($folder);
        $lyricsFile = null;
        
        // 按优先级查找（仅使用统一歌词目录）
        $searchKeys = [$baseName, $songTitle];
        foreach ($searchKeys as $key) {
            if (isset($lyricsIndex[$key])) {
                $lyricsFile = $lyricsIndex[$key];
                break;
            }
        }
        
        $result = null;
        if ($lyricsFile) {
            $lyrics = file_get_contents($lyricsFile);
            // 确保编码为UTF-8
            $lyrics = mb_convert_encoding($lyrics, 'UTF-8', 'auto');
            $result = ['success' => true, 'lyrics' => $lyrics];
        } else {
            $result = [
                'success' => false, 
                'message' => '歌词文件不存在'
            ];
        }
        
        // 缓存结果
        LyricsCache::set($cacheKey, $result);
        
        echo json_encode($result, JSON_UNESCAPED_UNICODE);
    } catch (Exception $e) {
        echo json_encode(['error' => '获取歌词失败: ' . $e->getMessage()]);
    }
    exit;
}

if ($_GET['action'] === 'clearLyricsCache') {
    try {
        LyricsCache::clearCache();
        echo json_encode(['success' => true, 'message' => '歌词缓存已清除']);
    } catch (Exception $e) {
        echo json_encode(['error' => '清除缓存失败: ' . $e->getMessage()]);
    }
    exit;
}

if ($_GET['action'] === 'getBatchLyrics') {
    try {
        $folder = $_GET['folder'];
        $songNames = json_decode($_GET['songs'], true);
        
        if (!is_array($songNames)) {
            echo json_encode(['error' => '无效的歌曲列表']);
            exit;
        }
        
        $results = [];
        foreach ($songNames as $songName) {
            $cacheKey = "lyrics_{$folder}_{$songName}";
            $cachedResult = LyricsCache::get($cacheKey);
            
            if ($cachedResult !== null) {
                $results[$songName] = $cachedResult;
            } else {
                // 快速查找逻辑
                $baseName = pathinfo($songName, PATHINFO_FILENAME);
                $songTitle = explode('-', $baseName)[0];
                
                $lyricsIndex = LyricsCache::getLyricsIndex($folder);
                $lyricsFile = null;
                
                $searchKeys = [$baseName, $songTitle];
                foreach ($searchKeys as $key) {
                    if (isset($lyricsIndex[$key])) {
                        $lyricsFile = $lyricsIndex[$key];
                        break;
                    }
                }
                
                $result = null;
                if ($lyricsFile) {
                    $lyrics = file_get_contents($lyricsFile);
                    $lyrics = mb_convert_encoding($lyrics, 'UTF-8', 'auto');
                    $result = ['success' => true, 'lyrics' => $lyrics];
                } else {
                    $result = ['success' => false, 'message' => '歌词文件不存在'];
                }
                
                LyricsCache::set($cacheKey, $result);
                $results[$songName] = $result;
            }
        }
        
        echo json_encode(['success' => true, 'results' => $results], JSON_UNESCAPED_UNICODE);
    } catch (Exception $e) {
        echo json_encode(['error' => '批量获取歌词失败: ' . $e->getMessage()]);
    }
    exit;
}

// 如果没有匹配的action，返回错误
echo json_encode(['error' => '无效的请求']);
?>
