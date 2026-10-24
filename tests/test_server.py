import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import server


class ServerSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.music = self.root / "music"
        self.folder = "歌单 ⚡"
        self.song = "[春庭雪]：夜"
        self.song_dir = self.music / self.folder / self.song
        self.song_dir.mkdir(parents=True)
        self.audio = self.song_dir / "曲目.flac"
        self.audio.write_bytes(b"0123456789")
        self.lyric = self.song_dir / "歌词.lrc"
        self.lyric.write_text("[00:01]春庭雪\n", encoding="utf-8")
        self.outside = self.root / "music-other" / "外部歌曲"
        self.outside.mkdir(parents=True)
        (self.outside / "outside.mp3").write_bytes(b"outside audio")
        (self.outside / "outside.lrc").write_text("outside lyrics", encoding="utf-8")
        self.addCleanup(patch.stopall)
        patch.object(server, "MUSIC_DIR", self.music).start()
        patch.dict(server.app.config, TESTING=True).start()
        server.lyrics_index_cache = None
        server.lyrics_index_timestamp = 0
        server.lyrics_result_cache.clear()
        self.client = server.app.test_client()

    def get(self, url, **kwargs):
        response = self.client.get(url, **kwargs)
        self.addCleanup(response.close)
        return response

    def lyrics(self, song=None, folder=None):
        return self.get("/api/lyrics", query_string={
            "folder": self.folder if folder is None else folder,
            "song": self.song if song is None else song,
        })

    def audio_url(self, relative=None):
        if relative is None:
            relative = self.audio.relative_to(self.music).as_posix()
        return "/music/" + quote(relative, safe="/")

    def link(self, target, destination):
        try:
            destination.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symbolic links unavailable: {error}")

    def test_unicode_playlists_audio_and_lyrics(self):
        self.assertEqual(self.get("/api/folders").get_json(), [self.folder])
        songs = self.get("/api/songs", query_string={"folder": self.folder})
        self.assertEqual(songs.get_json(), [{
            "name": self.song, "folder": self.folder, "file": self.audio.name,
        }])
        self.assertEqual(self.get(self.audio_url()).data, b"0123456789")
        expected = {"success": True, "lyrics": "[00:01]春庭雪\n"}
        self.assertEqual(self.lyrics().get_json(), expected)
        batch = self.get("/api/batch-lyrics", query_string={
            "folder": self.folder, "songs": json.dumps([self.song]),
        })
        self.assertEqual(batch.get_json(), {
            "success": True, "results": {self.song: expected},
        })

    def test_only_frontend_assets_are_public(self):
        for path in ("/", "/style.css", "/script.js"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 200)
        for path in ("/server.py", "/requirements.txt", "/start.sh", "/README.md"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 404)
        with self.client.post("/api/clear-cache") as response:
            self.assertEqual(response.status_code, 404)

    def test_traversal_absolute_paths_and_non_audio_are_rejected(self):
        outside_audio = self.outside / "outside.mp3"
        paths = ["../music-other/外部歌曲/outside.mp3", str(outside_audio),
                 "../server.py", self.lyric.relative_to(self.music).as_posix()]
        for path in paths:
            with self.subTest(path=path):
                response = self.get(self.audio_url(path), follow_redirects=True)
                self.assertIn(response.status_code, (400, 404))
        for folder in ("..", "../music-other", str(self.outside.parent), "/tmp"):
            with self.subTest(folder=folder):
                response = self.get("/api/songs", query_string={"folder": folder})
                self.assertEqual(response.status_code, 400)

    def test_symlink_directories_cannot_escape_music(self):
        self.link(self.outside.parent, self.music / "outside-playlist")
        self.link(self.outside, self.music / self.folder / "outside-song")
        self.assertNotIn("outside-playlist", self.get("/api/folders").get_json())
        songs = self.get("/api/songs", query_string={"folder": self.folder}).get_json()
        self.assertNotIn("outside-song", [song["name"] for song in songs])
        for folder, song in (("outside-playlist", "外部歌曲"),
                             (self.folder, "outside-song")):
            with self.subTest(folder=folder, song=song):
                response = self.get(self.audio_url(f"{folder}/{song}/outside.mp3"))
                self.assertIn(response.status_code, (400, 404))
                self.assertFalse(self.lyrics(song, folder).get_json()["success"])

    def test_symlink_files_cannot_escape_music(self):
        song_dir = self.music / self.folder / "outside-files"
        song_dir.mkdir()
        self.link(self.outside / "outside.mp3", song_dir / "outside.mp3")
        self.link(self.outside / "outside.lrc", song_dir / "outside.lrc")
        response = self.get(self.audio_url(f"{self.folder}/outside-files/outside.mp3"))
        self.assertIn(response.status_code, (400, 404))
        self.assertFalse(self.lyrics("outside-files").get_json()["success"])

    def test_replacing_indexed_lyrics_with_external_symlink_is_rejected(self):
        self.assertTrue(self.lyrics().get_json()["success"])
        server.lyrics_result_cache.clear()
        self.lyric.unlink()
        self.link(self.outside / "outside.lrc", self.lyric)
        self.assertFalse(self.lyrics().get_json()["success"])

    def test_symlinks_inside_music_remain_usable(self):
        self.link(self.song_dir, self.music / self.folder / "alias")
        response = self.get(self.audio_url(f"{self.folder}/alias/{self.audio.name}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"0123456789")
        self.assertEqual(self.lyrics("alias").get_json()["lyrics"], "[00:01]春庭雪\n")

    def test_range_and_head_responses(self):
        cases = [("bytes=0-0", b"0", "bytes 0-0/10"),
                 ("bytes=9-9", b"9", "bytes 9-9/10"),
                 ("bytes=7-", b"789", "bytes 7-9/10"),
                 ("bytes=-3", b"789", "bytes 7-9/10")]
        for header, body, content_range in cases:
            with self.subTest(header=header):
                response = self.get(self.audio_url(), headers={"Range": header})
                self.assertEqual(response.status_code, 206)
                self.assertEqual(response.data, body)
                self.assertEqual(response.headers["Content-Range"], content_range)
                self.assertEqual(int(response.headers["Content-Length"]), len(body))
        with self.client.head(self.audio_url()) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b"")
            self.assertEqual(response.headers["Content-Length"], "10")
        for header in ("bytes=10-", "bytes=9-2", "bytes=invalid", "bytes=0-1,3-4"):
            with self.subTest(header=header):
                response = self.get(self.audio_url(), headers={"Range": header})
                self.assertEqual(response.status_code, 416)

    def test_large_range_is_streamed_in_chunks(self):
        self.audio.write_bytes(b"x" * 65536)
        with server.app.test_request_context(self.audio_url(), headers={"Range": "bytes=0-65535"}):
            response = server.app.full_dispatch_request()
            try:
                self.assertEqual(response.status_code, 206)
                self.assertTrue(response.is_streamed)
                self.assertLess(len(next(iter(response.response))), 65536)
            finally:
                response.close()

    def test_missing_lyrics_do_not_fill_cache(self):
        self.lyrics()
        for number in range(20):
            self.assertFalse(self.lyrics(f"missing-{number}").get_json()["success"])
        self.get("/api/batch-lyrics", query_string={
            "folder": self.folder, "songs": json.dumps(["missing-a", "missing-b"]),
        })
        self.assertEqual(len(server.lyrics_result_cache), 1)

    def test_cache_capacity_and_expired_entries_are_evicted(self):
        names = [self.song, "second", "third"]
        for name in names[1:]:
            directory = self.music / self.folder / name
            directory.mkdir()
            (directory / "lyrics.lrc").write_text(name, encoding="utf-8")
        with patch.object(server, "CACHE_MAX_ENTRIES", 2):
            for name in names:
                self.assertTrue(self.lyrics(name).get_json()["success"])
                self.assertLessEqual(len(server.lyrics_result_cache), 2)
            self.lyric.write_text("changed lyrics", encoding="utf-8")
            with patch.object(server, "CACHE_TTL", -1):
                self.assertEqual(self.lyrics().get_json()["lyrics"], "changed lyrics")
                self.assertLessEqual(len(server.lyrics_result_cache), 1)

    def test_invalid_batch_parameters_are_rejected(self):
        invalid = ["{", "null", "true", "5", '"song"', "{}", "[1]", "[null]",
                   json.dumps(["x"] * (server.MAX_BATCH_SONGS + 1)),
                   json.dumps(["x" * (server.MAX_NAME_LENGTH + 1)]),
                   json.dumps(["../song"]), " " * (1024 * 1024) + "[]"]
        for value in invalid:
            with self.subTest(value=value[:80], length=len(value)):
                response = self.get("/api/batch-lyrics", query_string={
                    "folder": self.folder, "songs": value,
                })
                self.assertEqual(response.status_code, 400)
        for folder, song in (("../music", self.song), (self.folder, "../song"),
                             ("x" * (server.MAX_NAME_LENGTH + 1), self.song),
                             (self.folder, "x" * (server.MAX_NAME_LENGTH + 1))):
            self.assertEqual(self.lyrics(song, folder).status_code, 400)

    def test_oversized_lyrics_are_not_read_without_a_bound(self):
        self.lyric.write_bytes(b"x" * 100)
        real_open = io.open

        class BoundedReader:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def __getattr__(self, name):
                return getattr(self.stream, name)
            def read(self, size=-1):
                if not 0 <= size <= 33:
                    raise AssertionError("Lyrics read must be bounded before loading")
                return self.stream.read(size)

        def guarded_open(file, *args, **kwargs):
            stream = real_open(file, *args, **kwargs)
            return BoundedReader(stream) if Path(file) == self.lyric else stream

        with patch.object(server, "MAX_LYRICS_BYTES", 32), \
                patch("builtins.open", guarded_open), patch("io.open", guarded_open):
            self.assertFalse(self.lyrics().get_json()["success"])


if __name__ == "__main__":
    unittest.main()
