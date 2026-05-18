document.addEventListener("DOMContentLoaded", () => {
    const songList = document.getElementById("song-list");
    const audioPlayer = document.getElementById("audio-player");
    const nowPlayingTitle = document.getElementById("now-playing-title");
    const pagination = document.getElementById("pagination");
    const lyricsDisplay = document.getElementById("lyrics-display");
    const playlistCheckboxes = document.getElementById("playlist-checkboxes");
    const toggleTranslationCheckbox = document.getElementById("toggle-translation");
    const playlistDropdownBtn = document.getElementById("playlist-dropdown-btn");
    const playlistDropdownMenu = document.getElementById("playlist-dropdown-menu");
    const playlistDropdownText = document.getElementById("playlist-dropdown-text");

    let songs = [];
    let allSongs = [];
    let playbackMode = "sequential";
    let currentIndex = 0;
    let currentPage = 1;
    const songsPerPage = 10;
    let lyricsData = [];
    let lastLyricIndex = -1;
    let showTranslation = true;
    let prevLineEl = null;
    let currentLineEl = null;
    let nextLineEl = null;
    let selectedPlaylists = [];
    let allFolders = [];

    const songsCache = new Map();
    const lyricsCache = new Map();

    // ---- Dropdown ----

    function toggleDropdown() {
        if (playlistDropdownMenu.classList.contains("show")) {
            playlistDropdownMenu.classList.remove("show");
            playlistDropdownBtn.classList.remove("open");
        } else {
            playlistDropdownMenu.classList.add("show");
            playlistDropdownBtn.classList.add("open");
        }
    }

    playlistDropdownBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleDropdown();
    });

    document.addEventListener("click", (e) => {
        if (!playlistDropdownBtn.contains(e.target) && !playlistDropdownMenu.contains(e.target)) {
            playlistDropdownMenu.classList.remove("show");
            playlistDropdownBtn.classList.remove("open");
        }
    });

    playlistDropdownMenu.addEventListener("click", (e) => {
        e.stopPropagation();
    });

    function updateDropdownText() {
        const checkedBoxes = playlistCheckboxes.querySelectorAll("input[type=\"checkbox\"]:checked");
        const count = checkedBoxes.length;
        if (count === 0) {
            playlistDropdownText.textContent = "选择歌单";
        } else if (count === 1) {
            playlistDropdownText.textContent = checkedBoxes[0].nextElementSibling.textContent;
        } else {
            playlistDropdownText.textContent = `已选择 ${count} 个歌单`;
        }
    }

    // ---- Playlist selection ----

    async function updatePlaylistSelection() {
        const checkedBoxes = playlistCheckboxes.querySelectorAll("input[type=\"checkbox\"]:checked");
        selectedPlaylists = Array.from(checkedBoxes).map(cb => cb.value);

        await loadSelectedPlaylists();

        if (selectedPlaylists.length === 0) {
            songs = [];
        } else if (selectedPlaylists.length === 1) {
            songs = allSongs.filter(s => s.folder === selectedPlaylists[0]);
        } else {
            songs = allSongs.filter(s => selectedPlaylists.includes(s.folder));
        }

        updateDropdownText();
        currentPage = 1;
        renderSongList();
        renderPagination();
        clearLyrics();

        if (songs.length > 0) {
            setTimeout(() => preloadLyrics(songs, selectedPlaylists[0]), 100);
        }
    }

    async function loadSongsForPlaylist(folder) {
        if (songsCache.has(folder)) return songsCache.get(folder);

        try {
            const response = await fetch(`/api/songs?folder=${encodeURIComponent(folder)}`);
            const data = await response.json();
            if (!data.error && Array.isArray(data)) {
                songsCache.set(folder, data);
                return data;
            }
            return [];
        } catch (error) {
            console.error(`Failed to load playlist ${folder}:`, error);
            return [];
        }
    }

    async function loadSelectedPlaylists() {
        if (selectedPlaylists.length === 0) {
            allSongs = [];
            return;
        }
        const results = await Promise.all(selectedPlaylists.map(folder => loadSongsForPlaylist(folder)));
        allSongs = results.flat();
    }

    function buildPlaylistCheckboxes() {
        playlistCheckboxes.innerHTML = "";
        allFolders.forEach(folder => {
            const div = document.createElement("div");
            div.className = "playlist-checkbox";

            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.value = folder;
            cb.checked = selectedPlaylists.includes(folder);
            cb.addEventListener("change", updatePlaylistSelection);

            if (selectedPlaylists.includes(folder)) {
                div.classList.add("selected");
            }

            const label = document.createElement("span");
            label.textContent = folder;

            div.addEventListener("click", (e) => {
                e.stopPropagation();
                cb.checked = !cb.checked;
                if (cb.checked) {
                    div.classList.add("selected");
                } else {
                    div.classList.remove("selected");
                }
                cb.dispatchEvent(new Event("change"));
            });

            div.appendChild(cb);
            div.appendChild(label);
            playlistCheckboxes.appendChild(div);
        });
        updateDropdownText();
    }

    // ---- Init: load folders ----

    fetch("/api/folders")
        .then(res => res.json())
        .then(folders => {
            if (folders.error) {
                console.error("Failed to get folders:", folders.error);
                return;
            }
            allFolders = folders;
            if (folders.length > 0) {
                selectedPlaylists = [folders[0]];
                buildPlaylistCheckboxes();
                updatePlaylistSelection();
            }
        })
        .catch(error => console.error("Failed to load folders:", error));

    // ---- Song list rendering ----

    function renderSongList() {
        songList.innerHTML = "";

        if (songs.length === 0) {
            const li = document.createElement("li");
            li.className = "empty-msg";
            li.textContent = selectedPlaylists.length === 0
                ? "请选择歌单"
                : "歌单中暂无歌曲";
            songList.appendChild(li);
            return;
        }

        const startIndex = (currentPage - 1) * songsPerPage;
        const endIndex = Math.min(startIndex + songsPerPage, songs.length);

        for (let i = startIndex; i < endIndex; i++) {
            const song = songs[i];
            const li = document.createElement("li");
            li.textContent = selectedPlaylists.length > 1
                ? `${song.name} (${song.folder})`
                : song.name;
            li.addEventListener("click", () => playSong(i));
            if (i === currentIndex) li.classList.add("playing");
            songList.appendChild(li);
        }
    }

    function renderPagination() {
        pagination.innerHTML = "";
        if (songs.length === 0) return;

        const totalPages = Math.ceil(songs.length / songsPerPage);
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement("button");
            btn.textContent = i;
            if (i === currentPage) btn.classList.add("active");
            btn.addEventListener("click", () => {
                currentPage = i;
                renderSongList();
                renderPagination();
            });
            pagination.appendChild(btn);
        }
    }

    // ---- Playback ----

    function playSong(index) {
        if (index < 0 || index >= songs.length) return;

        currentIndex = index;
        const song = songs[index];
        const displayName = song.name;
        const folder = song.folder;
        const audioUrl = `music/${encodeURIComponent(folder)}/${encodeURIComponent(displayName)}/${encodeURIComponent(song.file)}`;

        audioPlayer.src = audioUrl;
        audioPlayer.play().catch(error => console.error("Playback failed:", error));

        nowPlayingTitle.textContent = selectedPlaylists.length > 1
            ? `${displayName} (${folder})`
            : displayName;

        loadLyrics(displayName, folder);

        const songPage = Math.floor(index / songsPerPage) + 1;
        if (songPage !== currentPage) {
            currentPage = songPage;
            renderSongList();
            renderPagination();
        } else {
            renderSongList();
        }
    }

    function setActiveButton(id) {
        document.querySelectorAll(".playback-options button").forEach(b => b.classList.remove("active"));
        document.getElementById(id).classList.add("active");
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

    setActiveButton("btn-sequential");

    audioPlayer.addEventListener("ended", () => {
        if (playbackMode === "loop") {
            playSong(currentIndex);
        } else if (playbackMode === "random") {
            const next = Math.floor(Math.random() * songs.length);
            playSong(next);
        } else {
            const next = (currentIndex + 1) % songs.length;
            playSong(next);
        }
    });

    // ---- Lyrics parsing ----

    function parseLyrics(lyricsText) {
        const lines = lyricsText.split("\n");
        const lyrics = [];

        for (let line of lines) {
            line = line.trim();
            if (!line) continue;

            const timeRegex = /\[(\d{2}):(\d{2})(?:[.:](\d{2,3}))?\]/g;
            const matches = [...line.matchAll(timeRegex)];

            if (matches.length > 0) {
                const text = line.replace(timeRegex, "").trim();
                if (text) {
                    for (let match of matches) {
                        const minutes = parseInt(match[1]);
                        const seconds = parseInt(match[2]);
                        const fracRaw = match[3];
                        let fractionSeconds = 0;
                        if (typeof fracRaw !== "undefined") {
                            const frac = parseInt(fracRaw);
                            fractionSeconds = fracRaw.length === 3 ? frac / 1000 : frac / 100;
                        }
                        const time = minutes * 60 + seconds + fractionSeconds;
                        lyrics.push({ time, text, originalText: text });
                    }
                }
            }
        }

        lyrics.sort((a, b) => a.time - b.time);

        const processed = [];
        for (let i = 0; i < lyrics.length; i++) {
            const current = lyrics[i];
            const next = lyrics[i + 1];
            if (next && Math.abs(current.time - next.time) < 0.1) {
                processed.push({ time: current.time, text: current.text, translation: next.text });
                i++;
            } else {
                processed.push({ time: current.time, text: current.text, translation: null });
            }
        }
        return processed;
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

    function getLyricAt(index) {
        if (index < 0 || index >= lyricsData.length) return null;
        return lyricsData[index];
    }

    function escapeHTML(str) {
        return String(str)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#39;");
    }

    function lyricExists(lyric) {
        return lyric && typeof lyric.text === "string";
    }

    function renderLyricHTML(lyric) {
        if (!lyricExists(lyric)) return "";
        const text = lyric.text || "";
        const translation = showTranslation && lyric.translation
            ? `<div class="lyrics-translation">${escapeHTML(lyric.translation)}</div>`
            : "";
        return `${escapeHTML(text)}${translation}`;
    }

    function snapToIndex(targetIndex) {
        if (!prevLineEl || !currentLineEl || !nextLineEl) return;
        prevLineEl.className = "lyrics-line lyric-prev";
        currentLineEl.className = "lyrics-line lyric-current";
        nextLineEl.className = "lyrics-line lyric-next";
        prevLineEl.innerHTML = renderLyricHTML(getLyricAt(targetIndex - 1));
        currentLineEl.innerHTML = renderLyricHTML(getLyricAt(targetIndex));
        nextLineEl.innerHTML = renderLyricHTML(getLyricAt(targetIndex + 1));
        lastLyricIndex = targetIndex;
    }

    function updateCurrentLyric(currentTime) {
        if (!lyricsData.length || !currentLineEl) return;
        const idx = findCurrentLyricIndex(currentTime);
        if (idx === -1) {
            prevLineEl.innerHTML = "";
            currentLineEl.innerHTML = renderLyricHTML(getLyricAt(0));
            nextLineEl.innerHTML = renderLyricHTML(getLyricAt(1));
            lastLyricIndex = -1;
            return;
        }
        snapToIndex(idx);
    }

    function displayLyrics() {
        lyricsDisplay.innerHTML = "";
        lastLyricIndex = -1;

        prevLineEl = document.createElement("div");
        prevLineEl.className = "lyrics-line lyric-prev";
        currentLineEl = document.createElement("div");
        currentLineEl.className = "lyrics-line lyric-current";
        nextLineEl = document.createElement("div");
        nextLineEl.className = "lyrics-line lyric-next";

        lyricsDisplay.appendChild(prevLineEl);
        lyricsDisplay.appendChild(currentLineEl);
        lyricsDisplay.appendChild(nextLineEl);

        if (lyricsData.length === 0) {
            currentLineEl.innerHTML = "暂无歌词";
            return;
        }

        const idx = findCurrentLyricIndex(audioPlayer.currentTime);
        snapToIndex(idx < 0 ? 0 : idx);
    }

    function displayNoLyrics() {
        lyricsDisplay.innerHTML = "";
        lastLyricIndex = -1;

        prevLineEl = document.createElement("div");
        prevLineEl.className = "lyrics-line lyric-prev";
        currentLineEl = document.createElement("div");
        currentLineEl.className = "lyrics-line lyric-current lyrics-empty";
        nextLineEl = document.createElement("div");
        nextLineEl.className = "lyrics-line lyric-next";

        const guide = [
            "未加载歌词",
            "将 .lrc 文件放入歌曲文件夹即可"
        ].join("<br/>");

        currentLineEl.innerHTML = guide;

        lyricsDisplay.appendChild(prevLineEl);
        lyricsDisplay.appendChild(currentLineEl);
        lyricsDisplay.appendChild(nextLineEl);
    }

    function clearLyrics() {
        displayNoLyrics();
        lyricsData = [];
        lastLyricIndex = -1;
    }

    function loadLyrics(songName, folder) {
        const cacheKey = `${folder}/${songName}`;
        if (lyricsCache.has(cacheKey)) {
            const cached = lyricsCache.get(cacheKey);
            if (cached.success) {
                lyricsData = parseLyrics(cached.lyrics);
                displayLyrics();
            } else {
                clearLyrics();
            }
            return;
        }

        fetch(`/api/lyrics?folder=${encodeURIComponent(folder)}&song=${encodeURIComponent(songName)}`)
            .then(res => res.json())
            .then(data => {
                lyricsCache.set(cacheKey, data);
                if (data.success) {
                    lyricsData = parseLyrics(data.lyrics);
                    displayLyrics();
                } else {
                    clearLyrics();
                }
            })
            .catch(error => {
                console.error("Failed to load lyrics:", error);
                clearLyrics();
            });
    }

    function preloadLyrics(songsToPreload, folder) {
        if (songsToPreload.length === 0) return;
        const songNames = songsToPreload.map(s => s.name);
        const songsParam = encodeURIComponent(JSON.stringify(songNames));

        fetch(`/api/batch-lyrics?folder=${encodeURIComponent(folder)}&songs=${songsParam}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    Object.entries(data.results).forEach(([name, result]) => {
                        lyricsCache.set(`${folder}/${name}`, result);
                    });
                }
            })
            .catch(error => console.error("Failed to preload lyrics:", error));
    }

    // ---- Audio events ----

    audioPlayer.addEventListener("timeupdate", () => updateCurrentLyric(audioPlayer.currentTime));
    audioPlayer.addEventListener("seeking", () => updateCurrentLyric(audioPlayer.currentTime));
    audioPlayer.addEventListener("seeked", () => updateCurrentLyric(audioPlayer.currentTime));
    audioPlayer.addEventListener("loadedmetadata", () => updateCurrentLyric(audioPlayer.currentTime));

    // ---- Translation toggle ----

    if (toggleTranslationCheckbox) {
        showTranslation = toggleTranslationCheckbox.checked;
        toggleTranslationCheckbox.addEventListener("change", () => {
            showTranslation = toggleTranslationCheckbox.checked;
            if (!lyricsData.length || !currentLineEl) return;
            const idx = lastLyricIndex >= 0 ? lastLyricIndex : findCurrentLyricIndex(audioPlayer.currentTime);
            snapToIndex(idx < 0 ? 0 : idx);
        });
    }
});
