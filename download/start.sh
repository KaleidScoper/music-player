#!/usr/bin/env sh
# Linux / macOS 启动器：无参数打开图形界面
cd "$(dirname "$0")/.." || exit 1
exec python3 download/download.py "$@"
