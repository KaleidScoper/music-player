#!/usr/bin/env python3
"""Music player server - single-file Flask application. Run with: python server.py"""

import argparse
import json
import os
import time
from collections import OrderedDict
from pathlib import Path
from threading import RLock

from flask import Flask, abort, jsonify, request, send_file

app = Flask(__name__, static_folder=None)

BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = (BASE_DIR / "music").resolve()
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
CACHE_TTL = 300
CACHE_MAX_ENTRIES = 256
MAX_NAME_LENGTH = 255
MAX_BATCH_SONGS = 100
MAX_BATCH_PARAM_LENGTH = 64 * 1024
MAX_LYRICS_BYTES = 256 * 1024

lyrics_index_cache = None
lyrics_index_timestamp = 0
lyrics_result_cache = OrderedDict()
lyrics_cache_lock = RLock()


def valid_name(name):
    return (
        isinstance(name, str)
        and 0 < len(name) <= MAX_NAME_LENGTH
        and name not in {".", ".."}
        and not any(char in name for char in ("/", "\\", "\0"))
        and not (os.name == "nt" and ":" in name)
    )


def resolve_music_path(path):
    try:
        resolved = Path(path).resolve(strict=True)
        resolved.relative_to(MUSIC_DIR)
    except (OSError, ValueError, RuntimeError):
        return None
    return resolved


def music_directories(parent):
    resolved = resolve_music_path(parent)
    if resolved is None or not resolved.is_dir():
        return
    for child in sorted(parent.iterdir()):
        target = resolve_music_path(child)
        if valid_name(child.name) and target is not None and target.is_dir():
            yield child


def build_lyrics_index():
    global lyrics_index_cache, lyrics_index_timestamp
    index = {}
    for playlist in music_directories(MUSIC_DIR):
        for song in music_directories(playlist):
            for lrc_file in sorted(song.glob("*.lrc")):
                target = resolve_music_path(lrc_file)
                if target is not None and target.is_file() and target.suffix.lower() == ".lrc":
                    # Keep the original path so a changed symlink is checked on every read.
                    index[f"{playlist.name}/{song.name}"] = lrc_file
                    break
    lyrics_index_cache = index
    lyrics_index_timestamp = time.monotonic()


def get_lyrics_index():
    with lyrics_cache_lock:
        if lyrics_index_cache is None or time.monotonic() - lyrics_index_timestamp >= CACHE_TTL:
            build_lyrics_index()
        return lyrics_index_cache


def get_lyrics(folder, song_name):
    cache_key = f"{folder}/{song_name}"
    missing = {"success": False, "message": "Lyrics file not found"}
    with lyrics_cache_lock:
        now = time.monotonic()
        for key, entry in list(lyrics_result_cache.items()):
            if now - entry["ts"] >= CACHE_TTL:
                del lyrics_result_cache[key]

        lrc_path = get_lyrics_index().get(cache_key)
        target = resolve_music_path(lrc_path) if lrc_path is not None else None
        if target is None or not target.is_file() or target.suffix.lower() != ".lrc":
            lyrics_result_cache.pop(cache_key, None)
            return missing

        if cache_key in lyrics_result_cache:
            lyrics_result_cache.move_to_end(cache_key)
            return lyrics_result_cache[cache_key]["data"]

        try:
            with target.open("rb") as lyrics_file:
                content = lyrics_file.read(MAX_LYRICS_BYTES + 1)
        except OSError:
            return missing
        if len(content) > MAX_LYRICS_BYTES:
            return {"success": False, "message": "Lyrics file too large"}

        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        result = {"success": True, "lyrics": text}
        if len(lyrics_result_cache) >= CACHE_MAX_ENTRIES:
            lyrics_result_cache.popitem(last=False)
        lyrics_result_cache[cache_key] = {"ts": now, "data": result}
        return result


def find_audio_file(song_dir_path):
    for audio_file in sorted(Path(song_dir_path).iterdir()):
        if not valid_name(audio_file.name) or audio_file.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        target = resolve_music_path(audio_file)
        if target is not None and target.is_file() and target.suffix.lower() in AUDIO_EXTENSIONS:
            return audio_file
    return None


# --- Static files ---

@app.route("/")
@app.route("/index.html")
def index():
    return send_file(BASE_DIR / "index.html")


@app.route("/<filename>")
def frontend_asset(filename):
    if filename not in {"style.css", "script.js"}:
        abort(404)
    return send_file(BASE_DIR / filename)


# --- API ---

@app.route("/api/folders")
def api_folders():
    return jsonify([folder.name for folder in music_directories(MUSIC_DIR)])


@app.route("/api/songs")
def api_songs():
    folder = request.args.get("folder", "")
    if not valid_name(folder):
        return jsonify({"error": "Invalid folder parameter"}), 400
    playlist_path = MUSIC_DIR / folder
    target = resolve_music_path(playlist_path)
    if target is None or not target.is_dir():
        return jsonify({"error": f"Folder not found: {folder}"}), 404

    songs = []
    for song_dir in music_directories(playlist_path):
        audio_path = find_audio_file(song_dir)
        if audio_path:
            songs.append({
                "name": song_dir.name,
                "folder": folder,
                "file": audio_path.name
            })
    return jsonify(songs)


@app.route("/api/lyrics")
def api_lyrics():
    folder = request.args.get("folder", "")
    song_name = request.args.get("song", "")
    if not valid_name(folder) or not valid_name(song_name):
        return jsonify({"error": "Invalid folder or song parameter"}), 400
    return jsonify(get_lyrics(folder, song_name))


@app.route("/api/batch-lyrics")
def api_batch_lyrics():
    folder = request.args.get("folder", "")
    raw_songs = request.args.get("songs", "[]")
    if not valid_name(folder) or len(raw_songs) > MAX_BATCH_PARAM_LENGTH:
        return jsonify({"error": "Invalid folder or songs parameter"}), 400
    try:
        song_names = json.loads(raw_songs)
    except (ValueError, RecursionError):
        return jsonify({"error": "Invalid songs parameter"}), 400
    if (not isinstance(song_names, list) or len(song_names) > MAX_BATCH_SONGS
            or not all(valid_name(name) for name in song_names)):
        return jsonify({"error": "Invalid songs parameter"}), 400

    results = {name: get_lyrics(folder, name) for name in song_names}
    return jsonify({"success": True, "results": results})


# --- Audio streaming with Range support ---

@app.route("/music/<path:filepath>")
def serve_music(filepath):
    if not all(valid_name(part) for part in filepath.split("/")):
        abort(404)
    path = MUSIC_DIR / filepath
    target = resolve_music_path(path)
    if (target is None or not target.is_file()
            or path.suffix.lower() not in AUDIO_EXTENSIONS
            or target.suffix.lower() not in AUDIO_EXTENSIONS):
        return jsonify({"error": "File not found"}), 404
    return send_file(target, conditional=True)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Music player server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"Serving on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
