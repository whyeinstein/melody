"""WebDAV 扫描与远程播放地址测试（使用假 WebDAV 服务，不依赖外网）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_webdav import FakeWebDavServer  # noqa: E402
from melody_app.core.db import Database  # noqa: E402
from melody_app.core.library.remote_scanner import RemoteScanWorker  # noqa: E402
from melody_app.core.library.service import LibraryService  # noqa: E402
from melody_app.core.models import Song  # noqa: E402
from melody_app.core.repositories import SongsRepo, SourcesRepo  # noqa: E402
from melody_app.core.sources.webdav_client import WebDavClient, WebDavConfig  # noqa: E402
from melody_app.core.sources.webdav_proxy import shutdown_all  # noqa: E402


def make_temp_dir(prefix: str = "webdav-scan") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def make_mp3_bytes(directory: str, name: str = "track.mp3", **tags: str) -> bytes:
    target = os.path.join(directory, name)
    args = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-c:a",
        "libmp3lame",
    ]
    for key, value in tags.items():
        args += ["-metadata", f"{key}={value}"]
    args.append(target)
    subprocess.run(args, check=True, capture_output=True)
    with open(target, "rb") as handle:
        return handle.read()


class WebDavTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = FakeWebDavServer().__enter__()
        self.server.add_file("a.mp3", b"a")
        self.server.add_file("notes.txt", b"text")
        self.server.add_file(".hidden/secret.mp3", b"hidden")
        self.server.add_file("sub/b.flac", b"b")
        self.server.add_file("sub/cover.jpg", b"img")

    def tearDown(self) -> None:
        self.server.__exit__(None, None, None)

    def test_list_tree_only_audio_and_skips_hidden(self) -> None:
        client = WebDavClient(WebDavConfig(base_url=self.server.base_url))
        paths = [entry.path for entry in client.list_tree()]
        self.assertEqual(paths, ["a.mp3", "sub/b.flac"])

    def test_modified_time_parsed(self) -> None:
        self.server.add_file("dated.mp3", b"x", mtime=1700000000)
        client = WebDavClient(WebDavConfig(base_url=self.server.base_url))
        entry = next(item for item in client.list_tree() if item.path == "dated.mp3")
        self.assertGreater(entry.modified_ms, 0)


@unittest.skipUnless(HAS_FFMPEG, "需要 ffmpeg/ffprobe")
class RemoteScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.data_dir = os.path.join(self.temp, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        os.environ["MELODY_DATA_DIR"] = self.data_dir
        self.db = Database(os.path.join(self.data_dir, "test.db"))
        self.songs = SongsRepo(self.db)
        self.sources = SourcesRepo(self.db)
        self.server = FakeWebDavServer().__enter__()

    def tearDown(self) -> None:
        self.db.close()
        self.server.__exit__(None, None, None)
        shutil.rmtree(self.temp, ignore_errors=True)
        os.environ.pop("MELODY_DATA_DIR", None)

    def _scan(self, source) -> dict:
        worker = RemoteScanWorker(self.db.path, source)
        results: list[dict] = []
        errors: list[str] = []
        worker.finished_scan.connect(results.append)
        worker.failed.connect(errors.append)
        worker.run()
        self.assertTrue(results, f"worker failed: {errors}")
        return results[0]

    def test_scan_incremental_and_remove(self) -> None:
        payload = make_mp3_bytes(self.temp, title="晨雾", artist="林深", album="雾气中的信号")
        self.server.add_file("tracks/晨雾.mp3", payload, mtime=1700000100)
        source = self.sources.add_remote("测试 NAS", self.server.base_url)

        stats = self._scan(source)
        self.assertEqual(stats["added"], 1)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["source_id"], source.id)

        songs = self.songs.query()
        self.assertEqual(len(songs), 1)
        song = songs[0]
        self.assertEqual(song.source_id, source.id)
        self.assertEqual(song.path, "tracks/晨雾.mp3")
        self.assertEqual(song.title, "晨雾")
        self.assertEqual(song.artist, "林深")
        self.assertEqual(song.format, "mp3")
        self.assertGreater(song.duration_ms or 0, 500)

        # 第二次扫描应全部视为未变化
        stats = self._scan(source)
        self.assertEqual(stats["added"], 0)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.songs.count(), 1)

        # 远程文件消失后清理
        self.server.remove_file("tracks/晨雾.mp3")
        stats = self._scan(source)
        self.assertEqual(stats["removed"], 1)
        self.assertEqual(self.songs.count(), 0)

    def test_stream_url_for_remote_song(self) -> None:
        source = self.sources.add_remote("测试 NAS", self.server.base_url)
        service = LibraryService(self.songs, self.sources)
        song = Song(
            id=1,
            path="a b.mp3",
            source_id=source.id,
            title="x",
            artist=None,
            album=None,
        )
        try:
            url = service.stream_url_for(song)
            self.assertTrue(url.startswith("http://127.0.0.1:"), url)
            self.assertIn("/media/", url)
            self.assertIn("a%20b.mp3", url)
        finally:
            shutdown_all()


if __name__ == "__main__":
    unittest.main()
