document.addEventListener("DOMContentLoaded", () => {
    const folderSelect = document.getElementById("folder-select");
    const songList = document.getElementById("song-list");
    const audioPlayer = document.getElementById("audio-player");
    const currentFolder = document.getElementById("current-folder");
    const nowPlayingTitle = document.getElementById("now-playing-title");
    const pagination = document.getElementById("pagination");

    let songs = [];
    let currentIndex = 0;
    let currentPage = 1; // 当前页码
    const songsPerPage = 10; // 每页显示的歌曲数

    // 加载文件夹和文件
    fetch("backend.php?action=getFolders")
        .then(res => res.json())
        .then(folders => {
            folders.forEach(folder => {
                const option = document.createElement("option");
                option.value = folder;
                option.textContent = folder;
                folderSelect.appendChild(option);
            });
            loadSongs(folderSelect.value);
        });

    folderSelect.addEventListener("change", () => loadSongs(folderSelect.value));

    function loadSongs(folder) {
        fetch(`backend.php?action=getSongs&folder=${folder}`)
            .then(res => res.json())
            .then(data => {
                songs = data;
                currentFolder.textContent = folder;
                currentPage = 1; // 重置为第一页
                renderSongList();
                renderPagination();
            });
    }

    function renderSongList() {
        // 清空列表
        songList.innerHTML = "";

        // 计算当前页的起始和结束索引
        const startIndex = (currentPage - 1) * songsPerPage;
        const endIndex = Math.min(startIndex + songsPerPage, songs.length);

        // 显示当前页的歌曲
        for (let i = startIndex; i < endIndex; i++) {
            const li = document.createElement("li");
            li.textContent = songs[i];
            li.addEventListener("click", () => playSong(i));
            songList.appendChild(li);
        }
    }

    function renderPagination() {
        // 清空分页控件
        pagination.innerHTML = "";

        // 计算总页数
        const totalPages = Math.ceil(songs.length / songsPerPage);

        // 创建分页按钮
        for (let i = 1; i <= totalPages; i++) {
            const button = document.createElement("button");
            button.textContent = i;
            button.classList.toggle("active", i === currentPage);
            button.addEventListener("click", () => {
                currentPage = i;
                renderSongList();
                renderPagination();
            });
            pagination.appendChild(button);
        }
    }

    function playSong(index) {
        currentIndex = index;
        const encodedFilename = encodeURIComponent(songs[index]); // URL 编码文件名
        audioPlayer.src = `music/${folderSelect.value}/${encodedFilename}`;
        audioPlayer.play();
        nowPlayingTitle.textContent = songs[index]; // 更新当前播放的歌曲
    }
});
