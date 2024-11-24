<?php
header('Content-Type: application/json');

// 根目录的音乐文件夹
$root_dir = './music';

// 获取所有文件夹
$folders = array_filter(glob($root_dir . '/*'), 'is_dir');
$result = [];

foreach ($folders as $folder) {
    $folder_name = basename($folder);
    $files = array_filter(glob("$folder/*"), function($file) {
        return preg_match('/\.(mp3|wav|ogg)$/i', $file);
    });

    $result[] = [
        'folder' => $folder_name,
        'files' => array_map('basename', $files)
    ];
}

echo json_encode($result);
