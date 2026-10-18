"""扫描器与 ffprobe 集成测试（需要系统 ffmpeg；缺失时自动跳过）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from melody_app.core.db import Database  # noqa: E402


import shutil
import uuid


def make_temp_dir(prefix: str = "melody") -> str:
    """在当前工作区的 .cache 下建目录（继承 ACL，兼容受限沙箱；不用 mkdtemp）。"""
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path

from melody_app.core.scanner import ScanWorker  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def make_track(directory: str, name: str, codec: str, **tags: str) -> str:
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
        codec,
    ]
    for key, value in tags.items():
        args += ["-metadata", f"{key}={value}"]
    args.append(target)
    subprocess.run(args, check=True, capture_output=True)
    return target


@unittest.skipUnless(HAS_FFMPEG, "需要 ffmpeg/ffprobe")
class ScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.music_dir = make_temp_dir("music")
        self.data_dir = make_temp_dir("data")
        os.environ["MELODY_DATA_DIR"] = self.data_dir
        self.db = Database(os.path.join(self.data_dir, "test.db"))

        make_track(self.music_dir, "01 - 林深 - 晨雾.mp3", "libmp3lame",
                   title="晨雾", artist="林深", album="雾气中的信号", track="1")
        make_track(self.music_dir, "02 - Nova - Orbit.flac", "flac",
                   title="Orbit", artist="Nova Sound", album="Orbital Drift", track="2")
        make_track(self.music_dir, "03 - 夜航 - 灯塔.ogg", "libvorbis",
                   title="灯塔", artist="夜航", album="夜航船", track="3")

    def tearDown(self) -> None:
        self.db.conn.close()
        shutil.rmtree(self.music_dir, ignore_errors=True)
        shutil.rmtree(self.data_dir, ignore_errors=True)
        os.environ.pop("MELODY_DATA_DIR", None)

    def _scan(self) -> dict:
        folder_id = self.db.add_folder(self.music_dir)
        worker = ScanWorker(self.db, folder_id, self.music_dir)
        results: list[dict] = []
        worker.finished_scan.connect(results.append)
        worker.run()  # 直接同步执行，不依赖 Qt 事件循环
        return results[0]

    def test_scan_reads_tags_from_all_formats(self) -> None:
        stats = self._scan()
        self.assertEqual(stats["added"], 3)
        self.assertEqual(stats["failed"], 0)

        songs = {song.title: song for song in self.db.list_songs()}
        self.assertIn("晨雾", songs)
        self.assertIn("Orbit", songs)
        self.assertIn("灯塔", songs)
        self.assertEqual(songs["灯塔"].artist, "夜航")
        self.assertEqual(songs["Orbit"].album, "Orbital Drift")
        self.assertGreater(songs["晨雾"].duration_ms or 0, 500)

    def test_rescan_is_incremental(self) -> None:
        self._scan()
        stats = self._scan()
        self.assertEqual(stats["added"], 0)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.db.song_count(), 3)

    def test_removed_file_is_pruned(self) -> None:
        self._scan()
        os.remove(os.path.join(self.music_dir, "01 - 林深 - 晨雾.mp3"))
        stats = self._scan()
        self.assertEqual(stats["removed"], 1)
        self.assertEqual(self.db.song_count(), 2)


if __name__ == "__main__":
    unittest.main()
