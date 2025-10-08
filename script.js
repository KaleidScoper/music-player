document.addEventListener("DOMContentLoaded", () => {
    const folderSelect = document.getElementById("folder-select");
    const songList = document.getElementById("song-list");
    const audioPlayer = document.getElementById("audio-player");
    const nowPlayingTitle = document.getElementById("now-playing-title");
    const pagination = document.getElementById("pagination");
    const lyricsDisplay = document.getElementById("lyrics-display");
    const themeSelect = document.getElementById("theme-select");
    const lyricsContainer = document.getElementById("lyrics-container");
    const crossPlaylistToggle = document.getElementById("cross-playlist-toggle");
    const playlistSelection = document.getElementById("playlist-selection");
    const playlistCheckboxes = document.getElementById("playlist-checkboxes");
    const applyCrossPlaylistBtn = document.getElementById("apply-cross-playlist");
    const toggleTranslationCheckbox = document.getElementById("toggle-translation");

    let songs = [];
    let allSongs = []; // 存储所有歌单的歌曲
    let playbackMode = "sequential";
    let currentIndex = 0;
    let currentPage = 1;
    const songsPerPage = 10;
    let lyricsData = [];
    let lastLyricIndex = -1; // 记录上一次高亮的歌词索引，避免重复滚动
    let showTranslation = true;
    let prevLineEl = null;
    let currentLineEl = null;
    let nextLineEl = null;
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
                } else {
                    songs = data.map(song => ({
                        name: song,
                        folder: folder,
                        fullPath: `${folder}/${song}`
                    }));
                }
                
                currentPage = 1;
                renderSongList();
                renderPagination();
                clearLyrics();
            })
            .catch(error => {
                console.error('加载歌曲失败:', error);
                songs = [];
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
            
            // 支持 [mm:ss], [mm:ss.xx], [mm:ss.xxx]，以及 [mm:ss:xx]
            const timeRegex = /\[(\d{2}):(\d{2})(?:[.:](\d{2,3}))?\]/g;
            const matches = [...line.matchAll(timeRegex)];
            
            if (matches.length > 0) {
                const text = line.replace(timeRegex, '').trim();
                if (text) {
                    for (let match of matches) {
                        const minutes = parseInt(match[1]);
                        const seconds = parseInt(match[2]);
                        const fracRaw = match[3];
                        let fractionSeconds = 0;
                        if (typeof fracRaw !== 'undefined') {
                            const frac = parseInt(fracRaw);
                            // 2 位表示百分之一秒，3 位表示千分之一秒
                            fractionSeconds = fracRaw.length === 3 ? frac / 1000 : frac / 100;
                        }
                        const time = minutes * 60 + seconds + fractionSeconds;
                        
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
        lastLyricIndex = -1;

        // 三行容器
        prevLineEl = document.createElement("div");
        prevLineEl.className = "lyrics-line lyric-prev";
        currentLineEl = document.createElement("div");
        currentLineEl.className = "lyrics-line lyric-current";
        nextLineEl = document.createElement("div");
        nextLineEl.className = "lyrics-line lyric-next";

        lyricsDisplay.appendChild(prevLineEl);
        lyricsDisplay.appendChild(currentLineEl);
        lyricsDisplay.appendChild(nextLineEl);

        // 无动画版本：无需动态滚动位移

        if (lyricsData.length === 0) {
            prevLineEl.innerHTML = "";
            currentLineEl.innerHTML = "暂无歌词";
            nextLineEl.innerHTML = "";
            return;
        }

        let idx = findCurrentLyricIndex(audioPlayer.currentTime);
        if (idx < 0) idx = 0;
        snapToIndex(idx);
    }

    function renderLyricHTML(lyric) {
        if (!LyricExists(lyric)) return "";
        const text = lyric.text || "";
        const translation = showTranslation && lyric.translation ? `<div class=\"lyrics-translation\">${escapeHTML(lyric.translation)}</div>` : "";
        return `${escapeHTML(text)}${translation}`;
    }

    function LyricExists(lyric) {
        return lyric && typeof lyric.text === 'string';
    }

    function getLyricAt(index) {
        if (index < 0 || index >= lyricsData.length) return null;
        return lyricsData[index];
    }

    function findCurrentLyricIndex(currentTime) {
        if (!lyricsData.length) return -1;
        let low = 0, high = lyricsData.length - 1, idx = -1;
        while (low <= high) {
            const mid = (low + high) >> 1;
            if (currentTime >= lyricsData[mid].time) {
                idx = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        return idx;
    }

    function snapToIndex(targetIndex) {
        // 每次更新都重绘三行（仅装饰前后行，不做轮换）
        const prevIdx = targetIndex - 1;
        const nextIdx = targetIndex + 1;
        if (!prevLineEl || !currentLineEl || !nextLineEl) return;
        prevLineEl.className = 'lyrics-line lyric-prev';
        currentLineEl.className = 'lyrics-line lyric-current';
        nextLineEl.className = 'lyrics-line lyric-next';
        prevLineEl.innerHTML = renderLyricHTML(getLyricAt(prevIdx));
        currentLineEl.innerHTML = renderLyricHTML(getLyricAt(targetIndex));
        nextLineEl.innerHTML = renderLyricHTML(getLyricAt(nextIdx));
        lastLyricIndex = targetIndex;
    }

    function updateCurrentLyric(currentTime) {
        if (!lyricsData.length || !currentLineEl) return;
        const currentIndex = findCurrentLyricIndex(currentTime);
        if (currentIndex === -1) {
            // 还未到第一句
            prevLineEl.innerHTML = "";
            currentLineEl.innerHTML = renderLyricHTML(getLyricAt(0));
            nextLineEl.innerHTML = renderLyricHTML(getLyricAt(1));
            // 动画方向：首句前保持不动
            lyricsDisplay.classList.remove('animate-up', 'animate-down');
            lastLyricIndex = -1;
            return;
        }

        // 无动画版本：不设置动画方向类

        snapToIndex(currentIndex);
    }

    function clearLyrics() {
        displayNoLyrics();
        lyricsData = [];
        lastLyricIndex = -1;
        if (lyricsContainer) {
            // 保持不可滚动
        }
    }

    function displayNoLyrics() {
        lyricsDisplay.innerHTML = "";
        lastLyricIndex = -1;

        // 渲染三行占位，但仅中间显示提示
        prevLineEl = document.createElement("div");
        prevLineEl.className = "lyrics-line lyric-prev";
        currentLineEl = document.createElement("div");
        currentLineEl.className = "lyrics-line lyric-current lyrics-empty";
        nextLineEl = document.createElement("div");
        nextLineEl.className = "lyrics-line lyric-next";

        const guide = [
            '未找到歌词',
            '',
            '添加方法：将与音频同名的 .lrc 文件放置在以下任一位置：',
            '• music/歌单/文件名.lrc',
            '• music/歌单/lyrics/文件名.lrc',
            '• lyrics/歌单/文件名.lrc',
            '• music/lyrics/歌单/文件名.lrc'
        ].join('\n');

        currentLineEl.innerHTML = `<div>${guide.replaceAll('\n', '<br/>')}</div>`;

        lyricsDisplay.appendChild(prevLineEl);
        lyricsDisplay.appendChild(currentLineEl);
        lyricsDisplay.appendChild(nextLineEl);
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
        updateCurrentLyric(audioPlayer.currentTime);
    });

    audioPlayer.addEventListener('seeking', () => {
        updateCurrentLyric(audioPlayer.currentTime);
    });

    audioPlayer.addEventListener('seeked', () => {
        updateCurrentLyric(audioPlayer.currentTime);
    });

    audioPlayer.addEventListener('loadedmetadata', () => {
        updateCurrentLyric(audioPlayer.currentTime);
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

    // 阻止用户滚动歌词容器
    if (lyricsContainer) {
        const prevent = (e) => { e.preventDefault(); };
        lyricsContainer.addEventListener('wheel', prevent, { passive: false });
        lyricsContainer.addEventListener('touchstart', prevent, { passive: false });
        lyricsContainer.addEventListener('touchmove', prevent, { passive: false });
        lyricsContainer.addEventListener('touchend', prevent, { passive: false });
    }

    // 翻译显示开关
    if (toggleTranslationCheckbox) {
        showTranslation = toggleTranslationCheckbox.checked;
        toggleTranslationCheckbox.addEventListener('change', () => {
            showTranslation = toggleTranslationCheckbox.checked;
            if (!lyricsData.length || !currentLineEl) return;
            // 以当前索引为中心重绘三行
            const idx = lastLyricIndex >= 0 ? lastLyricIndex : findCurrentLyricIndex(audioPlayer.currentTime);
            snapToIndex(idx < 0 ? 0 : idx);
        });
    }

    // HTML 转义
    function escapeHTML(str) {
        return String(str)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
}); 