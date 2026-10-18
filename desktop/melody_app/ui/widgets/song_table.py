"""歌曲表：模型 + 视图（列头排序、双击播放、右键菜单）。"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from ...core.models import Song
from ..theme import DEFAULT_ACCENT


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    width: int = 100
    alignment: int = int(Qt.AlignLeft | Qt.AlignVCenter)
    sortable: bool = True


COLUMNS: tuple[Column, ...] = (
    Column("favorite", "♥", 34, int(Qt.AlignCenter), False),
    Column("title", "标题", 260),
    Column("artist", "艺术家", 170),
    Column("album", "专辑", 190),
    Column("duration", "时长", 64, int(Qt.AlignRight | Qt.AlignVCenter)),
    Column("format", "格式", 58, int(Qt.AlignCenter)),
)

SORT_FIELDS = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "duration": "duration",
    "format": "format",
}


class SongTableModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._songs: list[Song] = []
        self._accent = QColor(DEFAULT_ACCENT)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        if self._songs:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._songs) - 1, 0)
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

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return COLUMNS[section].label

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        song = self._songs[index.row()]
        column = COLUMNS[index.column()]

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
        if role == Qt.TextAlignmentRole:
            return column.alignment
        if role == Qt.ForegroundRole and column.key == "favorite" and song.favorite:
            return self._accent
        if role == Qt.FontRole and column.key == "title":
            font = QFont()
            font.setBold(True)
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

        self.setModel(self._model)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(32)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        header = self.horizontalHeader()
        for index, column in enumerate(COLUMNS):
            if column.key == "title":
                header.setSectionResizeMode(index, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(index, QHeaderView.Fixed)
                self.setColumnWidth(index, column.width)

        self.doubleClicked.connect(self._on_double_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

    # ------------------------------------------------------------------ 数据
    def set_songs(self, songs: list[Song]) -> None:
        self._model.set_songs(songs)

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
        self._model.set_accent(color)

    def update_favorite(self, song_id: int, favorite: bool) -> None:
        self._model.update_favorite(song_id, favorite)

    # ------------------------------------------------------------------ 排序
    def set_sort(self, field: str, direction: str = "asc") -> None:
        self._sort_field = field
        self._sort_direction = "desc" if direction == "desc" else "asc"
        for index, column in enumerate(COLUMNS):
            if column.key == field:
                order = Qt.DescendingOrder if self._sort_direction == "desc" else Qt.AscendingOrder
                self.horizontalHeader().setSortIndicator(index, order)
                return

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
