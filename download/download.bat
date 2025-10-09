@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM B站视频批量下载工具
REM 使用 bilibili-video2mp3 工具
REM 批处理版本，避免PowerShell编码问题

echo 检查环境依赖...

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查 npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 请先安装 npm
    pause
    exit /b 1
)

REM 检查 FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告: 未检测到 FFmpeg，可能无法正确转换为 MP3 格式
    echo 请安装 FFmpeg: https://ffmpeg.org/download.html
    set /p continue="是否继续执行？(y/N): "
    if /i not "!continue!"=="y" (
        echo 用户取消执行
        pause
        exit /b 0
    )
)

echo ✅ 环境检查完成！
echo.

echo === B站视频批量下载工具 ===
echo 请输入要下载的B站视频URL（每行一个）
echo 输入完成后直接按回车开始下载
echo.

set urls=
set counter=1

:input_loop
set /p url="URL #!counter! (直接回车结束输入): "
if "!url!"=="" goto :end_input

REM 简单的URL验证（检查是否包含bilibili.com）
echo !url! | findstr /i "bilibili.com" >nul
if errorlevel 1 (
    echo ⚠️  无效的B站URL，请重新输入
    goto :input_loop
)

REM 使用正确的格式 --url="URL"
set urls=!urls! --url="!url!"
echo ✅ 已添加: !url!
set /a counter+=1
goto :input_loop

:end_input
if "!urls!"=="" (
    echo ❌ 未输入任何URL，脚本退出
    pause
    exit /b 0
)

echo.
echo 准备下载以下 !counter! 个视频:
set temp_counter=1
for %%u in (!urls!) do (
    echo   !temp_counter!. %%u
    set /a temp_counter+=1
)

echo.
set /p confirm="确认开始下载？(Y/n): "
if /i "!confirm!"=="n" (
    echo 用户取消下载
    pause
    exit /b 0
)

echo 开始下载...
echo 执行命令: npx bv2mp3 !urls!

REM 执行下载
npx bv2mp3 !urls!
if errorlevel 1 (
    echo ❌ 下载过程中出现错误
    pause
    exit /b 1
)

echo.
echo ✅ 下载完成！音频文件已保存到当前目录。
pause
