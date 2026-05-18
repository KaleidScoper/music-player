# 前端视觉重构方案

## 一、背景与目标

### 使用场景
项目预期部署在 VPS 上持久运行，链接嵌入其他站点以 popup 窗口打开。窗口尺寸通常较紧凑（约 400×600 至 600×800），非全屏浏览场景。

### 当前问题
1. **悬浮卡片式布局不适合 popup**：大圆角、backdrop-filter、背景图片在紧凑窗口中浪费空间，且与宿主页面风格割裂
2. **vibe coding 痕迹严重**：
   - 按钮的 `::before` 涟漪伪元素（300px 扩散）
   - 无意义的 hover translateX/translateY 微动效
   - `contain: layout style paint` 属于过早优化
   - `performance.memory` 监控和 MutationObserver — 对几十首歌的场景过度设计
   - 虚拟滚动 — 同上
   - 残留的 `data-theme` 清理代码
   - Font Awesome CDN 外部依赖
3. **视觉风格与参考项目（文人书斋）不统一**

### 目标
- 布局极简，适配 popup 窗口
- 采用文人书斋暗色设计语言，与 `kaleidscoper.github.io` 视觉统一
- 去除 vibe coding 痕迹，保留优秀功能设计
- 零外部 CDN 依赖

---

## 二、视觉设计系统（文人书斋暗色）

> 以下色值直接沿用参考项目 `kaleidscoper.github.io` 的暗色模式主题。

### 2.1 色彩

```css
:root {
  --bg:            #1c1f26;   /* 页面背景 - 靛灰 */
  --surface:       #2a2f3a;   /* 控件/面板背景 */
  --border:        #3b414c;   /* 分割线 */
  --text:          #d0d0d0;   /* 正文 */
  --text-secondary:#aaa;      /* 辅助文字、时间戳 */
  --accent:        #80cfff;   /* 强调色：选中态、链接、当前播放 */
  --accent-hover:  #a8daff;   /* 悬停 */
  --muted:         #888;      /* 占位/禁用 */
}
```

**原则**：
- 纯暗色，无主题切换，无背景图片
- 强调色仅用于当前播放指示、激活按钮、进度条
- 不使用渐变，所有背景为纯色

### 2.2 字体

```css
--font-ui:    "Noto Sans SC", "Source Han Sans SC", "PingFang SC",
             "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
--font-text:  "Noto Serif SC", "Source Han Serif SC", "STSong",
             Georgia, "Times New Roman", serif;
```

| 角色 | 字体 | 说明 |
|------|------|------|
| UI 控件、按钮、列表 | sans-serif | 清晰可辨，符合操作预期 |
| 歌词正文 | serif | 阅读感，符合文人书斋气质 |
| 歌词翻译 | serif + italic | 与原文区分 |

### 2.3 间距与圆角

```css
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--space-xs: 4px;
--space-sm: 8px;
--space-md: 12px;
--space-lg: 16px;
--space-xl: 24px;
```

### 2.4 动效

```css
--transition-fast: 0.1s ease-in-out;   /* 按钮点击反馈 */
--transition-base: 0.3s ease-in-out;   /* 悬停、切换 */
```

**原则**：禁止缩放动效、禁止位移动效（translate）、禁止涟漪。仅保留透明度/颜色过渡。

---

## 三、布局方案

### 3.1 整体结构

```
┌──────────────────────────────┐
│  歌单选择器 (dropdown)        │
├──────────────────────────────┤
│                              │
│  歌曲列表                     │
│  (占据剩余高度, overflow-y)    │
│                              │
│                              │
├──────────────────────────────┤
│  分页器                      │
├──────────────────────────────┤
│  正在播放: 歌曲名             │
│  [========▶️ 音频进度条 =====]│
│  [单曲循环] [顺序] [随机]     │
├──────────────────────────────┤
│  歌词 (三行固定)              │
└──────────────────────────────┘
```

**关键决策**：
- **取消悬浮卡片容器**：`player-container` 的圆角、backdrop-filter、box-shadow 全部移除
- **body 直接作为布局容器**：flex column，填满窗口
- **歌词面板固定在底部**：始终可见，不随列表滚动
- **歌曲列表 flex-grow 填充剩余空间**

### 3.2 CSS 布局骨架

```css
body {
  display: flex;
  flex-direction: column;
  height: 100vh;
  margin: 0;
  padding: 12px;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
}

.song-list-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;        /* flex 嵌套滚动必需 */
}

.controls-area {
  flex-shrink: 0;       /* 底部控制区固定高度 */
}

.lyrics-area {
  flex-shrink: 0;       /* 底部歌词固定高度 120px */
  height: 120px;
  overflow: hidden;
}
```

### 3.3 Popup 适配

- 所有 padding/margin 使用紧凑值（8-16px）
- 歌词区高度固定（120px），不挤压列表
- 歌曲列表项高度固定（40px），便于计算可见数量
- 字号比全屏场景略小（13-14px 基准）

---

## 四、组件设计

### 4.1 歌单选择器

**保留**：多选歌单 dropdown 功能设计

**变更**：
- 去除 backdrop-filter 毛玻璃
- 背景改为 `var(--surface)` 纯色
- 下拉菜单改 dark 色值
- 选中状态：`var(--accent)` 背景 + `#1c1f26` 深色文字（高对比）

```css
.playlist-dropdown-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text);
}

.playlist-dropdown-menu {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.playlist-checkbox.selected {
  background: var(--accent);
  color: #1c1f26;
  font-weight: 600;
}
```

### 4.2 歌曲列表

**保留**：分页（每页 10 首）、点击播放、当前播放高亮

**删除**：虚拟滚动（歌曲量达不到需要它的阈值）、loading spinner 动画

**变更**：
- 列表项去掉 hover 时的 translateX 位移
- 当前播放项使用左侧 accent 色竖线（文人书斋标题风格）替代整行变色
- 列表项底部 border 改用 `var(--border)`

```css
#song-list li {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background var(--transition-fast);
  border-left: 3px solid transparent;  /* 预留给播放指示器 */
}

#song-list li:hover {
  background: rgba(128, 207, 255, 0.05);
}

#song-list li.playing {
  border-left-color: var(--accent);
  font-weight: 600;
}
```

### 4.3 音频播放器

**保留**：原生 `<audio>` 控件（浏览器保证无障碍和可用性）

**变更**：浏览器原生 audio 控件通过 CSS accent-color 融入主题色

```css
#audio-player {
  accent-color: var(--accent);
}
```

### 4.4 播放模式按钮

**保留**：三种模式（单曲循环、顺序、随机），互斥选中

**删除**：`::before` 涟漪伪元素、hover 上浮动效、Font Awesome 图标

**变更**：
- 图标改用行内 Unicode 字符（↻ 单曲循环、→ 顺序、⇄ 随机）
- 激活态仅改 background 和 color

```css
.playback-options button {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-ui);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.playback-options button.active {
  background: var(--accent);
  color: #1c1f26;
  border-color: var(--accent);
}
```

### 4.5 分页器

**保留**：页码按钮、当前页高亮

**变更**：统一暗色按钮风格

```css
.pagination button {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-ui);
}

.pagination button.active {
  background: var(--accent);
  color: #1c1f26;
  border-color: var(--accent);
}
```

### 4.6 歌词显示

**保留**：
- 三行固定显示（prev/current/next）
- LRC 解析逻辑（时间戳 + 原文 + 翻译配对）
- 翻译显示开关
- 歌词缓存和预加载机制

**变更**：
- 当前行使用 serif 字体，前后行 sans-serif
- 当前行高亮方式从 opacity 改为 color（`var(--text)` vs `var(--text-secondary)`）
- 翻译行颜色 `var(--muted)` + italic
- 翻译开关移到歌词区域右上角，极小化

```css
.lyric-prev, .lyric-next {
  color: var(--text-secondary);
  font-size: 0.9em;
}

.lyric-current {
  color: var(--text);
  font-family: var(--font-text);   /* 当前歌词用衬线 */
  font-size: 1.1em;
}

.lyrics-translation {
  color: var(--muted);
  font-style: italic;
  font-size: 0.85em;
}
```

### 4.7 无歌词提示

**保留**：引导用户添加歌词的提示文案

**变更**：样式收敛为简约居中文本

---

## 五、代码清理清单

### 删除项

| 代码 | 原因 |
|------|------|
| CSS `::before` 伪元素涟漪 | vibe coding，无功能价值 |
| hover translateX/translateY | 同上 |
| `contain: layout style paint` | 过早优化 |
| `@keyframes spin` | 仅 loading 用，loading 本身已删除 |
| `#song-list.virtual-scroll` 及关联 CSS | 虚拟滚动已删除 |
| `performance.memory` 监控 | 过度设计 |
| `MutationObserver` DOM 计数 | 过度设计 |
| `clearOldCache()` | 过度设计 |
| `initPerformanceOptimization()` | 全部上述逻辑 |
| `data-theme` 清理代码 | 遗留代码 |
| `localStorage.removeItem('selectedTheme')` | 遗留代码 |
| Font Awesome CDN `<link>` | 外部依赖 |
| `fa fa-*` 类名引用 | 改用 Unicode |
| `.copyright` 块中的 emoji | 风格不统一 |
| 所有渐变色 | 设计系统要求纯色 |

### 保留项

| 功能 | 原因 |
|------|------|
| 多歌单选择（dropdown + checkbox） | 核心功能 |
| 歌曲分页（10 首/页） | 控制列表长度 |
| LRC 解析 (`parseLyrics`) | 核心功能，实现正确 |
| 原文/翻译配对逻辑 | 同上 |
| 三行歌词显示 | 简洁有效 |
| 翻译开关 | 用户控制权 |
| 歌词缓存（内存 Map + 批量预加载） | 合理优化 |
| song list 缓存 (`songsCache`) | 避免重复请求 |
| HTML 转义 (`escapeHTML`) | 安全必要 |
| 三种播放模式 + ended 事件处理 | 核心功能 |

---

## 六、HTML 结构变更

```html
<!-- index.html 目标结构 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>音乐播放器</title>
    <link rel="stylesheet" href="style.css">
    <!-- Font Awesome CDN 已删除 -->
</head>
<body>
    <!-- 歌单选择 -->
    <div class="playlist-header">
        <div class="playlist-dropdown-container">
            <button id="playlist-dropdown-btn">
                <span id="playlist-dropdown-text">选择歌单</span>
                <span class="dropdown-arrow">▾</span>
            </button>
            <div id="playlist-dropdown-menu">
                <div id="playlist-checkboxes"></div>
            </div>
        </div>
    </div>

    <!-- 歌曲列表（flex-grow 填充） -->
    <div class="song-list-area">
        <ul id="song-list"></ul>
    </div>

    <!-- 分页 -->
    <div id="pagination"></div>

    <!-- 播放控制 -->
    <div class="controls">
        <div class="now-playing">
            <span id="now-playing-title">未在播放</span>
        </div>
        <audio id="audio-player" controls></audio>
        <div class="playback-options">
            <button id="btn-loop">↻ 单曲循环</button>
            <button id="btn-sequential">→ 顺序</button>
            <button id="btn-random">⇄ 随机</button>
        </div>
    </div>

    <!-- 歌词 -->
    <div class="lyrics-header">
        <label class="toggle-translation">
            <input type="checkbox" id="toggle-translation" checked>
            <span>翻译</span>
        </label>
    </div>
    <div class="lyrics-area">
        <div id="lyrics-display"></div>
    </div>

    <script src="script.js"></script>
</body>
</html>
```

### 与旧 HTML 的差异

| 变更 | 说明 |
|------|------|
| 去除 `h1` 标题 | popup 无需标题，歌单选择器自解释 |
| 去除 `.player-container` 包裹 | body 即为容器 |
| 去除 `.playlist`, `.controls`, `.lyrics-container` 额外卡片层 | 减少嵌套 |
| 去除 Font Awesome CDN | 零外部依赖 |
| 去除 `.copyright` 块 | popup 窗口不适合放版权信息（可放 title/aria-label） |
| 歌词区域从 `.lyrics-container` 改为 `.lyrics-area` | 语义更清晰 |

---

## 七、实施步骤

1. 重写 `style.css` — 彻底替换为文人书斋暗色系统
2. 重写 `index.html` — 简化 DOM 结构
3. 重构 `script.js` — 删除 vibe coding 垃圾代码，保留功能
4. 全场景测试：单歌单/多歌单、有歌词/无歌词、分页、播放模式切换
