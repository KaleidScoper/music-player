document.addEventListener("DOMContentLoaded", () => {
    const folderSelect = document.getElementById("folder-select");
    const songList = document.getElementById("song-list");
    const audioPlayer = document.getElementById("audio-player");
    const currentFolder = document.getElementById("current-folder");
    const nowPlayingTitle = document.getElementById("now-playing-title");

    let songs = [];
    let playbackMode = "sequential"; // 默认顺序播放
    let currentIndex = 0;

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
                songList.innerHTML = "";
                songs.forEach((song, index) => {
                    const li = document.createElement("li");
                    li.textContent = song;
                    li.addEventListener("click", () => playSong(index));
                    songList.appendChild(li);
                });
            });
    }

    function playSong(index) {
        currentIndex = index;
        const encodedFilename = encodeURIComponent(songs[index]); // URL 编码文件名
        audioPlayer.src = `music/${folderSelect.value}/${encodedFilename}`;
        audioPlayer.play();
        nowPlayingTitle.textContent = songs[index]; // 更新当前播放的歌曲
    }

    // 播放模式按钮事件处理
    function setActiveButton(buttonId) {
        // 移除所有按钮的 active 类
        document.querySelectorAll(".playback-options button").forEach(button => {
            button.classList.remove("active");
        });
        // 为当前按钮添加 active 类
        document.getElementById(buttonId).classList.add("active");
    }

    document.getElementById("btn-loop").addEventListener("click", () => {
        playbackMode = "loop";
        audioPlayer.loop = true;
        setActiveButton("btn-loop");
    });

    document.getElementById("btn-sequential").addEventListener("click", () => {
        playbackMode = "sequential";
        audioPlayer.loop = false;
        setActiveButton("btn-sequential");
    });

    document.getElementById("btn-random").addEventListener("click", () => {
        playbackMode = "random";
        audioPlayer.loop = false;
        setActiveButton("btn-random");
    });

    // 自动播放下一首歌曲
    audioPlayer.addEventListener("ended", () => {
        if (playbackMode === "loop") {
            playSong(currentIndex);
        } else if (playbackMode === "random") {
            const nextIndex = Math.floor(Math.random() * songs.length);
            playSong(nextIndex);
        } else if (playbackMode === "sequential") {
            const nextIndex = (currentIndex + 1) % songs.length;
            playSong(nextIndex);
        }
    });
});
