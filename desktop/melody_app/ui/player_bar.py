"""底部播放条：当前曲目、传输控制、进度与音量。"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt, pyqtSignal
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
from .icons import icon
from .theme import DEFAULT_ACCENT, TEXT, TEXT_MUTED
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
        self._accent = DEFAULT_ACCENT
        self._last_volume = max(1, ctx.playback.volume)
        self.setObjectName("playerBar")
        self.setFixedHeight(92)
        self._build_ui()
        self._connect()
        self._update_track(None)
        self._sync_modes()
        self._update_volume(ctx.playback.volume)
        self._refresh_icons()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(18)

        # 左侧：封面 + 曲目信息
        left = QWidget()
        left.setFixedWidth(300)
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        self.cover = CoverLabel(54)
        left_layout.addWidget(self.cover)
        info = QVBoxLayout()
        info.setSpacing(3)
        info.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("未在播放")
        self.title_label.setObjectName("playerTitle")
        self.artist_label = QLabel("选择一首歌开始播放")
        self.artist_label.setObjectName("playerArtist")
        for label in (self.title_label, self.artist_label):
            label.setMaximumWidth(220)
        info.addStretch(1)
        info.addWidget(self.title_label)
        info.addWidget(self.artist_label)
        info.addStretch(1)
        left_layout.addLayout(info, 1)
        layout.addWidget(left)

        # 中间：传输控制 + 进度
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 2, 0, 2)
        center_layout.setSpacing(4)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.addStretch(1)
        self.prev_button = QPushButton()
        self.prev_button.setObjectName("transport")
        self.prev_button.setToolTip("上一首")
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.clicked.connect(self._ctx.playback.previous_track)
        controls.addWidget(self.prev_button)

        self.play_button = QPushButton()
        self.play_button.setObjectName("transportPrimary")
        self.play_button.setToolTip("播放 / 暂停")
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.clicked.connect(self._ctx.playback.toggle)
        controls.addWidget(self.play_button)

        self.next_button = QPushButton()
        self.next_button.setObjectName("transport")
        self.next_button.setToolTip("下一首")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(lambda: self._ctx.playback.next_track(manual=True))
        controls.addWidget(self.next_button)
        controls.addStretch(1)
        center_layout.addLayout(controls)

        progress = QHBoxLayout()
        progress.setSpacing(10)
        self.position_label = QLabel("0:00")
        self.position_label.setObjectName("timeLabel")
        self.position_label.setFixedWidth(36)
        self.position_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setCursor(Qt.PointingHandCursor)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(
            lambda value: self.position_label.setText(format_ms(value))
        )
        self.duration_label = QLabel("0:00")
        self.duration_label.setObjectName("timeLabel")
        self.duration_label.setFixedWidth(36)
        progress.addWidget(self.position_label)
        progress.addWidget(self.seek_slider, 1)
        progress.addWidget(self.duration_label)
        center_layout.addLayout(progress)
        layout.addWidget(center, 1)

        # 右侧：模式 / 音量 / 队列
        right = QWidget()
        right.setFixedWidth(300)
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.addStretch(1)

        self.shuffle_button = QPushButton()
        self.shuffle_button.setObjectName("iconButton")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.setToolTip("随机播放")
        self.shuffle_button.setCursor(Qt.PointingHandCursor)
        self.shuffle_button.clicked.connect(self._on_shuffle_clicked)
        right_layout.addWidget(self.shuffle_button)

        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("iconButton")
        self.repeat_button.setToolTip("播放模式：顺序 / 列表循环 / 单曲循环")
        self.repeat_button.setCursor(Qt.PointingHandCursor)
        self.repeat_button.clicked.connect(self._on_repeat_clicked)
        right_layout.addWidget(self.repeat_button)

        self.mute_button = QPushButton()
        self.mute_button.setObjectName("iconButton")
        self.mute_button.setToolTip("静音")
        self.mute_button.setCursor(Qt.PointingHandCursor)
        self.mute_button.clicked.connect(self._on_mute_clicked)
        right_layout.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(84)
        self.volume_slider.setToolTip("音量")
        self.volume_slider.setCursor(Qt.PointingHandCursor)
        self.volume_slider.valueChanged.connect(self._ctx.playback.set_volume)
        right_layout.addWidget(self.volume_slider)

        self.queue_button = QPushButton()
        self.queue_button.setObjectName("iconButton")
        self.queue_button.setToolTip("打开播放页与队列")
        self.queue_button.setCursor(Qt.PointingHandCursor)
        self.queue_button.clicked.connect(self.open_player.emit)
        right_layout.addWidget(self.queue_button)
        layout.addWidget(right)

        for button in (
            self.prev_button,
            self.play_button,
            self.next_button,
            self.shuffle_button,
            self.repeat_button,
            self.mute_button,
            self.queue_button,
        ):
            button.setIconSize(QSize(20, 20))

    def _connect(self) -> None:
        playback = self._ctx.playback
        playback.track_changed.connect(self._update_track)
        playback.state_changed.connect(self._on_state_changed)
        playback.position_changed.connect(self._on_position_changed)
        playback.duration_changed.connect(self._on_duration_changed)
        playback.volume_changed.connect(self._update_volume)
        playback.mode_changed.connect(self._sync_modes)

    # ------------------------------------------------------------------ 图标
    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self._refresh_icons()

    def _refresh_icons(self) -> None:
        muted = TEXT_MUTED
        self.prev_button.setIcon(icon("prev", TEXT, 20))
        self.next_button.setIcon(icon("next", TEXT, 20))
        self.play_button.setIcon(
            icon("pause" if self._is_playing else "play", "#ffffff", 20)
        )
        active = self._accent if self.shuffle_button.isChecked() else muted
        self.shuffle_button.setIcon(icon("shuffle", active, 20))
        repeat_icon = "repeat-one" if self._ctx.playback.repeat == RepeatMode.ONE else "repeat"
        active = self._accent if self._ctx.playback.repeat != RepeatMode.OFF else muted
        self.repeat_button.setIcon(icon(repeat_icon, active, 20))
        volume_icon = "volume-mute" if self._ctx.playback.volume == 0 else "volume"
        self.mute_button.setIcon(icon(volume_icon, muted, 20))
        self.queue_button.setIcon(icon("queue", muted, 20))

    @property
    def _is_playing(self) -> bool:
        state = getattr(self._ctx.playback, "state", "")
        return state == "playing"

    # ------------------------------------------------------------------ 刷新
    def _update_track(self, song: Song | None) -> None:
        if song is None:
            self.cover.set_cover(None)
            self.title_label.setText("未在播放")
            self.artist_label.setText("选择一首歌开始播放")
            self.setToolTip("")
            return
        self.cover.set_cover(song.cover_path, seed=song.album or song.title)
        self.title_label.setText(song.title)
        self.artist_label.setText(song.artist_text)
        self.setToolTip(f"{song.title}\n{song.artist_text}\n{song.album_text}")

    def _on_state_changed(self, state: str) -> None:
        self.play_button.setIcon(
            icon("pause" if state == "playing" else "play", "#ffffff", 20)
        )

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
        if volume > 0:
            self._last_volume = volume
        self._refresh_icons()

    def _sync_modes(self) -> None:
        self.shuffle_button.setChecked(self._ctx.playback.shuffle)
        mode = self._ctx.playback.repeat
        self.repeat_button.setToolTip(f"播放模式：{mode.label}")
        self._refresh_icons()

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

    def _on_mute_clicked(self) -> None:
        if self._ctx.playback.volume > 0:
            self._last_volume = self._ctx.playback.volume
            self._ctx.playback.set_volume(0)
        else:
            self._ctx.playback.set_volume(self._last_volume or 60)
