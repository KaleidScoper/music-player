#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频批量下载工具
使用 bilibili-video2mp3 工具
"""

import subprocess
import sys
import os
import re
import glob
from typing import List, Optional

def check_command_exists(command: str) -> bool:
    """检查命令是否存在"""
    try:
        # 对于不同的命令使用不同的参数
        if command == 'npm':
            # npm 使用 -v 参数，如果失败则尝试 --version
            try:
                subprocess.run([command, '-v'], 
                              capture_output=True, 
                              check=True, 
                              timeout=10)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                # 如果 -v 失败，尝试 --version
                try:
                    subprocess.run([command, '--version'], 
                                  capture_output=True, 
                                  check=True, 
                                  timeout=10)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    # 如果都失败，尝试简单的 help 命令
                    subprocess.run([command, 'help'], 
                                  capture_output=True, 
                                  check=True, 
                                  timeout=10)
                    return True
        elif command == 'node':
            # node 使用 --version 参数
            subprocess.run([command, '--version'], 
                          capture_output=True, 
                          check=True, 
                          timeout=10)
        elif command == 'ffmpeg':
            # ffmpeg 使用 -version 参数
            subprocess.run([command, '-version'], 
                          capture_output=True, 
                          check=True, 
                          timeout=10)
        else:
            # 默认使用 --version
            subprocess.run([command, '--version'], 
                          capture_output=True, 
                          check=True, 
                          timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_environment():
    """检查环境依赖"""
    print("检查环境依赖...")
    
    # 检查 Node.js
    print("检查 Node.js...")
    if not check_command_exists('node'):
        print("❌ 错误: 请先安装 Node.js: https://nodejs.org/")
        return False
    else:
        print("✅ Node.js 已安装")
    
    # 检查 FFmpeg
    print("检查 FFmpeg...")
    if not check_command_exists('ffmpeg'):
        print("⚠️  警告: 未检测到 FFmpeg，可能无法正确转换为 MP3 格式")
        print("请安装 FFmpeg: https://ffmpeg.org/download.html")
        
        while True:
            choice = input("是否继续执行？(y/N): ").strip().lower()
            if choice in ['y', 'yes']:
                break
            elif choice in ['n', 'no', '']:
                print("用户取消执行")
                return False
            else:
                print("请输入 y 或 n")
    else:
        print("✅ FFmpeg 已安装")
    
    print("✅ 环境检查完成！")
    return True

def extract_bilibili_url(text: str) -> str:
    """从文本中提取B站URL"""
    # 匹配B站视频URL的正则表达式
    # 支持多种B站URL格式
    patterns = [
        r'https?://www\.bilibili\.com/video/[A-Za-z0-9_\-]+',
        r'https?://bilibili\.com/video/[A-Za-z0-9_\-]+',
        r'https?://www\.b23\.tv/[A-Za-z0-9_\-]+',
        r'https?://b23\.tv/[A-Za-z0-9_\-]+'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None

def collect_urls() -> List[str]:
    """收集用户输入的URL"""
    print("\n=== B站视频批量下载工具 ===")
    print("请输入要下载的B站视频URL（每行一个）")
    print("支持直接粘贴B站分享文本，脚本会自动提取URL")
    print("输入完成后直接按回车开始下载")
    print()
    
    urls = []
    counter = 1
    
    while True:
        try:
            user_input = input(f"URL #{counter} (直接回车结束输入): ").strip()
            
            if not user_input:
                break
            
            # 尝试从输入文本中提取B站URL
            extracted_url = extract_bilibili_url(user_input)
            
            if extracted_url:
                urls.append(extracted_url)
                print(f"✅ 已添加: {extracted_url}")
                if extracted_url != user_input:
                    print(f"   原始输入: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
                counter += 1
            else:
                print("⚠️  未找到有效的B站URL，请重新输入")
                print("   提示: 支持直接粘贴B站分享文本，如：【视频标题】 https://www.bilibili.com/video/...")
                
        except KeyboardInterrupt:
            print("\n\n用户中断输入")
            return []
        except EOFError:
            break
    
    return urls

def get_music_directories() -> List[str]:
    """获取现有的歌单目录列表"""
    music_dir = "../music"
    if not os.path.exists(music_dir):
        return []
    
    directories = []
    for item in os.listdir(music_dir):
        item_path = os.path.join(music_dir, item)
        if os.path.isdir(item_path):
            directories.append(item)
    
    return sorted(directories)

def select_save_directory() -> str:
    """让用户选择保存目录"""
    print("\n=== 选择保存目录 ===")
    print("请选择音频文件的保存位置：")
    print()
    
    # 获取现有歌单目录
    existing_dirs = get_music_directories()
    
    options = []
    print("1. 保存到 download 目录（当前目录）")
    options.append("download")
    
    if existing_dirs:
        print(f"\n2-{len(existing_dirs)+1}. 保存到现有歌单目录：")
        for i, dir_name in enumerate(existing_dirs, 2):
            print(f"   {i}. {dir_name}")
            options.append(f"../music/{dir_name}")
    
    print(f"\n{len(options)+1}. 创建新歌单目录")
    options.append("new")
    
    while True:
        try:
            max_choice = len(existing_dirs) + 2  # 1个download + 现有歌单数量 + 1个新建
            choice = input(f"\n请选择 (1-{max_choice}): ").strip()
            
            if not choice.isdigit():
                print("请输入数字")
                continue
            
            choice_num = int(choice)
            
            if choice_num == 1:
                return "download"
            elif 2 <= choice_num <= len(existing_dirs) + 1:
                return options[choice_num - 1]
            elif choice_num == max_choice:
                return create_new_playlist_directory()
            else:
                print(f"请输入 1 到 {max_choice} 之间的数字")
                
        except KeyboardInterrupt:
            print("\n\n用户中断选择")
            return "download"
        except Exception as e:
            print(f"输入错误: {e}")

def create_new_playlist_directory() -> str:
    """创建新歌单目录"""
    print("\n=== 创建新歌单目录 ===")
    
    while True:
        try:
            playlist_name = input("请输入新歌单名称: ").strip()
            
            if not playlist_name:
                print("歌单名称不能为空")
                continue
            
            # 清理名称，移除非法字符
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', playlist_name)
            if clean_name != playlist_name:
                print(f"已清理非法字符，歌单名称: {clean_name}")
            
            # 检查是否已存在
            target_dir = f"../music/{clean_name}"
            if os.path.exists(target_dir):
                print(f"歌单 '{clean_name}' 已存在，请选择其他名称")
                continue
            
            # 创建目录
            try:
                os.makedirs(target_dir, exist_ok=True)
                print(f"✅ 已创建歌单目录: {target_dir}")
                return target_dir
            except Exception as e:
                print(f"❌ 创建目录失败: {e}")
                return "download"
                
        except KeyboardInterrupt:
            print("\n\n用户中断创建")
            return "download"
        except Exception as e:
            print(f"输入错误: {e}")

def display_urls(urls: List[str]):
    """显示URL列表"""
    if not urls:
        print("❌ 未输入任何URL，脚本退出")
        return False
    
    print(f"\n准备下载以下 {len(urls)} 个视频:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    return True

def confirm_download() -> bool:
    """确认是否开始下载"""
    print()
    while True:
        choice = input("确认开始下载？(Y/n): ").strip().lower()
        if choice in ['y', 'yes', '']:
            return True
        elif choice in ['n', 'no']:
            print("用户取消下载")
            return False
        else:
            print("请输入 Y 或 n")

def move_files_to_target_directory(target_directory: str) -> bool:
    """将下载的文件移动到目标目录"""
    if target_directory == "download":
        return True  # 不需要移动
    
    print(f"\n正在移动文件到目标目录: {target_directory}")
    
    # 确保目标目录存在
    if not os.path.exists(target_directory):
        try:
            os.makedirs(target_directory, exist_ok=True)
        except Exception as e:
            print(f"❌ 创建目标目录失败: {e}")
            return False
    
    # 查找当前目录下的音频文件
    audio_extensions = ['.mp3', '.m4a', '.aac', '.wav', '.flac']
    moved_files = []
    
    try:
        for file in os.listdir('.'):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                source_path = file
                target_path = os.path.join(target_directory, file)
                
                # 如果目标文件已存在，添加序号
                counter = 1
                base_name, ext = os.path.splitext(file)
                while os.path.exists(target_path):
                    new_name = f"{base_name}_{counter}{ext}"
                    target_path = os.path.join(target_directory, new_name)
                    counter += 1
                
                # 移动文件
                os.rename(source_path, target_path)
                moved_files.append(os.path.basename(target_path))
                print(f"✅ 已移动: {file} → {os.path.basename(target_path)}")
        
        if moved_files:
            print(f"\n✅ 文件移动完成！共移动 {len(moved_files)} 个文件到: {target_directory}")
        else:
            print("⚠️  未找到音频文件需要移动")
            
        return True
        
    except Exception as e:
        print(f"❌ 移动文件时出现错误: {e}")
        return False

def execute_download(urls: List[str], save_directory: str):
    """执行下载"""
    print("开始下载...")
    
    # 构建命令字符串，使用shell执行
    # 始终先下载到当前目录
    command_parts = ['npx', 'bv2mp3']
    for url in urls:
        command_parts.append(f'--url="{url}"')
    
    command_str = ' '.join(command_parts)
    print(f"执行命令: {command_str}")
    
    try:
        # 使用shell执行命令，这样引号会被正确解析
        result = subprocess.run(command_str, 
                              shell=True,
                              check=True, 
                              capture_output=False,
                              text=True)
        
        print("\n✅ 下载完成！")
        
        # 如果需要移动到其他目录
        if save_directory != "download":
            if not move_files_to_target_directory(save_directory):
                print("⚠️  文件移动失败，文件保留在当前目录")
                return False
        else:
            print("音频文件已保存到当前目录。")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 下载过程中出现错误: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\n用户中断下载")
        return False
    
    return True

def main():
    """主函数"""
    try:
        # 检查命令行参数
        debug_mode = '--debug' in sys.argv or '-d' in sys.argv
        skip_check = '--skip-check' in sys.argv or '-s' in sys.argv
        show_help = '--help' in sys.argv or '-h' in sys.argv
        
        if show_help:
            print("B站视频批量下载工具")
            print("\n使用方法:")
            print("  python download.py                 # 正常模式（检查环境）")
            print("  python download.py --skip-check   # 跳过环境检查模式")
            print("  python download.py --debug        # 调试模式")
            print("  python download.py --help         # 显示帮助")
            print("\n参数说明:")
            print("  -s, --skip-check    跳过环境检查，直接开始下载")
            print("  -d, --debug        启用调试模式，显示详细检测信息")
            print("  -h, --help         显示此帮助信息")
            return
        
        if debug_mode:
            print("🐛 调试模式已启用")
            print("正在测试命令检测...")
            
            # 测试各个命令
            for cmd in ['node', 'ffmpeg']:
                print(f"测试 {cmd}...")
                try:
                    if cmd == 'node':
                        result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10)
                        print(f"  node --version 返回码: {result.returncode}")
                        print(f"  输出: {result.stdout.strip()}")
                    elif cmd == 'ffmpeg':
                        result = subprocess.run([cmd, '-version'], capture_output=True, text=True, timeout=10)
                        print(f"  ffmpeg -version 返回码: {result.returncode}")
                        print(f"  输出: {result.stdout[:100]}..." if len(result.stdout) > 100 else f"  输出: {result.stdout.strip()}")
                except Exception as e:
                    print(f"  {cmd} 测试失败: {e}")
                print()
        
        # 检查环境（除非跳过检查）
        if not skip_check:
            if not check_environment():
                sys.exit(1)
        else:
            print("⚠️  跳过环境检查模式")
            print("注意: 如果环境不完整，下载可能会失败")
            print()
        
        # 收集URL
        urls = collect_urls()
        
        # 显示URL列表
        if not display_urls(urls):
            sys.exit(0)
        
        # 选择保存目录
        save_directory = select_save_directory()
        
        # 确认下载
        if not confirm_download():
            sys.exit(0)
        
        # 执行下载
        execute_download(urls, save_directory)
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序出现未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
