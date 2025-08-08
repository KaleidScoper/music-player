document.addEventListener("DOMContentLoaded", () => {
    const folderSelect = document.getElementById("folder-select");
    const songList = document.getElementById("song-list");
    const audioPlayer = document.getElementById("audio-player");
    const currentFolder = document.getElementById("current-folder");
    const nowPlayingTitle = document.getElementById("now-playing-title");
    const pagination = document.getElementById("pagination");
    const lyricsDisplay = document.getElementById("lyrics-display");
    const themeSelect = document.getElementById("theme-select");
    const crossPlaylistToggle = document.getElementById("cross-playlist-toggle");
    const playlistSelection = document.getElementById("playlist-selection");
    const playlistCheckboxes = document.getElementById("playlist-checkboxes");
    const applyCrossPlaylistBtn = document.getElementById("apply-cross-playlist");

    let songs = [];
    let allSongs = []; // 存储所有歌单的歌曲
    let playbackMode = "sequential";
    let currentIndex = 0;
    let currentPage = 1;
    const songsPerPage = 10;
    let lyricsData = [];
    let crossPlaylistEnabled = false;
    let selectedPlaylists = [];
    let allFolders = [];

    // 配色方案功能
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('selectedTheme', theme);
    }

    // 加载保存的配色方案，默认为暗色主题
    const savedTheme = localStorage.getItem('selectedTheme') || 'dark';
    setTheme(savedTheme);
    themeSelect.value = savedTheme;

    themeSelect.addEventListener("change", function() {
        setTheme(this.value);
    });

    // 自选歌单播放功能
    crossPlaylistToggle.addEventListener("change", function() {
        crossPlaylistEnabled = this.checked;
        playlistSelection.style.display = crossPlaylistEnabled ? 'block' : 'none';
        
        if (crossPlaylistEnabled) {
            loadAllSongs();
        } else {
            // 恢复到单歌单模式
            songs = allSongs.filter(song => song.folder === folderSelect.value);
            currentPage = 1;
            renderSongList();
            renderPagination();
        }
    });

    // 加载所有歌单的歌曲
    function loadAllSongs() {
        allSongs = [];
        const promises = allFolders.map(folder => 
            fetch(`backend.php?action=getSongs&folder=${encodeURIComponent(folder)}`)
                .then(res => res.json())
                .then(data => {
                    if (!data.error) {
                        return data.map(song => ({
                            name: song,
                            folder: folder,
                            fullPath: `${folder}/${song}`
                        }));
                    }
                    return [];
                })
                .catch(error => {
                    console.error(`加载歌单 ${folder} 失败:`, error);
                    return [];
                })
        );

        Promise.all(promises).then(results => {
            allSongs = results.flat();
            updatePlaylistCheckboxes();
        });
    }

    // 更新歌单选择复选框
    function updatePlaylistCheckboxes() {
        playlistCheckboxes.innerHTML = '';
        
        allFolders.forEach(folder => {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'playlist-checkbox';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `playlist-${folder}`;
            checkbox.value = folder;
            checkbox.checked = selectedPlaylists.includes(folder);
            
            const label = document.createElement('label');
            label.htmlFor = `playlist-${folder}`;
            label.textContent = folder;
            
            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(label);
            playlistCheckboxes.appendChild(checkboxDiv);
        });
    }

    // 应用自选歌单播放设置
    applyCrossPlaylistBtn.addEventListener("click", function() {
        selectedPlaylists = [];
        const checkboxes = playlistCheckboxes.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            selectedPlaylists.push(checkbox.value);
        });

        if (selectedPlaylists.length > 0) {
            songs = allSongs.filter(song => selectedPlaylists.includes(song.folder));
            currentPage = 1;
            renderSongList();
            renderPagination();
            console.log(`自选歌单播放已启用，包含 ${selectedPlaylists.length} 个歌单，共 ${songs.length} 首歌曲`);
        } else {
            alert('请至少选择一个歌单！');
        }
    });

    // 加载文件夹和文件
    fetch("backend.php?action=getFolders")
        .then(res => res.json())
        .then(folders => {
            console.log('获取到的文件夹:', folders);
            if (folders.error) {
                console.error('获取文件夹失败:', folders.error);
                return;
            }
            
            allFolders = folders;
            
            folders.forEach(folder => {
                const option = document.createElement("option");
                option.value = folder;
                option.textContent = folder;
                folderSelect.appendChild(option);
            });
            
            if (folders.length > 0) {
                loadSongs(folders[0]);
                loadAllSongs(); // 预加载所有歌单
            }
        })
        .catch(error => {
            console.error('加载文件夹失败:', error);
        });

    folderSelect.addEventListener("change", () => {
        if (!crossPlaylistEnabled) {
            loadSongs(folderSelect.value);
        }
    });

    function loadSongs(folder) {
        console.log('正在加载歌单:', folder);
        fetch(`backend.php?action=getSongs&folder=${encodeURIComponent(folder)}`)
            .then(res => res.json())
            .then(data => {
                console.log('获取到的歌曲:', data);
                
                if (data.error) {
                    console.error('获取歌曲列表失败:', data.error);
                    songs = [];
                    currentFolder.textContent = folder + ' (加载失败)';
                } else {
                    songs = data.map(song => ({
                        name: song,
                        folder: folder,
                        fullPath: `${folder}/${song}`
                    }));
                    currentFolder.textContent = folder;
                }
                
                currentPage = 1;
                renderSongList();
                renderPagination();
                clearLyrics();
            })
            .catch(error => {
                console.error('加载歌曲失败:', error);
                songs = [];
                currentFolder.textContent = folder + ' (加载失败)';
                renderSongList();
                renderPagination();
                clearLyrics();
            });
    }

    function renderSongList() {
        songList.innerHTML = "";
        
        if (songs.length === 0) {
            const li = document.createElement("li");
            li.textContent = "暂无歌曲或加载失败";
            li.style.textAlign = "center";
            li.style.color = "#666";
            li.style.fontStyle = "italic";
            songList.appendChild(li);
            return;
        }
        
        const startIndex = (currentPage - 1) * songsPerPage;
        const endIndex = Math.min(startIndex + songsPerPage, songs.length);

        for (let i = startIndex; i < endIndex; i++) {
            const li = document.createElement("li");
            const song = songs[i];
            
            // 显示歌曲名称和所属歌单
            if (crossPlaylistEnabled) {
                li.textContent = `${song.name} (${song.folder})`;
            } else {
                li.textContent = song.name;
            }
            
            li.addEventListener("click", () => playSong(i));
            
            if (i === currentIndex) {
                li.classList.add("playing");
            }
            
            songList.appendChild(li);
        }
    }

    function renderPagination() {
        pagination.innerHTML = "";
        
        if (songs.length === 0) return;
        
        const totalPages = Math.ceil(songs.length / songsPerPage);

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

    function parseLyrics(lyricsText) {
        const lines = lyricsText.split('\n');
        const lyrics = [];
        
        for (let line of lines) {
            line = line.trim();
            if (!line) continue;
            
            const timeRegex = /\[(\d{2}):(\d{2})[.:](\d{2})\]/g;
            const matches = [...line.matchAll(timeRegex)];
            
            if (matches.length > 0) {
                const text = line.replace(timeRegex, '').trim();
                if (text) {
                    for (let match of matches) {
                        const minutes = parseInt(match[1]);
                        const seconds = parseInt(match[2]);
                        const centiseconds = parseInt(match[3]);
                        const time = minutes * 60 + seconds + centiseconds / 100;
                        
                        lyrics.push({
                            time: time,
                            text: text,
                            originalText: text
                        });
                    }
                }
            }
        }
        
        lyrics.sort((a, b) => a.time - b.time);
        
        const processedLyrics = [];
        for (let i = 0; i < lyrics.length; i++) {
            const current = lyrics[i];
            const next = lyrics[i + 1];
            
            if (next && Math.abs(current.time - next.time) < 0.1) {
                processedLyrics.push({
                    time: current.time,
                    text: current.text,
                    translation: next.text
                });
                i++;
            } else {
                processedLyrics.push({
                    time: current.time,
                    text: current.text,
                    translation: null
                });
            }
        }
        
        return processedLyrics;
    }

    function displayLyrics() {
        lyricsDisplay.innerHTML = "";
        
        if (lyricsData.length === 0) {
            lyricsDisplay.innerHTML = '<div class="lyrics-line">暂无歌词</div>';
            return;
        }
        
        lyricsData.forEach((lyric, index) => {
            const lineDiv = document.createElement("div");
            lineDiv.className = "lyrics-line";
            lineDiv.innerHTML = lyric.text;
            
            if (lyric.translation) {
                const translationDiv = document.createElement("div");
                translationDiv.className = "lyrics-translation";
                translationDiv.textContent = lyric.translation;
                lineDiv.appendChild(translationDiv);
            }
            
            lyricsDisplay.appendChild(lineDiv);
        });
    }

    function updateCurrentLyric(currentTime) {
        const lines = lyricsDisplay.querySelectorAll('.lyrics-line');
        lines.forEach(line => line.classList.remove('active'));
        
        let currentLyricIndex = -1;
        for (let i = 0; i < lyricsData.length; i++) {
            if (currentTime >= lyricsData[i].time) {
                currentLyricIndex = i;
            } else {
                break;
            }
        }
        
        if (currentLyricIndex >= 0 && currentLyricIndex < lines.length) {
            lines[currentLyricIndex].classList.add('active');
            
            const activeLine = lines[currentLyricIndex];
            const container = document.querySelector('.lyrics-container');
            const containerHeight = container.clientHeight;
            const lineTop = activeLine.offsetTop;
            const lineHeight = activeLine.clientHeight;
            
            container.scrollTop = lineTop - containerHeight / 2 + lineHeight / 2;
        }
    }

    function clearLyrics() {
        lyricsDisplay.innerHTML = "";
        lyricsData = [];
    }

    function loadLyrics(songName, folder) {
        console.log('正在加载歌词:', folder, songName);
        
        fetch(`backend.php?action=getLyrics&folder=${encodeURIComponent(folder)}&song=${encodeURIComponent(songName)}`)
            .then(res => res.json())
            .then(data => {
                console.log('歌词加载结果:', data);
                
                if (data.success) {
                    lyricsData = parseLyrics(data.lyrics);
                    displayLyrics();
                } else {
                    console.log('歌词文件不存在:', data.message);
                    clearLyrics();
                }
            })
            .catch(error => {
                console.error('加载歌词失败:', error);
                clearLyrics();
            });
    }

    function playSong(index) {
        if (index < 0 || index >= songs.length) {
            console.error('无效的歌曲索引:', index);
            return;
        }
        
        currentIndex = index;
        const song = songs[index];
        const songName = song.name;
        const folder = song.folder;
        const encodedFilename = encodeURIComponent(songName);
        const audioUrl = `music/${folder}/${encodedFilename}`;
        
        console.log('播放歌曲:', audioUrl);
        
        audioPlayer.src = audioUrl;
        audioPlayer.play().catch(error => {
            console.error('播放失败:', error);
        });
        
        nowPlayingTitle.textContent = crossPlaylistEnabled ? 
            `${songName} (${folder})` : songName;
        
        loadLyrics(songName, folder);
        
        const songPage = Math.floor(index / songsPerPage) + 1;
        if (songPage !== currentPage) {
            currentPage = songPage;
            renderSongList();
            renderPagination();
        } else {
            renderSongList();
        }
    }

    function setActiveButton(buttonId) {
        document.querySelectorAll(".playback-options button").forEach(button => {
            button.classList.remove("active");
        });
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

    audioPlayer.addEventListener("timeupdate", () => {
        if (lyricsData.length > 0) {
            updateCurrentLyric(audioPlayer.currentTime);
        }
    });

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

    setActiveButton("btn-sequential");
}); 