"""歌曲页：全部歌曲 + 搜索 / 筛选 / 排序 / 右键菜单。"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..app_context import AppContext
from ..icons import icon
from ..song_actions import show_song_context_menu
from ..widgets.common import EmptyState, PageHeader, format_total_duration
from ..widgets.song_table import SongTableView
from ...core.models import Song


class SongsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._source_id: int | None = None
        self._filter = "all"
        self._sort_field = "artist"
        self._sort_direction = "asc"

        self._build_ui()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(16)

        self.header = PageHeader("歌曲", "")
        layout.addWidget(self.header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索标题、艺术家或专辑…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(260)
        self.search_edit.addAction(icon("search", "#667086", 16), QLineEdit.LeadingPosition)
        toolbar.addWidget(self.search_edit, 1)

        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        self._filter_buttons: dict[str, QPushButton] = {}
        for label, value in (("全部", "all"), ("收藏", "favorite"), ("最近播放", "recent")):
            chip = QPushButton(label)
            chip.setObjectName("chip")
            chip.setCheckable(True)
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _checked=False, key=value: self._set_filter(key))
            self.filter_group.addButton(chip)
            self._filter_buttons[value] = chip
            toolbar.addWidget(chip)
        self._filter_buttons["all"].setChecked(True)

        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(140)
        toolbar.addWidget(self.source_combo)
        layout.addLayout(toolbar)

        self.table = SongTableView()
        self.table.set_sort("artist", "asc")
        self.empty_state = EmptyState("音乐库还是空的", "到「音乐库」页添加一个音乐文件夹开始扫描。")
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty_state)
        layout.addWidget(self.stack, 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)

    def _connect(self) -> None:
        self._search_timer.timeout.connect(self.reload)
        self.search_edit.textChanged.connect(lambda _text: self._search_timer.start())
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.table.song_activated.connect(self.play_song)
        self.table.sort_requested.connect(self._on_sort_requested)
        self.table.song_context_menu.connect(self._on_context_menu)

        self._ctx.library_changed.connect(self.refresh)
        self._ctx.sources_changed.connect(self._refresh_sources)
        self._ctx.favorite_changed.connect(self.table.update_favorite)
        self._ctx.playback.track_changed.connect(self._on_track_changed)
        current = self._ctx.playback.current_song
        self.table.set_playing(current.id if current else None)

    # ------------------------------------------------------------------ 数据
    def refresh(self) -> None:
        self._refresh_sources()
        self.reload()

    def _refresh_sources(self) -> None:
        current = self._source_id
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem("全部来源", None)
        for source in self._ctx.library.enabled_sources():
            self.source_combo.addItem(source.name, source.id)
        index = self.source_combo.findData(current)
        self.source_combo.setCurrentIndex(index if index >= 0 else 0)
        self._source_id = self.source_combo.currentData()
        self.source_combo.blockSignals(False)

    def reload(self) -> None:
        search = self.search_edit.text()
        favorite = True if self._filter == "favorite" else None
        recent = self._filter == "recent"
        songs = self._ctx.songs.query(
            search=search,
            source_id=self._source_id,
            favorite=favorite,
            recent=recent,
            sort=self._sort_field,
            direction=self._sort_direction,
        )
        self.table.set_songs(songs)
        total = sum(song.duration_ms or 0 for song in songs)
        self.header.set_subtitle(f"共 {len(songs)} 首 · 总时长 {format_total_duration(total)}")

        if songs:
            self.stack.setCurrentWidget(self.table)
        else:
            if search.strip():
                self.empty_state.set_content(
                    "没有找到匹配的歌曲", "换个关键词，或清空搜索条件。", icon="?"
                )
            elif self._filter == "favorite":
                self.empty_state.set_content(
                    "还没有收藏的歌曲", "在歌曲上右键选择「收藏」，之后会出现在这里。", icon="♥"
                )
            elif self._filter == "recent":
                self.empty_state.set_content(
                    "还没有播放记录", "播放过的歌曲会按时间出现在这里。", icon="⏱"
                )
            else:
                self.empty_state.set_content(
                    "音乐库还是空的", "到「音乐库」页添加一个音乐文件夹开始扫描。", icon="♪"
                )
            self.stack.setCurrentWidget(self.empty_state)

    # ------------------------------------------------------------------ 交互
    def _set_filter(self, key: str) -> None:
        self._filter = key
        button = self._filter_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        self.reload()

    def _on_source_changed(self) -> None:
        self._source_id = self.source_combo.currentData()
        self.reload()

    def _on_sort_requested(self, field: str, direction: str) -> None:
        self._sort_field = field
        self._sort_direction = direction
        self.reload()

    def set_source_filter(self, source_id: int | None) -> None:
        index = self.source_combo.findData(source_id)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)
        self._source_id = source_id
        self.reload()

    def _on_track_changed(self, song) -> None:
        self.table.set_playing(song.id if song else None)

    def play_song(self, song: Song) -> None:
        songs = self.table.songs()
        index = next((i for i, item in enumerate(songs) if item.id == song.id), -1)
        if index >= 0:
            self._ctx.playback.play_songs(songs, index)

    def _on_context_menu(self, song: Song, position) -> None:
        show_song_context_menu(self, self._ctx, song, position, on_play=self.play_song)

    def focus_search(self) -> None:
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.focus_search()
            return
        super().keyPressEvent(event)
