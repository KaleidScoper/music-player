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
from typing import List

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

def collect_urls() -> List[str]:
    """收集用户输入的URL"""
    print("\n=== B站视频批量下载工具 ===")
    print("请输入要下载的B站视频URL（每行一个）")
    print("输入完成后直接按回车开始下载")
    print()
    
    urls = []
    counter = 1
    
    while True:
        try:
            url = input(f"URL #{counter} (直接回车结束输入): ").strip()
            
            if not url:
                break
            
            # 验证是否为B站URL
            if re.search(r'bilibili\.com', url):
                urls.append(url)
                print(f"✅ 已添加: {url}")
                counter += 1
            else:
                print("⚠️  无效的B站URL，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n用户中断输入")
            return []
        except EOFError:
            break
    
    return urls

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

def execute_download(urls: List[str]):
    """执行下载"""
    print("开始下载...")
    
    # 构建命令字符串，使用shell执行
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
        
        print("\n✅ 下载完成！音频文件已保存到当前目录。")
        
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
        
        # 确认下载
        if not confirm_download():
            sys.exit(0)
        
        # 执行下载
        execute_download(urls)
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序出现未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
