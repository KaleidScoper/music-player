document.addEventListener('DOMContentLoaded', () => {
    const folderName = document.getElementById('folder-name');
    const fileList = document.getElementById('file-list');
    const audioPlayer = document.getElementById('audio-player');
    const playBtn = document.getElementById('play');
    const nextBtn = document.getElementById('next');
    const prevBtn = document.getElementById('prev');
    const modeBtn = document.getElementById('mode');
  
    let currentFolder = null;
    let currentFiles = [];
    let currentIndex = 0;
    let playMode = 'sequential'; // Options: 'sequential', 'random', 'repeat'
  
    // 获取文件夹和文件
    fetch('get_music.php')
      .then(response => response.json())
      .then(data => {
        if (data.length > 0) {
          loadFolder(data[0]);
        }
        renderFolders(data);
      });
  
    function renderFolders(data) {
      data.forEach(folder => {
        const li = document.createElement('li');
        li.textContent = folder.folder;
        li.addEventListener('click', () => loadFolder(folder));
        fileList.appendChild(li);
      });
    }
  
    function loadFolder(folder) {
      currentFolder = folder.folder;
      currentFiles = folder.files;
      currentIndex = 0;
      folderName.textContent = currentFolder;
      renderFiles();
    }
  
    function renderFiles() {
      fileList.innerHTML = '';
      currentFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.textContent = file;
        li.addEventListener('click', () => playFile(index));
        fileList.appendChild(li);
      });
    }
  
    function playFile(index) {
      currentIndex = index;
      audioPlayer.src = `music/${currentFolder}/${currentFiles[currentIndex]}`;
      audioPlayer.play();
    }
  
    playBtn.addEventListener('click', () => {
      if (audioPlayer.paused) {
        audioPlayer.play();
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
      } else {
        audioPlayer.pause();
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
      }
    });
  
    nextBtn.addEventListener('click', playNext);
    prevBtn.addEventListener('click', playPrev);
    modeBtn.addEventListener('click', toggleMode);
  
    function playNext() {
      if (playMode === 'random') {
        currentIndex = Math.floor(Math.random() * currentFiles.length);
      } else if (playMode === 'sequential') {
        currentIndex = (currentIndex + 1) % currentFiles.length;
      }
      playFile(currentIndex);
    }
  
    function playPrev() {
      currentIndex = (currentIndex - 1 + currentFiles.length) % currentFiles.length;
      playFile(currentIndex);
    }
  
    function toggleMode() {
      const modes = ['sequential', 'random', 'repeat'];
      playMode = modes[(modes.indexOf(playMode) + 1) % modes.length];
      modeBtn.innerHTML = playMode === 'random' ? '<i class="fas fa-random"></i>' :
                          playMode === 'repeat' ? '<i class="fas fa-repeat"></i>' :
                          '<i class="fas fa-list"></i>';
    }
  });
   