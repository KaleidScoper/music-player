<?php
if ($_GET['action'] === 'getFolders') {
    $folders = array_filter(glob('music/*'), 'is_dir');
    echo json_encode(array_map('basename', $folders));
    exit;
}

if ($_GET['action'] === 'getSongs') {
    $folder = $_GET['folder'];
    $files = array_filter(glob("music/$folder/*"), function($file) {
        return preg_match('/\.(mp3|ogg|wav)$/i', $file);
    });
    // 将文件名转换为 UTF-8
    $files = array_map(function($file) {
        return mb_convert_encoding(basename($file), 'UTF-8', 'auto');
    }, $files);
    echo json_encode(array_map('basename', $files));
    exit;
}
