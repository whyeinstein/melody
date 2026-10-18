"""底部播放条：全局常驻，显示当前曲目与传输控制。"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Song
from ..core.playback.queue import RepeatMode
from .app_context import AppContext
from .widgets.common import format_ms
from .widgets.cover import CoverLabel

REPEAT_SHORT = {
    RepeatMode.OFF: "顺序",
    RepeatMode.ALL: "循环",
    RepeatMode.ONE: "单曲",
}


class PlayerBar(QFrame):
    open_player = pyqtSignal()

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._seeking = False
        self.setObjectName("playerBar")
        self.setFixedHeight(76)
        self._build_ui()
        self._connect()
        self._update_track(None)
        self._sync_modes()
        self._update_volume(ctx.playback.volume)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self.cover = CoverLabel(52)
        layout.addWidget(self.cover)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("未在播放")
        self.title_label.setObjectName("playerTitle")
        self.artist_label = QLabel("—")
        self.artist_label.setObjectName("playerArtist")
        self.title_label.setMinimumWidth(150)
        self.title_label.setMaximumWidth(240)
        info.addWidget(self.title_label)
        info.addWidget(self.artist_label)
        layout.addLayout(info)

        self.prev_button = QPushButton("◀◀")
        self.prev_button.setObjectName("transport")
        self.prev_button.setToolTip("上一首")
        self.prev_button.clicked.connect(self._ctx.playback.previous_track)
        layout.addWidget(self.prev_button)

        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("transportPrimary")
        self.play_button.setToolTip("播放 / 暂停")
        self.play_button.clicked.connect(self._ctx.playback.toggle)
        layout.addWidget(self.play_button)

        self.next_button = QPushButton("▶▶")
        self.next_button.setObjectName("transport")
        self.next_button.setToolTip("下一首")
        self.next_button.clicked.connect(lambda: self._ctx.playback.next_track(manual=True))
        layout.addWidget(self.next_button)

        self.position_label = QLabel("0:00")
        self.position_label.setObjectName("muted")
        layout.addWidget(self.position_label)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(
            lambda value: self.position_label.setText(format_ms(value))
        )
        layout.addWidget(self.seek_slider, 1)

        self.duration_label = QLabel("0:00")
        self.duration_label.setObjectName("muted")
        layout.addWidget(self.duration_label)

        self.shuffle_button = QPushButton("随机")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.setToolTip("随机播放")
        self.shuffle_button.clicked.connect(self._on_shuffle_clicked)
        layout.addWidget(self.shuffle_button)

        self.repeat_button = QPushButton("顺序")
        self.repeat_button.setToolTip("播放模式：顺序 / 列表循环 / 单曲循环")
        self.repeat_button.clicked.connect(self._on_repeat_clicked)
        layout.addWidget(self.repeat_button)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.setToolTip("音量")
        self.volume_slider.valueChanged.connect(self._ctx.playback.set_volume)
        layout.addWidget(self.volume_slider)

        self.player_page_button = QPushButton("队列")
        self.player_page_button.setToolTip("打开播放页")
        self.player_page_button.clicked.connect(self.open_player.emit)
        layout.addWidget(self.player_page_button)

    def _connect(self) -> None:
        playback = self._ctx.playback
        playback.track_changed.connect(self._update_track)
        playback.state_changed.connect(self._on_state_changed)
        playback.position_changed.connect(self._on_position_changed)
        playback.duration_changed.connect(self._on_duration_changed)
        playback.volume_changed.connect(self._update_volume)
        playback.mode_changed.connect(self._sync_modes)

    # ------------------------------------------------------------------ 刷新
    def _update_track(self, song: Song | None) -> None:
        if song is None:
            self.cover.set_cover(None)
            self.title_label.setText("未在播放")
            self.artist_label.setText("—")
            self.setToolTip("")
            return
        self.cover.set_cover(song.cover_path, seed=song.album or song.title)
        self.title_label.setText(song.title)
        self.artist_label.setText(song.artist_text)
        self.setToolTip(f"{song.title}\n{song.artist_text}\n{song.album_text}")

    def _on_state_changed(self, state: str) -> None:
        self.play_button.setText("❚❚" if state == "playing" else "▶")

    def _on_position_changed(self, position: int) -> None:
        if not self._seeking:
            self.seek_slider.setValue(position)
        self.position_label.setText(format_ms(position))

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, max(0, duration))
        self.duration_label.setText(format_ms(duration))

    def _update_volume(self, volume: int) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)

    def _sync_modes(self) -> None:
        self.shuffle_button.setChecked(self._ctx.playback.shuffle)
        mode = self._ctx.playback.repeat
        self.repeat_button.setText(REPEAT_SHORT.get(mode, "顺序"))
        self.repeat_button.setToolTip(f"播放模式：{mode.label}")

    # ------------------------------------------------------------------ 动作
    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self._ctx.playback.seek(self.seek_slider.value())

    def _on_shuffle_clicked(self) -> None:
        self._ctx.playback.set_shuffle(self.shuffle_button.isChecked())
        self._sync_modes()

    def _on_repeat_clicked(self) -> None:
        self._ctx.playback.cycle_repeat()
        self._sync_modes()
