# 页面样式优化 Prompt

## 背景与约束

项目是一个 Web 音乐播放器。项目前端部分存在严重的 vibe coding 痕迹，本 prompt 意在去除这种痕迹，从而优化视觉效果。目标效果为简约、克制的风格。

## 一、配色方案选择器（theme-selector-inline）

移除此选择器，并且移除 image-theme 以外的所有主题。

## 二、image-theme 主题

重命名此主题为 dark-theme。现在它仍然是项目的默认主题。强调色为#80CFFF。

将所有渐变色更改为纯色。去除所有 emoji。

player-container 目前是一张不透明白色的 Accent Border Card。将其调整为黑色，透明度0.8，去除卡片顶部的色条。

playlist 块、播放器块和歌词块也均做出符合新 player-container 的颜色改变。其颜色需为不透明的、颜色接近新 player-container 的“半透明后的黑色”的颜色。

pagination 中的页码按钮当前颜色为#007bff渐变色，被选中则为绿色。被选中按钮颜色改为纯色强调色，未被选中者为半透明暗色毛玻璃。

player-container 底部文本块下方添加版权声明。

## 三、其他

其余未提到的部分酌情优化为视觉上与前文统一的风格。