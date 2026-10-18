"""数据层测试（v2 schema、仓库、歌单、设置、v1→v2 迁移）。"""

from __future__ import annotations

import os
import sqlite3
import sys
import uuid
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from melody_app.core.db import SCHEMA_VERSION, Database  # noqa: E402
from melody_app.core.repositories import (  # noqa: E402
    AlbumsRepo,
    PlaylistsRepo,
    SettingsRepo,
    SongsRepo,
    SourcesRepo,
)

V1_SCHEMA = """
CREATE TABLE folders (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  added_at INTEGER NOT NULL
);
CREATE TABLE songs (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  artist TEXT,
  album TEXT,
  album_artist TEXT,
  genre TEXT,
  year INTEGER,
  track_no INTEGER,
  duration_ms INTEGER,
  bitrate INTEGER,
  sample_rate INTEGER,
  channels INTEGER,
  format TEXT,
  size INTEGER NOT NULL,
  mtime_ms INTEGER NOT NULL,
  cover_path TEXT,
  added_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
"""


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
        self.songs = SongsRepo(self.db)
        self.albums = AlbumsRepo(self.db)
        self.playlists = PlaylistsRepo(self.db)
        self.sources = SourcesRepo(self.db)
        self.settings = SettingsRepo(self.db)

    def tearDown(self) -> None:
        self.db.close()

    # ------------------------------------------------------------------ 辅助
    def _add_source(self, path: str = r"D:\music"):
        return self.sources.add_local(path)

    def _song_row(self, path: str, source_id: int, **overrides) -> dict:
        data = {
            "path": path,
            "source_id": source_id,
            "title": os.path.splitext(os.path.basename(path))[0],
            "artist": "林深",
            "album": "雾气中的信号",
            "album_artist": "林深",
            "size": 100,
            "mtime_ms": 1000,
            "format": "mp3",
            "duration_ms": 3000,
        }
        data.update(overrides)
        return data

    # ------------------------------------------------------------------ 测试
    def test_schema_version_is_v2(self) -> None:
        self.assertEqual(self.db.schema_version(), SCHEMA_VERSION)
        tables = {
            row["name"]
            for row in self.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for expected in ("songs", "sources", "playlists", "playlist_items", "settings", "meta"):
            self.assertIn(expected, tables)
        self.assertNotIn("folders", tables)

    def test_source_and_song_upsert(self) -> None:
        source = self._add_source(r"D:\music")
        self.songs.upsert_scan(self._song_row(r"D:\music\a.mp3", source.id))
        self.songs.upsert_scan(
            self._song_row(r"D:\music\b.mp3", source.id, title="旧城", artist="夜航")
        )
        self.songs.commit()
        self.assertEqual(self.songs.count(), 2)

        found = self.songs.find_file(r"D:\music\a.mp3")
        self.assertIsNotNone(found)

        self.songs.upsert_scan(
            self._song_row(r"D:\music\a.mp3", source.id, title="改名了", size=200, mtime_ms=2000)
        )
        self.songs.commit()
        self.assertEqual(self.songs.count(), 2)
        titles = {song.path: song.title for song in self.songs.query()}
        self.assertEqual(titles[r"D:\music\a.mp3"], "改名了")

    def test_query_search_filter_and_sort(self) -> None:
        source = self._add_source()
        self.songs.upsert_scan(self._song_row(r"D:\music\晨雾.mp3", source.id, title="晨雾"))
        self.songs.upsert_scan(
            self._song_row(
                r"D:\music\Orbit.flac",
                source.id,
                title="Orbit",
                artist="Nova Sound",
                album="Orbital Drift",
                album_artist="Nova Sound",
                format="flac",
                duration_ms=9000,
            )
        )
        self.songs.commit()

        self.assertEqual(len(self.songs.query(search="晨雾")), 1)
        self.assertEqual(len(self.songs.query(search="nova")), 1)
        self.assertEqual(len(self.songs.query(album="Orbital Drift")), 1)
        self.assertEqual(len(self.songs.query(artist="Nova Sound")), 1)
        self.assertEqual(len(self.songs.query(source_id=source.id)), 2)

        by_duration = self.songs.query(sort="duration", direction="desc")
        self.assertEqual(by_duration[0].title, "Orbit")

    def test_favorite_play_count_and_stats(self) -> None:
        source = self._add_source()
        self.songs.upsert_scan(self._song_row(r"D:\music\a.mp3", source.id))
        self.songs.upsert_scan(self._song_row(r"D:\music\b.mp3", source.id, title="B"))
        self.songs.commit()

        target = self.songs.query(search="a")[0]
        self.songs.set_favorite(target.id, True)
        self.songs.record_play(target.id)
        self.songs.record_play(target.id)

        favorites = self.songs.query(favorite=True)
        self.assertEqual(len(favorites), 1)
        self.assertTrue(favorites[0].favorite)
        self.assertEqual(favorites[0].play_count, 2)
        self.assertIsNotNone(favorites[0].last_played_at)
        self.assertEqual(len(self.songs.query(recent=True)), 1)

        stats = self.songs.stats()
        self.assertEqual(stats.songs, 2)
        self.assertEqual(stats.albums, 1)
        self.assertEqual(stats.artists, 1)
        self.assertEqual(stats.duration_ms, 6000)

    def test_album_aggregation(self) -> None:
        source = self._add_source()
        for index in range(3):
            self.songs.upsert_scan(
                self._song_row(
                    rf"D:\music\{index}.mp3",
                    source.id,
                    title=f"Track {index + 1}",
                    track_no=index + 1,
                )
            )
        self.songs.commit()
        albums = self.albums.list()
        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].track_count, 3)
        tracks = self.albums.tracks(albums[0].name, albums[0].album_artist)
        self.assertEqual([track.track_no for track in tracks], [1, 2, 3])

    def test_playlist_crud(self) -> None:
        source = self._add_source()
        for index in range(3):
            self.songs.upsert_scan(self._song_row(rf"D:\music\{index}.mp3", source.id))
        self.songs.commit()
        song_ids = [song.id for song in self.songs.query()]

        playlist = self.playlists.create("通勤")
        self.assertEqual(playlist.track_count, 0)
        self.assertTrue(self.playlists.exists("通勤"))

        self.assertEqual(self.playlists.add_songs(playlist.id, song_ids), 3)
        # 重复添加不会产生重复曲目
        self.assertEqual(self.playlists.add_songs(playlist.id, song_ids[:2]), 0)
        self.assertEqual(self.playlists.get(playlist.id).track_count, 3)

        tracks = self.playlists.tracks(playlist.id)
        self.assertEqual([track.id for track in tracks], song_ids)

        self.assertTrue(self.playlists.move_song(playlist.id, song_ids[2], -1))
        tracks = self.playlists.tracks(playlist.id)
        self.assertEqual(tracks[1].id, song_ids[2])

        self.playlists.remove_song(playlist.id, song_ids[0])
        self.assertEqual(self.playlists.get(playlist.id).track_count, 2)

        self.playlists.rename(playlist.id, "上班路上")
        self.assertEqual(self.playlists.get(playlist.id).name, "上班路上")

        self.playlists.delete(playlist.id)
        self.assertEqual(self.playlists.list(), [])

    def test_settings_roundtrip(self) -> None:
        self.settings.set("playback.volume", 42)
        self.assertEqual(self.settings.get_int("playback.volume", 0), 42)
        self.settings.volume = 55
        self.assertEqual(self.settings.volume, 55)
        self.settings.shuffle = True
        self.assertTrue(self.settings.shuffle)
        self.settings.repeat_mode = "one"
        self.assertEqual(self.settings.repeat_mode, "one")
        self.settings.set("nested", {"a": [1, 2]})
        self.assertEqual(self.settings.get("nested"), {"a": [1, 2]})

    def test_migration_from_v1(self) -> None:
        temp = make_temp_dir("migrate")
        path = os.path.join(temp, "v1.db")
        conn = sqlite3.connect(path)
        conn.executescript(V1_SCHEMA)
        conn.execute(
            "INSERT INTO folders(id, path, added_at) VALUES (1, ?, 111)", (r"D:\music",)
        )
        conn.execute(
            """INSERT INTO songs(path, folder_id, title, artist, album, album_artist, genre,
                   year, track_no, duration_ms, bitrate, sample_rate, channels, format,
                   size, mtime_ms, cover_path, added_at, updated_at)
               VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                r"D:\music\a.mp3", "晨雾", "林深", "雾气中的信号", "林深", "folk",
                2020, 1, 3000, 320000, 44100, 2, "mp3", 100, 1000,
                r"D:\covers\a.jpg", 111, 111,
            ),
        )
        conn.commit()
        conn.close()

        migrated = Database(path)
        try:
            self.assertEqual(migrated.schema_version(), 2)
            self.assertTrue(os.path.exists(path + ".v1.bak"))
            sources = SourcesRepo(migrated)
            songs = SongsRepo(migrated)
            source_rows = sources.list()
            self.assertEqual(len(source_rows), 1)
            self.assertEqual(source_rows[0].kind, "local")
            self.assertEqual(source_rows[0].path, r"D:\music")
            self.assertEqual(source_rows[0].name, "music")

            rows = songs.query()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].source_id, source_rows[0].id)
            self.assertEqual(rows[0].title, "晨雾")
            self.assertFalse(rows[0].favorite)
            self.assertEqual(rows[0].play_count, 0)
            # v1 的 folders 表已并入 sources
            self.assertNotIn(
                "folders",
                {
                    row["name"]
                    for row in migrated.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                },
            )
        finally:
            migrated.close()


if __name__ == "__main__":
    unittest.main()
