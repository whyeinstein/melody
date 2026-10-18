"""最小自动化测试（不依赖 pytest）：python -m unittest discover -s tests_py"""

from __future__ import annotations

import os
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



class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir("db")
        self.db = Database(os.path.join(self.temp, "test.db"))

    def tearDown(self) -> None:
        self.db.conn.close()

    def _song(self, path: str, **overrides) -> dict:
        data = {
            "path": path,
            "folder_id": 1,
            "title": os.path.splitext(os.path.basename(path))[0],
            "artist": "林深",
            "album": "雾气中的信号",
            "size": 100,
            "mtime_ms": 1000,
            "format": "mp3",
            "duration_ms": 3000,
        }
        data.update(overrides)
        return data

    def test_add_folder_and_upsert_song(self) -> None:
        folder_id = self.db.add_folder(r"D:\music")
        self.assertGreater(folder_id, 0)
        self.db.upsert_song(self._song(r"D:\music\a.mp3", folder_id=folder_id))
        self.db.upsert_song(self._song(r"D:\music\b.mp3", folder_id=folder_id, title="旧城"))
        self.db.commit()
        self.assertEqual(self.db.song_count(), 2)

        folders = self.db.list_folders()
        self.assertEqual(folders[0]["song_count"], 2)

    def test_upsert_updates_existing_row(self) -> None:
        folder_id = self.db.add_folder(r"D:\music")
        path = r"D:\music\a.mp3"
        self.db.upsert_song(self._song(path, folder_id=folder_id))
        self.db.commit()
        first = self.db.find_song_file(path)
        self.assertIsNotNone(first)

        self.db.upsert_song(self._song(path, folder_id=folder_id, title="改名了", size=200, mtime_ms=2000))
        self.db.commit()
        self.assertEqual(self.db.song_count(), 1)
        songs = self.db.list_songs()
        self.assertEqual(songs[0].title, "改名了")

    def test_search_and_folder_filter(self) -> None:
        folder_a = self.db.add_folder(r"D:\a")
        folder_b = self.db.add_folder(r"D:\b")
        self.db.upsert_song(self._song(r"D:\a\晨雾.mp3", folder_id=folder_a, title="晨雾"))
        self.db.upsert_song(self._song(r"D:\b\Orbit.flac", folder_id=folder_b, title="Orbit", artist="Nova Sound"))
        self.db.commit()

        self.assertEqual(len(self.db.list_songs("晨雾")), 1)
        self.assertEqual(len(self.db.list_songs("nova")), 1)
        self.assertEqual(len(self.db.list_songs(folder_id=folder_a)), 1)
        self.assertEqual(len(self.db.list_songs()), 2)

    def test_remove_missing(self) -> None:
        folder_id = self.db.add_folder(r"D:\music")
        self.db.upsert_song(self._song(r"D:\music\a.mp3", folder_id=folder_id))
        self.db.upsert_song(self._song(r"D:\music\b.mp3", folder_id=folder_id))
        self.db.commit()

        removed = self.db.remove_missing(folder_id, [r"D:\music\a.mp3"])
        self.assertEqual(removed, 1)
        self.assertEqual(self.db.song_count(), 1)

    def test_remove_folder_cascades(self) -> None:
        folder_id = self.db.add_folder(r"D:\music")
        self.db.upsert_song(self._song(r"D:\music\a.mp3", folder_id=folder_id))
        self.db.commit()
        self.db.remove_folder(folder_id)
        self.assertEqual(self.db.song_count(), 0)


if __name__ == "__main__":
    unittest.main()
