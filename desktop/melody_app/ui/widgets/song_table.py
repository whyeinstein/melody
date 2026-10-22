"""歌曲表：模型 + 视图（封面缩略图、正在播放高亮、列头排序、右键菜单）。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from ...core.models import Song
from ..icons import icon as make_icon
from ..theme import DEFAULT_ACCENT, SURFACE_2, TEXT_MUTED


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    width: int = 100
    alignment: int = int(Qt.AlignLeft | Qt.AlignVCenter)
    sortable: bool = True


COLUMNS: tuple[Column, ...] = (
    Column("favorite", "", 36, int(Qt.AlignCenter), False),
    Column("title", "标题", 300),
    Column("artist", "艺术家", 170),
    Column("album", "专辑", 190),
    Column("duration", "时长", 72, int(Qt.AlignRight | Qt.AlignVCenter)),
    Column("format", "格式", 60, int(Qt.AlignCenter)),
)

SORT_FIELDS = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "duration": "duration",
    "format": "format",
}

_COVER_CACHE: dict[str, QPixmap] = {}
_COVER_SIZE = 34


def _placeholder_pixmap(seed: str, size: int = _COVER_SIZE) -> QPixmap:
    """无封面时按名称生成稳定渐变色 + 音符图标。"""
    value = abs(hash(seed)) if seed else 0
    hue = value % 360
    start = QColor.fromHsv(hue, 90, 110)
    end = QColor.fromHsv((hue + 40) % 360, 120, 70)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, 7, 7)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, start)
    gradient.setColorAt(1, end)
    painter.fillPath(path, gradient)
    glyph = make_icon("music", "#ffffff", int(size * 0.5)).pixmap(int(size * 0.5), int(size * 0.5))
    painter.setOpacity(0.75)
    painter.drawPixmap(
        (size - int(size * 0.5)) // 2, (size - int(size * 0.5)) // 2, glyph
    )
    painter.end()
    return pixmap


def cover_pixmap(cover_path: str | None, seed: str, size: int = _COVER_SIZE) -> QPixmap:
    key = f"{cover_path or ''}|{seed}|{size}"
    cached = _COVER_CACHE.get(key)
    if cached is not None:
        return cached

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    source = QPixmap(cover_path) if cover_path and os.path.exists(cover_path) else None
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, 7, 7)
    painter.setClipPath(path)
    if source is not None and not source.isNull():
        scaled = source.scaled(
            size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        painter.drawPixmap(0, 0, scaled)
    else:
        painter.end()
        pixmap = _placeholder_pixmap(seed, size)
        _COVER_CACHE[key] = pixmap
        return pixmap
    painter.end()
    _COVER_CACHE[key] = pixmap
    return pixmap


class SongTableModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._songs: list[Song] = []
        self._accent = QColor(DEFAULT_ACCENT)
        self._playing_id: int | None = None
        self._sort_field: str | None = None
        self._sort_direction = "asc"

    def set_sort_state(self, field: str | None, direction: str = "asc") -> None:
        self._sort_field = field
        self._sort_direction = direction
        if self._songs:
            self.headerDataChanged.emit(Qt.Horizontal, 0, len(COLUMNS) - 1)

    # ------------------------------------------------------------------ 状态
    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        if self._songs:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._songs) - 1, len(COLUMNS) - 1)
            )

    def set_playing(self, song_id: int | None) -> None:
        if self._playing_id == song_id:
            return
        self._playing_id = song_id
        if self._songs:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._songs) - 1, len(COLUMNS) - 1)
            )

    def set_songs(self, songs: list[Song]) -> None:
        self.beginResetModel()
        self._songs = list(songs)
        self.endResetModel()

    def songs(self) -> list[Song]:
        return list(self._songs)

    def song_at(self, row: int) -> Song | None:
        if 0 <= row < len(self._songs):
            return self._songs[row]
        return None

    def update_favorite(self, song_id: int, favorite: bool) -> None:
        for row, song in enumerate(self._songs):
            if song.id == song_id and song.favorite != favorite:
                song.favorite = favorite
                index = self.index(row, 0)
                self.dataChanged.emit(index, index)
                return

    # ------------------------------------------------------------------ 模型
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            return COLUMNS[section].alignment
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        column = COLUMNS[section]
        label = column.label
        if column.key == self._sort_field:
            label += " ↑" if self._sort_direction == "asc" else " ↓"
        return label

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        song = self._songs[index.row()]
        column = COLUMNS[index.column()]
        is_playing = song.id == self._playing_id

        if role == Qt.DisplayRole:
            if column.key == "favorite":
                return "♥" if song.favorite else ""
            if column.key == "title":
                return song.title
            if column.key == "artist":
                return song.artist_text
            if column.key == "album":
                return song.album_text
            if column.key == "duration":
                return song.duration_text
            if column.key == "format":
                return song.format_text
            return None
        if role == Qt.DecorationRole and column.key == "title":
            return QIcon(cover_pixmap(song.cover_path, song.album or song.title))
        if role == Qt.TextAlignmentRole:
            return column.alignment
        if role == Qt.ForegroundRole:
            if column.key == "favorite" and song.favorite:
                return self._accent
            if column.key == "title" and is_playing:
                return self._accent
            if column.key in ("artist", "album", "duration", "format"):
                return QColor(TEXT_MUTED)
        if role == Qt.FontRole and column.key == "title":
            font = QFont()
            font.setBold(is_playing)
            return font
        if role == Qt.ToolTipRole:
            detail = [song.path]
            if song.bitrate:
                detail.append(f"{song.bitrate // 1000} kbps")
            if song.sample_rate:
                detail.append(f"{song.sample_rate} Hz")
            if song.play_count:
                detail.append(f"播放 {song.play_count} 次")
            return "\n".join(detail)
        return None


class SongTableView(QTableView):
    song_activated = pyqtSignal(object)  # Song
    song_context_menu = pyqtSignal(object, object)  # Song, QPoint(global)
    sort_requested = pyqtSignal(str, str)  # field, direction

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = SongTableModel(self)
        self._sort_field = ""
        self._sort_direction = "asc"
        self._accent = DEFAULT_ACCENT
        self._playing_id: int | None = None

        self.setModel(self._model)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setMouseTracking(True)
        self.setIconSize(QSize(_COVER_SIZE, _COVER_SIZE))
        self.setFrameShape(QTableView.NoFrame)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(50)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSortIndicatorShown(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setFixedHeight(38)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        for index, column in enumerate(COLUMNS):
            if column.key == "title":
                header.setSectionResizeMode(index, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(index, QHeaderView.Fixed)
                self.setColumnWidth(index, column.width)

        self.doubleClicked.connect(self._on_double_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu)
        header.sectionClicked.connect(self._on_header_clicked)

    # ------------------------------------------------------------------ 数据
    def set_songs(self, songs: list[Song]) -> None:
        self._model.set_songs(songs)
        if self._playing_id is not None:
            self._model.set_playing(self._playing_id)

    def songs(self) -> list[Song]:
        return self._model.songs()

    def song_at(self, row: int) -> Song | None:
        return self._model.song_at(row)

    def selected_song(self) -> Song | None:
        indexes = self.selectionModel().selectedRows() if self.selectionModel() else []
        if not indexes:
            return None
        return self._model.song_at(indexes[0].row())

    def current_row(self) -> int:
        song = self.selected_song()
        if song is None:
            return -1
        for index, item in enumerate(self._model.songs()):
            if item.id == song.id:
                return index
        return -1

    def select_song(self, song_id: int) -> None:
        for row, song in enumerate(self._model.songs()):
            if song.id == song_id:
                self.selectRow(row)
                return

    def set_accent(self, color: str) -> None:
        self._accent = color
        self._model.set_accent(color)

    def set_playing(self, song_id: int | None) -> None:
        self._playing_id = song_id
        self._model.set_playing(song_id)

    def update_favorite(self, song_id: int, favorite: bool) -> None:
        self._model.update_favorite(song_id, favorite)

    # ------------------------------------------------------------------ 排序
    def set_sort(self, field: str, direction: str = "asc") -> None:
        self._sort_field = field
        self._sort_direction = "desc" if direction == "desc" else "asc"
        self._model.set_sort_state(field, self._sort_direction)

    def _on_header_clicked(self, section: int) -> None:
        column = COLUMNS[section]
        field = SORT_FIELDS.get(column.key)
        if not column.sortable or field is None:
            return
        if field == self._sort_field:
            self._sort_direction = "desc" if self._sort_direction == "asc" else "asc"
        else:
            self._sort_field = field
            self._sort_direction = "asc"
        self.set_sort(field, self._sort_direction)
        self.sort_requested.emit(field, self._sort_direction)

    # ------------------------------------------------------------------ 事件
    def _on_double_clicked(self, index: QModelIndex) -> None:
        song = self._model.song_at(index.row())
        if song is not None:
            self.song_activated.emit(song)

    def _on_context_menu(self, position: QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return
        self.selectRow(index.row())
        song = self._model.song_at(index.row())
        if song is not None:
            self.song_context_menu.emit(song, self.viewport().mapToGlobal(position))

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            song = self.selected_song()
            if song is not None:
                self.song_activated.emit(song)
                return
        super().keyPressEvent(event)
