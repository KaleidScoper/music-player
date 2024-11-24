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
    echo json_encode(array_map('basename', $files));
    exit;
}
