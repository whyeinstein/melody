"""播放队列与控制器测试（用假引擎，不依赖 QtMultimedia 与声卡）。"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from PyQt5.QtCore import QObject, pyqtSignal  # noqa: E402

from melody_app.core.db import Database  # noqa: E402
from melody_app.core.models import Song  # noqa: E402
from melody_app.core.playback.controller import PlaybackController  # noqa: E402
from melody_app.core.playback.queue import PlayQueue, RepeatMode  # noqa: E402
from melody_app.core.repositories import SettingsRepo, SongsRepo, SourcesRepo  # noqa: E402


def make_temp_dir(prefix: str = "melody") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


def make_song(song_id: int, title: str | None = None) -> Song:
    return Song(
        id=song_id,
        path=rf"D:\music\{song_id}.mp3",
        source_id=1,
        title=title or f"Song {song_id}",
        artist="Artist",
        album="Album",
        duration_ms=3000,
    )


class FakeEngine(QObject):
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    track_started = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.played: list[str] = []
        self.seeks: list[int] = []
        self.stops = 0
        self._volume = 80
        self._muted = False
        self._playing = False
        self._position = 0

    def play_path(self, path: str, autoplay: bool = True) -> None:
        self.played.append(path)
        self._playing = autoplay
        self.state_changed.emit("playing" if autoplay else "stopped")

    def play(self) -> None:
        self._playing = True
        self.state_changed.emit("playing")

    def pause(self) -> None:
        self._playing = False
        self.state_changed.emit("paused")

    def stop(self) -> None:
        self.stops += 1
        self._playing = False
        self.state_changed.emit("stopped")

    def toggle(self) -> None:
        self.pause() if self._playing else self.play()

    def seek(self, position_ms: int) -> None:
        self.seeks.append(int(position_ms))
        self._position = int(position_ms)

    def position(self) -> int:
        return self._position

    def duration(self) -> int:
        return 3000

    def is_playing(self) -> bool:
        return self._playing

    def set_volume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))

    @property
    def volume(self) -> int:
        return self._volume

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)

    @property
    def muted(self) -> bool:
        return self._muted


class PlayQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue = PlayQueue()
        self.songs = [make_song(1), make_song(2), make_song(3)]

    def test_sequential_auto_stops_at_end(self) -> None:
        self.queue.set_queue(self.songs, 0)
        self.assertEqual(self.queue.next(auto=True).id, 2)
        self.assertEqual(self.queue.next(auto=True).id, 3)
        self.assertIsNone(self.queue.next(auto=True))

    def test_manual_next_wraps(self) -> None:
        self.queue.set_queue(self.songs, 2)
        self.assertEqual(self.queue.next(auto=False).id, 1)

    def test_repeat_all_wraps_on_auto(self) -> None:
        self.queue.set_queue(self.songs, 2)
        self.queue.set_repeat(RepeatMode.ALL)
        self.assertEqual(self.queue.next(auto=True).id, 1)

    def test_repeat_one_returns_current_on_auto(self) -> None:
        self.queue.set_queue(self.songs, 1)
        self.queue.set_repeat(RepeatMode.ONE)
        self.assertEqual(self.queue.next(auto=True).id, 2)

    def test_shuffle_keeps_current_first(self) -> None:
        self.queue.set_shuffle(True)
        self.queue.set_queue(self.songs, 1)
        ordered = self.queue.ordered_items()
        self.assertEqual(ordered[0].id, 2)
        self.assertEqual({song.id for song in ordered}, {1, 2, 3})

    def test_append_deduplicates(self) -> None:
        self.queue.set_queue(self.songs[:2], 0)
        self.assertEqual(self.queue.append([make_song(2), make_song(4)]), 1)
        self.assertEqual(len(self.queue), 3)

    def test_remove_current_advances(self) -> None:
        self.queue.set_queue(self.songs, 0)
        self.queue.remove_at(0)
        self.assertEqual(self.queue.current.id, 2)
        self.assertEqual(len(self.queue), 2)


class PlaybackControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir("playback")
        self.db = Database(os.path.join(self.temp, "test.db"))
        self.songs = SongsRepo(self.db)
        self.sources = SourcesRepo(self.db)
        source = self.sources.add_local(r"D:\music")
        for song_id in (1, 2, 3):
            self.songs.upsert_scan(
                {
                    "path": rf"D:\music\{song_id}.mp3",
                    "source_id": source.id,
                    "title": f"Song {song_id}",
                    "artist": "Artist",
                    "album": "Album",
                    "size": 100,
                    "mtime_ms": 1000,
                    "format": "mp3",
                    "duration_ms": 3000,
                }
            )
        self.songs.commit()
        self.db_songs = self.songs.query(sort="title")
        self.engine = FakeEngine()
        self.queue = PlayQueue()
        self.settings = SettingsRepo(self.db)
        self.controller = PlaybackController(self.engine, self.queue, self.songs, self.settings)
        self.events: list = []
        self.controller.track_changed.connect(lambda song: self.events.append(("track", song)))

    def tearDown(self) -> None:
        self.db.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_play_songs_records_play_and_emits_track(self) -> None:
        self.controller.play_songs(self.db_songs, 1)
        self.assertTrue(self.engine.played)
        self.assertEqual(self.events[-1][0], "track")
        self.assertEqual(self.events[-1][1].id, self.db_songs[1].id)
        played = self.songs.get(self.db_songs[1].id)
        self.assertEqual(played.play_count, 1)
        self.assertEqual(self.settings.get_int("playback.last_song_id", -1), self.db_songs[1].id)

    def test_ended_advances_when_repeat_all(self) -> None:
        self.controller.set_repeat(RepeatMode.ALL)
        self.controller.play_songs(self.db_songs, 2)
        self.engine.state_changed.emit("ended")
        self.assertEqual(self.controller.current_song.id, self.db_songs[0].id)

    def test_ended_stops_when_repeat_off(self) -> None:
        self.controller.play_songs(self.db_songs, 2)
        self.engine.state_changed.emit("ended")
        self.assertEqual(self.controller.current_song.id, self.db_songs[2].id)

    def test_top_level_transport(self) -> None:
        self.controller.play_songs(self.db_songs, 0)
        self.controller.next_track(manual=True)
        self.assertEqual(self.controller.current_song.id, self.db_songs[1].id)
        self.controller.previous_track()
        self.assertEqual(self.controller.current_song.id, self.db_songs[0].id)

    def test_volume_and_modes_persist(self) -> None:
        self.controller.set_volume(35)
        self.assertEqual(self.settings.volume, 35)
        self.controller.set_shuffle(True)
        self.assertTrue(self.settings.shuffle)
        self.controller.cycle_repeat()
        self.assertEqual(self.settings.repeat_mode, RepeatMode.ALL.value)

    def test_restore_session(self) -> None:
        self.controller.play_songs(self.db_songs, 1)
        self.controller.save_session()
        self.controller.stop()
        self.assertTrue(self.controller.restore_session())
        self.assertEqual(self.controller.current_song.id, self.db_songs[1].id)
        self.assertFalse(self.engine.played[-1].endswith(".wav"))


if __name__ == "__main__":
    unittest.main()
