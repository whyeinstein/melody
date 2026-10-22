"""播放页：大封面、传输控制与当前播放队列。"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Song
from ...core.playback.queue import RepeatMode
from ..app_context import AppContext
from ..icons import icon
from ..theme import DEFAULT_ACCENT, TEXT, TEXT_MUTED
from ..widgets.common import Card, PageHeader, format_ms, muted_label
from ..widgets.cover import CoverLabel


class PlayerPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._seeking = False
        self._current_song: Song | None = None
        self._accent = ctx.settings.accent or DEFAULT_ACCENT

        self._build_ui()
        self._connect()
        self._sync_modes()
        self._update_track(None)
        self._rebuild_queue()
        self._refresh_icons()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(16)

        self.header = PageHeader("播放", "正在播放与播放队列")
        layout.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(20)

        # ---------------------------------------------------- 左侧：正在播放
        now_card = Card(spacing=12, margins=(28, 28, 28, 24))
        now_layout = now_card.body()
        cover_row = QHBoxLayout()
        cover_row.addStretch(1)
        self.cover = CoverLabel(300)
        cover_row.addWidget(self.cover)
        cover_row.addStretch(1)
        now_layout.addLayout(cover_row)
        now_layout.addSpacing(4)

        self.title_label = QLabel("未在播放")
        self.title_label.setObjectName("nowTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.artist_label = QLabel("从歌曲或专辑开始播放")
        self.artist_label.setObjectName("nowArtist")
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.album_label = QLabel("")
        self.album_label.setObjectName("dim")
        self.album_label.setAlignment(Qt.AlignCenter)
        now_layout.addWidget(self.title_label)
        now_layout.addWidget(self.artist_label)
        now_layout.addWidget(self.album_label)

        favorite_row = QHBoxLayout()
        favorite_row.addStretch(1)
        self.favorite_button = QPushButton()
        self.favorite_button.setObjectName("iconButton")
        self.favorite_button.setCheckable(True)
        self.favorite_button.setToolTip("收藏")
        self.favorite_button.setCursor(Qt.PointingHandCursor)
        self.favorite_button.clicked.connect(self._toggle_favorite)
        favorite_row.addWidget(self.favorite_button)
        favorite_row.addStretch(1)
        now_layout.addLayout(favorite_row)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setCursor(Qt.PointingHandCursor)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        now_layout.addWidget(self.seek_slider)

        time_row = QHBoxLayout()
        self.position_label = muted_label("0:00")
        self.position_label.setObjectName("timeLabel")
        self.duration_label = muted_label("0:00")
        self.duration_label.setObjectName("timeLabel")
        time_row.addWidget(self.position_label)
        time_row.addStretch(1)
        time_row.addWidget(self.duration_label)
        now_layout.addLayout(time_row)

        transport = QHBoxLayout()
        transport.setSpacing(6)
        transport.addStretch(1)
        self.shuffle_button = QPushButton()
        self.shuffle_button.setObjectName("iconButton")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.setToolTip("随机播放")
        self.shuffle_button.setCursor(Qt.PointingHandCursor)
        self.shuffle_button.clicked.connect(self._on_shuffle_clicked)
        transport.addWidget(self.shuffle_button)

        self.prev_button = QPushButton()
        self.prev_button.setObjectName("transport")
        self.prev_button.setToolTip("上一首")
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.clicked.connect(self._ctx.playback.previous_track)
        transport.addWidget(self.prev_button)

        self.play_button = QPushButton()
        self.play_button.setObjectName("transportPrimary")
        self.play_button.setToolTip("播放 / 暂停")
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.clicked.connect(self._ctx.playback.toggle)
        transport.addWidget(self.play_button)

        self.next_button = QPushButton()
        self.next_button.setObjectName("transport")
        self.next_button.setToolTip("下一首")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(lambda: self._ctx.playback.next_track(manual=True))
        transport.addWidget(self.next_button)

        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("iconButton")
        self.repeat_button.setToolTip("播放模式：顺序 / 列表循环 / 单曲循环")
        self.repeat_button.setCursor(Qt.PointingHandCursor)
        self.repeat_button.clicked.connect(self._on_repeat_clicked)
        transport.addWidget(self.repeat_button)
        transport.addStretch(1)
        now_layout.addLayout(transport)

        for button in (
            self.favorite_button,
            self.shuffle_button,
            self.prev_button,
            self.play_button,
            self.next_button,
            self.repeat_button,
        ):
            button.setIconSize(QSize(20, 20))
        body.addWidget(now_card, 3)

        # ------------------------------------------------------ 右侧：队列
        queue_card = Card(spacing=10, margins=(18, 18, 18, 14))
        queue_layout = queue_card.body()
        queue_header = QHBoxLayout()
        self.queue_title = QLabel("播放队列")
        self.queue_title.setObjectName("sectionTitle")
        queue_header.addWidget(self.queue_title)
        queue_header.addStretch(1)
        self.clear_button = QPushButton("清空")
        self.clear_button.setObjectName("ghost")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self._ctx.playback.clear_queue)
        queue_header.addWidget(self.clear_button)
        queue_layout.addLayout(queue_header)

        self.queue_list = QListWidget()
        self.queue_list.setSpacing(1)
        self.queue_list.doubleClicked.connect(self._on_queue_activated)
        queue_layout.addWidget(self.queue_list, 1)
        self.queue_empty = QLabel("队列是空的\n在歌曲列表里双击任意歌曲开始播放")
        self.queue_empty.setObjectName("emptyHint")
        self.queue_empty.setAlignment(Qt.AlignCenter)
        queue_layout.addWidget(self.queue_empty, 1)
        body.addWidget(queue_card, 2)

        layout.addLayout(body, 1)

    def _connect(self) -> None:
        playback = self._ctx.playback
        playback.track_changed.connect(self._update_track)
        playback.state_changed.connect(self._on_state_changed)
        playback.position_changed.connect(self._on_position_changed)
        playback.duration_changed.connect(self._on_duration_changed)
        playback.queue_changed.connect(self._rebuild_queue)
        playback.mode_changed.connect(self._sync_modes)
        self._ctx.favorite_changed.connect(self._on_favorite_changed)
        self._ctx.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ 图标
    def _refresh_icons(self) -> None:
        accent = self._accent
        self.favorite_button.setIcon(
            icon("heart", accent if self.favorite_button.isChecked() else TEXT_MUTED, 20)
        )
        self.shuffle_button.setIcon(
            icon("shuffle", accent if self.shuffle_button.isChecked() else TEXT_MUTED, 20)
        )
        repeat_icon = "repeat-one" if self._ctx.playback.repeat == RepeatMode.ONE else "repeat"
        active = accent if self._ctx.playback.repeat != RepeatMode.OFF else TEXT_MUTED
        self.repeat_button.setIcon(icon(repeat_icon, active, 20))
        self.prev_button.setIcon(icon("prev", TEXT, 20))
        self.next_button.setIcon(icon("next", TEXT, 20))
        state = self._ctx.playback.state
        self.play_button.setIcon(icon("pause" if state == "playing" else "play", "#ffffff", 20))

    def _on_theme_changed(self) -> None:
        self._accent = self._ctx.settings.accent or DEFAULT_ACCENT
        self._refresh_icons()
        self._rebuild_queue()

    # ------------------------------------------------------------------ 刷新
    def refresh(self) -> None:
        self._sync_modes()
        self._rebuild_queue()
        self._update_track(self._ctx.playback.current_song)

    def _update_track(self, song: Song | None) -> None:
        self._current_song = song
        if song is None:
            self.cover.set_cover(None)
            self.title_label.setText("未在播放")
            self.artist_label.setText("从歌曲或专辑开始播放")
            self.album_label.setText("")
            self.favorite_button.setEnabled(False)
            self.favorite_button.setChecked(False)
            self.header.set_subtitle("正在播放与播放队列")
            self._refresh_icons()
            return
        self.cover.set_cover(song.cover_path, seed=song.album or song.title)
        self.title_label.setText(song.title)
        self.artist_label.setText(song.artist_text)
        self.album_label.setText(song.album_text)
        self.favorite_button.setEnabled(True)
        self.favorite_button.setChecked(song.favorite)
        self.header.set_subtitle(f"正在播放 · {song.artist_text}")
        self._refresh_icons()

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

    def _sync_modes(self) -> None:
        self.shuffle_button.setChecked(self._ctx.playback.shuffle)
        mode = self._ctx.playback.repeat
        self.repeat_button.setToolTip(f"播放模式：{mode.label}")
        self._refresh_icons()

    def _rebuild_queue(self) -> None:
        queue = self._ctx.playback.queue
        items = queue.items
        self.queue_title.setText(f"播放队列 · {len(items)}")
        self.queue_list.blockSignals(True)
        self.queue_list.clear()
        for index, song in enumerate(items):
            item = QListWidgetItem(f"{index + 1:02d}   {song.title}\n       {song.artist_text}")
            item.setData(Qt.UserRole, song.id)
            item.setSizeHint(QSize(0, 52))
            self.queue_list.addItem(item)
        current = queue.current_index
        if 0 <= current < self.queue_list.count():
            self.queue_list.setCurrentRow(current)
            current_item = self.queue_list.item(current)
            if current_item is not None:
                current_item.setForeground(QColor(self._accent))
        self.queue_list.blockSignals(False)
        self.clear_button.setEnabled(bool(items))
        self.queue_empty.setVisible(not items)
        self.queue_list.setVisible(bool(items))

    def _on_queue_activated(self, index) -> None:
        if index.isValid():
            self._ctx.playback.jump_to(index.row())

    # ------------------------------------------------------------------ 动作
    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_moved(self, value: int) -> None:
        self.position_label.setText(format_ms(value))

    def _on_seek_end(self) -> None:
        self._seeking = False
        self._ctx.playback.seek(self.seek_slider.value())

    def _on_shuffle_clicked(self) -> None:
        self._ctx.playback.set_shuffle(self.shuffle_button.isChecked())
        self._sync_modes()

    def _on_repeat_clicked(self) -> None:
        self._ctx.playback.cycle_repeat()
        self._sync_modes()

    def _toggle_favorite(self) -> None:
        song = self._current_song
        if song is None:
            return
        favorite = not song.favorite
        self._ctx.songs.set_favorite(song.id, favorite)
        song.favorite = favorite
        self.favorite_button.setChecked(favorite)
        self._refresh_icons()
        self._ctx.favorite_changed.emit(song.id, favorite)

    def _on_favorite_changed(self, song_id: int, favorite: bool) -> None:
        if self._current_song is not None and self._current_song.id == song_id:
            self._current_song.favorite = favorite
            self.favorite_button.setChecked(favorite)
            self._refresh_icons()
