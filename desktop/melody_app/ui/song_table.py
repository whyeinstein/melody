"""歌曲表格模型。"""

from __future__ import annotations

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QFont

from ..core.db import Song


class SongTableModel(QAbstractTableModel):
    HEADERS = ["标题", "艺术家", "专辑", "时长", "格式"]

    def __init__(self) -> None:
        super().__init__()
        self._songs: list[Song] = []

    def set_songs(self, songs: list[Song]) -> None:
        self.beginResetModel()
        self._songs = songs
        self.endResetModel()

    def songs(self) -> list[Song]:
        return self._songs

    def song_at(self, row: int) -> Song | None:
        if 0 <= row < len(self._songs):
            return self._songs[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._songs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section + 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        song = self._songs[index.row()]
        column = index.column()
        if role == Qt.DisplayRole:
            if column == 0:
                return song.title
            if column == 1:
                return song.artist or "未知艺术家"
            if column == 2:
                return song.album or "未知专辑"
            if column == 3:
                return song.duration_text
            if column == 4:
                return (song.format or "").upper()
        if role == Qt.FontRole and column == 0:
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.TextAlignmentRole and column == 3:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            return song.path
        return None
