"""音频引擎：QMediaPlayer + 非原生格式的 ffmpeg 转码缓存。"""

from __future__ import annotations

import hashlib
import os
import time

from PyQt5.QtCore import QObject, QThread, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

from ...config import cache_dir
from ..library import ffprobe

# QtMultimedia 在 Windows 上走 DirectShow，直接可播的格式很少；
# 其余格式先转码成 WAV 再播放，换取稳定与 seek 支持。
NATIVE_FORMATS = {".mp3", ".wav"}


class TranscodeWorker(QThread):
    done = pyqtSignal(str, str)  # (wav 路径, 错误信息)

    def __init__(self, source: str, mtime_ms: int) -> None:
        super().__init__()
        self._source = source
        self._mtime_ms = mtime_ms

    def _target(self) -> str:
        digest = hashlib.sha1(f"{self._source}:{self._mtime_ms}".encode("utf-8")).hexdigest()[:20]
        return os.path.join(cache_dir(), digest + ".wav")

    def run(self) -> None:
        target = self._target()
        if os.path.exists(target) and os.path.getsize(target) > 1024:
            self.done.emit(target, "")
            return
        ok = ffprobe.transcode_to_wav(self._source, target)
        if ok and os.path.exists(target):
            self.done.emit(target, "")
        else:
            self.done.emit("", "无法解码该音频文件")


class AudioEngine(QObject):
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)  # loading / playing / paused / stopped / error
    error_occurred = pyqtSignal(str)
    track_started = pyqtSignal(str)  # 实际播放的本地路径

    def __init__(self) -> None:
        super().__init__()
        self._media = QMediaPlayer(None)
        self._media.stateChanged.connect(self._on_state)
        self._media.positionChanged.connect(self.position_changed.emit)
        self._media.durationChanged.connect(self._on_duration)
        self._media.error.connect(self._on_error)
        self._media.mediaStatusChanged.connect(self._on_status)
        self._worker: TranscodeWorker | None = None
        self._pending_autoplay = False
        self._volume = 80
        self._muted = False
        self._media.setVolume(self._volume)
        self.current_path: str | None = None

    # ---------------------------------------------------------------- 控制
    def set_volume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))
        self._apply_volume()

    @property
    def volume(self) -> int:
        return self._volume

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self._apply_volume()

    @property
    def muted(self) -> bool:
        return self._muted

    def _apply_volume(self) -> None:
        self._media.setVolume(0 if self._muted else self._volume)

    def play_path(self, path: str, autoplay: bool = True) -> None:
        self.current_path = path
        self._pending_autoplay = autoplay
        extension = os.path.splitext(path)[1].lower()
        if extension in NATIVE_FORMATS:
            self._load(path)
            return
        try:
            mtime_ms = int(os.stat(path).st_mtime * 1000)
        except OSError:
            mtime_ms = int(time.time() * 1000)
        self.state_changed.emit("loading")
        self._worker = TranscodeWorker(path, mtime_ms)
        self._worker.done.connect(self._on_transcoded)
        self._worker.start()

    def _on_transcoded(self, target: str, error: str) -> None:
        if error:
            self.state_changed.emit("error")
            self.error_occurred.emit(error)
            return
        self._load(target)

    def _load(self, path: str) -> None:
        self._media.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.track_started.emit(path)
        if self._pending_autoplay:
            self._media.play()

    def toggle(self) -> None:
        if self._media.state() == QMediaPlayer.PlayingState:
            self._media.pause()
        else:
            self._media.play()

    def play(self) -> None:
        self._media.play()

    def pause(self) -> None:
        self._media.pause()

    def stop(self) -> None:
        self._media.stop()

    def seek(self, position_ms: int) -> None:
        self._media.setPosition(max(0, int(position_ms)))

    def position(self) -> int:
        return int(self._media.position())

    def duration(self) -> int:
        return int(self._media.duration())

    def is_playing(self) -> bool:
        return self._media.state() == QMediaPlayer.PlayingState

    # ---------------------------------------------------------------- 事件
    def _on_state(self, state) -> None:
        if state == QMediaPlayer.PlayingState:
            self.state_changed.emit("playing")
        elif state == QMediaPlayer.PausedState:
            self.state_changed.emit("paused")
        elif state == QMediaPlayer.StoppedState:
            self.state_changed.emit("stopped")

    def _on_duration(self, duration: int) -> None:
        self.duration_changed.emit(int(duration))

    def _on_status(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self.state_changed.emit("ended")

    def _on_error(self, _error) -> None:
        message = self._media.errorString()
        self.state_changed.emit("error")
        self.error_occurred.emit(message)
