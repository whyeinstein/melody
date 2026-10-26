"""播放控制器：队列 + 引擎 + 播放记录 + 会话恢复的唯一入口。"""

from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal

from ..models import Song
from ..repositories.settings import (
    KEY_LAST_POSITION,
    KEY_LAST_SONG,
    KEY_MUTED,
    KEY_RESTORE_SESSION,
    KEY_REPEAT,
    KEY_SHUFFLE,
    KEY_VOLUME,
    SettingsRepo,
)
from ..repositories.songs import SongsRepo
from .engine import AudioEngine
from .queue import PlayQueue, RepeatMode


class PlaybackController(QObject):
    track_changed = pyqtSignal(object)  # Song | None
    state_changed = pyqtSignal(str)  # loading / playing / paused / stopped / error
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    queue_changed = pyqtSignal()
    volume_changed = pyqtSignal(int)
    mode_changed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        engine: AudioEngine,
        queue: PlayQueue,
        songs: SongsRepo,
        settings: SettingsRepo,
        url_resolver=None,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._queue = queue
        self._songs = songs
        self._settings = settings
        self._url_resolver = url_resolver
        self._current_song: Song | None = None
        self._state = "stopped"
        self._pending_seek: int | None = None

        engine.position_changed.connect(self.position_changed.emit)
        engine.duration_changed.connect(self._on_duration)
        engine.state_changed.connect(self._on_state)
        engine.error_occurred.connect(self._on_engine_error)
        queue.changed.connect(self._on_queue_changed)

        volume = settings.volume
        engine.set_volume(volume)
        engine.set_muted(settings.get_bool(KEY_MUTED, False))
        queue.set_repeat(RepeatMode.from_value(settings.repeat_mode))
        queue.set_shuffle(settings.get_bool(KEY_SHUFFLE, False))

    # ------------------------------------------------------------------ 读取
    @property
    def queue(self) -> PlayQueue:
        return self._queue

    @property
    def current_song(self) -> Song | None:
        return self._current_song

    @property
    def state(self) -> str:
        return self._state

    @property
    def volume(self) -> int:
        return self._engine.volume

    @property
    def muted(self) -> bool:
        return self._engine.muted

    @property
    def shuffle(self) -> bool:
        return self._queue.shuffle

    @property
    def repeat(self) -> RepeatMode:
        return self._queue.repeat

    def position(self) -> int:
        return self._engine.position()

    def duration(self) -> int:
        return self._engine.duration()

    # ------------------------------------------------------------------ 播放
    def play_songs(self, songs: list[Song], start: int = 0) -> None:
        if not songs:
            return
        self._queue.set_queue(songs, start)
        self.play_current()

    def play_song(self, song: Song) -> None:
        self.play_songs([song], 0)

    def play_current(self, record: bool = True) -> None:
        song = self._queue.current
        if song is None:
            return
        self._current_song = song
        self._state = "loading"
        self.state_changed.emit("loading")
        self._engine.play_path(self._play_url(song), autoplay=True)
        if record:
            try:
                self._songs.record_play(song.id)
            except Exception:  # noqa: BLE001 - 统计失败不应阻断播放
                pass
        self._settings.set(KEY_LAST_SONG, song.id)
        self._settings.set(KEY_LAST_POSITION, 0)
        self.track_changed.emit(song)

    def _play_url(self, song: Song) -> str:
        """本地曲目直接用路径；远程曲目交给 LibraryService 换成代理 URL。"""
        if self._url_resolver is None:
            return song.path
        try:
            return self._url_resolver(song)
        except Exception:  # noqa: BLE001 - 远程不可用时退回原路径，由引擎报错
            return song.path

    def toggle(self) -> None:
        if self._current_song is None:
            if len(self._queue):
                self.play_current()
            return
        self._engine.toggle()

    def pause(self) -> None:
        self._engine.pause()

    def stop(self) -> None:
        self._engine.stop()
        self._state = "stopped"
        self.state_changed.emit("stopped")

    def next_track(self, manual: bool = True) -> None:
        song = self._queue.next(auto=not manual)
        if song is None:
            if not manual:
                self._state = "stopped"
                self.state_changed.emit("stopped")
            return
        if not manual and song.id == (self._current_song.id if self._current_song else -1):
            # 单曲循环：从头重放。
            self._engine.seek(0)
            self._engine.play()
            return
        self.play_current()

    def previous_track(self) -> None:
        song = self._queue.previous()
        if song is not None:
            self.play_current()

    def jump_to(self, item_index: int) -> None:
        song = self._queue.jump_to(item_index)
        if song is not None:
            self.play_current()

    def seek(self, position_ms: int) -> None:
        self._engine.seek(position_ms)
        self._settings.set(KEY_LAST_POSITION, max(0, int(position_ms)))

    def set_volume(self, value: int) -> None:
        self._engine.set_volume(value)
        self._settings.set(KEY_VOLUME, self._engine.volume)
        self.volume_changed.emit(self._engine.volume)

    def toggle_mute(self) -> None:
        self._engine.set_muted(not self._engine.muted)
        self._settings.set(KEY_MUTED, self._engine.muted)
        self.volume_changed.emit(self._engine.volume)

    def set_shuffle(self, shuffle: bool) -> None:
        self._queue.set_shuffle(shuffle)
        self._settings.set(KEY_SHUFFLE, shuffle)
        self.mode_changed.emit()

    def set_repeat(self, mode: RepeatMode) -> None:
        self._queue.set_repeat(mode)
        self._settings.set(KEY_REPEAT, mode.value)
        self.mode_changed.emit()

    def cycle_repeat(self) -> RepeatMode:
        mode = self._queue.cycle_repeat()
        self._settings.set(KEY_REPEAT, mode.value)
        self.mode_changed.emit()
        return mode

    def clear_queue(self) -> None:
        self._engine.stop()
        self._queue.clear()
        self._current_song = None
        self._state = "stopped"
        self.track_changed.emit(None)
        self.state_changed.emit("stopped")

    # ---------------------------------------------------------------- 会话
    def save_session(self) -> None:
        if self._current_song is not None:
            self._settings.set(KEY_LAST_SONG, self._current_song.id)
            self._settings.set(KEY_LAST_POSITION, max(0, self._engine.position()))

    def restore_session(self) -> bool:
        if not self._settings.get_bool(KEY_RESTORE_SESSION, True):
            return False
        song_id = self._settings.get_int(KEY_LAST_SONG, -1)
        if song_id < 0:
            return False
        song = self._songs.get(song_id)
        if song is None or song.missing:
            return False
        position = self._settings.get_int(KEY_LAST_POSITION, 0)
        self._queue.set_queue([song], 0)
        self._current_song = song
        self._pending_seek = position if position > 1000 else None
        self._engine.play_path(self._play_url(song), autoplay=False)
        self.track_changed.emit(song)
        return True

    # ---------------------------------------------------------------- 事件
    def _on_duration(self, duration: int) -> None:
        self.duration_changed.emit(duration)
        if self._pending_seek is not None and duration > 0:
            target = min(self._pending_seek, max(0, duration - 1000))
            self._pending_seek = None
            self._engine.seek(target)

    def _on_state(self, state: str) -> None:
        if state == "ended":
            self.next_track(manual=False)
            return
        self._state = state
        self.state_changed.emit(state)

    def _on_queue_changed(self) -> None:
        self.queue_changed.emit()
        if self._queue.current is not None and self._queue.current is not self._current_song:
            # 队列被外部跳转（例如播放页双击）时同步当前曲目。
            self._current_song = self._queue.current
            self.track_changed.emit(self._current_song)

    def _on_engine_error(self, message: str) -> None:
        self._state = "error"
        self.error_occurred.emit(message)
