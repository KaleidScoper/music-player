#!/usr/bin/env python3
"""Music player server - single-file Flask application. Run with: python server.py"""

import argparse
import glob
import json
import mimetypes
import os
import re
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

app = Flask(__name__, static_url_path="", static_folder=".")

MUSIC_DIR = "music"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
CACHE_TTL = 300

lyrics_index_cache = None
lyrics_index_timestamp = 0
lyrics_result_cache = {}


def build_lyrics_index():
    global lyrics_index_cache, lyrics_index_timestamp
    index = {}
    if not os.path.isdir(MUSIC_DIR):
        lyrics_index_cache = index
        lyrics_index_timestamp = time.time()
        return

    for playlist in os.listdir(MUSIC_DIR):
        playlist_path = os.path.join(MUSIC_DIR, playlist)
        if not os.path.isdir(playlist_path):
            continue
        for song_dir_name in os.listdir(playlist_path):
            song_path = os.path.join(playlist_path, song_dir_name)
            if not os.path.isdir(song_path):
                continue
            lrc_files = glob.glob(os.path.join(song_path, "*.lrc"))
            if lrc_files:
                key = f"{playlist}/{song_dir_name}"
                index[key] = lrc_files[0]

    lyrics_index_cache = index
    lyrics_index_timestamp = time.time()


def get_lyrics_index():
    global lyrics_index_cache, lyrics_index_timestamp
    if lyrics_index_cache is None or (time.time() - lyrics_index_timestamp > CACHE_TTL):
        build_lyrics_index()
    return lyrics_index_cache


def find_audio_file(song_dir_path):
    for f in sorted(os.listdir(song_dir_path)):
        if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS:
            return os.path.join(song_dir_path, f)
    return None


# --- Static files ---

@app.route("/")
def index():
    return send_file("index.html")


# --- API ---

@app.route("/api/folders")
def api_folders():
    if not os.path.isdir(MUSIC_DIR):
        return jsonify([])
    folders = sorted(
        d for d in os.listdir(MUSIC_DIR)
        if os.path.isdir(os.path.join(MUSIC_DIR, d))
    )
    return jsonify(folders)


@app.route("/api/songs")
def api_songs():
    folder = request.args.get("folder", "")
    playlist_path = os.path.join(MUSIC_DIR, folder)
    if not os.path.isdir(playlist_path):
        return jsonify({"error": f"Folder not found: {folder}"}), 404

    songs = []
    for entry in sorted(os.listdir(playlist_path)):
        song_dir = os.path.join(playlist_path, entry)
        if not os.path.isdir(song_dir):
            continue
        audio_path = find_audio_file(song_dir)
        if audio_path:
            songs.append({
                "name": entry,
                "folder": folder,
                "file": os.path.basename(audio_path)
            })

    return jsonify(songs)


@app.route("/api/lyrics")
def api_lyrics():
    folder = request.args.get("folder", "")
    song_name = request.args.get("song", "")
    cache_key = f"{folder}/{song_name}"

    if cache_key in lyrics_result_cache:
        entry = lyrics_result_cache[cache_key]
        if time.time() - entry["ts"] < CACHE_TTL:
            return jsonify(entry["data"])

    index = get_lyrics_index()
    lrc_path = index.get(cache_key)

    if lrc_path and os.path.isfile(lrc_path):
        with open(lrc_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        result = {"success": True, "lyrics": content}
    else:
        result = {"success": False, "message": "Lyrics file not found"}

    lyrics_result_cache[cache_key] = {"ts": time.time(), "data": result}
    return jsonify(result)


@app.route("/api/batch-lyrics")
def api_batch_lyrics():
    folder = request.args.get("folder", "")
    try:
        song_names = json.loads(request.args.get("songs", "[]"))
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid songs parameter"}), 400

    index = get_lyrics_index()
    results = {}

    for song_name in song_names:
        cache_key = f"{folder}/{song_name}"
        if cache_key in lyrics_result_cache:
            entry = lyrics_result_cache[cache_key]
            if time.time() - entry["ts"] < CACHE_TTL:
                results[song_name] = entry["data"]
                continue

        lrc_path = index.get(cache_key)
        if lrc_path and os.path.isfile(lrc_path):
            with open(lrc_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            data = {"success": True, "lyrics": content}
        else:
            data = {"success": False, "message": "Lyrics file not found"}

        lyrics_result_cache[cache_key] = {"ts": time.time(), "data": data}
        results[song_name] = data

    return jsonify({"success": True, "results": results})


@app.route("/api/clear-cache", methods=["POST"])
def api_clear_cache():
    global lyrics_index_cache, lyrics_index_timestamp, lyrics_result_cache
    lyrics_index_cache = None
    lyrics_index_timestamp = 0
    lyrics_result_cache = {}
    return jsonify({"success": True, "message": "Cache cleared"})


# --- Audio streaming with Range support ---

def parse_range_header(range_header, file_size):
    match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not match:
        return None
    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1
    if start >= file_size or end >= file_size:
        return None
    return start, end


@app.route("/music/<path:filepath>")
def serve_music(filepath):
    abs_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.isfile(abs_path):
        return jsonify({"error": "File not found"}), 404

    file_size = os.path.getsize(abs_path)
    mime_type = mimetypes.guess_type(abs_path)[0] or "application/octet-stream"

    range_header = request.headers.get("Range")
    if range_header:
        ranges = parse_range_header(range_header, file_size)
        if ranges:
            start, end = ranges
            length = end - start + 1
            with open(abs_path, "rb") as f:
                f.seek(start)
                data = f.read(length)
            return Response(
                data,
                206,
                headers={
                    "Content-Type": mime_type,
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(length),
                    "Accept-Ranges": "bytes",
                },
                direct_passthrough=True,
            )

    return send_file(abs_path, mimetype=mime_type)


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
