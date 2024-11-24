document.addEventListener("DOMContentLoaded", () => {
  const folderSelect = document.getElementById("folder-select");
  const songList = document.getElementById("song-list");
  const audioPlayer = document.getElementById("audio-player");
  const currentFolder = document.getElementById("current-folder");

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

  // 加载歌曲列表
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

    // 更新“正在播放的音乐”
    const nowPlayingTitle = document.getElementById("now-playing-title");
    nowPlayingTitle.textContent = songs[index];
}

  // 播放模式
  document.getElementById("btn-loop").addEventListener("click", () => {
      playbackMode = "loop";
      audioPlayer.loop = true;
  });

  document.getElementById("btn-sequential").addEventListener("click", () => {
      playbackMode = "sequential";
      audioPlayer.loop = false;
  });

  document.getElementById("btn-random").addEventListener("click", () => {
      playbackMode = "random";
      audioPlayer.loop = false;
  });

  audioPlayer.addEventListener("ended", () => {
    if (playMode === "repeat") {
        // 单曲循环
        playSong(currentIndex);
    } else if (playMode === "shuffle") {
        // 随机播放
        const nextIndex = Math.floor(Math.random() * songs.length);
        playSong(nextIndex);
    } else {
        // 顺序播放
        const nextIndex = (currentIndex + 1) % songs.length;
        playSong(nextIndex);
    }
});

});
