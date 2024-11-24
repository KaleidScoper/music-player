document.addEventListener('DOMContentLoaded', () => {
    const fileList = document.getElementById('file-list');
    const audioPlayer = document.getElementById('audio-player');
    const folderName = document.getElementById('folder-name');
    const playModeBtn = document.getElementById('play-mode');
    const progressBar = document.getElementById('progress-bar');
    const currentTimeEl = document.getElementById('current-time');
    const totalTimeEl = document.getElementById('total-time');
  
    let currentFiles = [];
    let currentIndex = 0;
    let playMode = 'order'; // 顺序播放，随机播放(random)，单曲循环(loop)
  
    // 格式化时间函数
    function formatTime(seconds) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
  
    // 更新进度条和时间显示
    function updateProgress() {
      const currentTime = audioPlayer.currentTime;
      const duration = audioPlayer.duration;
  
      currentTimeEl.textContent = formatTime(currentTime);
      totalTimeEl.textContent = duration ? formatTime(duration) : '00:00';
  
      if (duration) {
        progressBar.value = (currentTime / duration) * 100;
      }
    }
  
    // 加载音乐列表
    function loadMusic(folderPath = './music') {
      fetch(`get_music.php?path=${encodeURIComponent(folderPath)}`)
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            alert(data.error);
            return;
          }
          folderName.textContent = data.folder;
          currentFiles = data.files;
          renderFileList();
        })
        .catch(err => alert('Error loading folder: ' + err));
    }
  
    // 渲染文件列表
    function renderFileList() {
      fileList.innerHTML = '';
      currentFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.textContent = file;
        li.addEventListener('click', () => {
          playFile(index);
        });
        fileList.appendChild(li);
      });
    }
  
    // 播放指定文件
    function playFile(index) {
      if (index < 0 || index >= currentFiles.length) return;
      currentIndex = index;
      const filePath = `./music/${currentFiles[currentIndex]}`;
      audioPlayer.src = filePath;
      audioPlayer.play();
    }
  
    // 切换播放模式
    playModeBtn.addEventListener('click', () => {
      if (playMode === 'order') {
        playMode = 'random';
        playModeBtn.textContent = 'Random';
      } else if (playMode === 'random') {
        playMode = 'loop';
        playModeBtn.textContent = 'Loop';
      } else {
        playMode = 'order';
        playModeBtn.textContent = 'Order';
      }
    });
  
    // 播放结束时根据播放模式切换
    audioPlayer.addEventListener('ended', () => {
      if (playMode === 'order') {
        currentIndex = (currentIndex + 1) % currentFiles.length;
      } else if (playMode === 'random') {
        currentIndex = Math.floor(Math.random() * currentFiles.length);
      }
      if (playMode === 'loop') {
        audioPlayer.currentTime = 0;
      } else {
        playFile(currentIndex);
      }
    });
  
    // 进度条功能
    audioPlayer.addEventListener('timeupdate', updateProgress);
  
    audioPlayer.addEventListener('loadedmetadata', () => {
      progressBar.max = 100;
      totalTimeEl.textContent = formatTime(audioPlayer.duration);
    });
  
    progressBar.addEventListener('input', (e) => {
      const duration = audioPlayer.duration;
      if (duration) {
        const newTime = (e.target.value / 100) * duration;
        audioPlayer.currentTime = newTime;
      }
    });
  
    // 默认加载音乐
    loadMusic();
  });
  