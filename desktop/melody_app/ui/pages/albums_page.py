"""专辑页：封面墙 + 专辑详情。"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Album, Song
from ..app_context import AppContext
from ..song_actions import show_song_context_menu
from ..widgets.common import Card, EmptyState, PageHeader, muted_label, primary_button
from ..widgets.cover import CoverLabel, cover_pixmap
from ..widgets.song_table import SongTableView


class AlbumsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._albums: list[Album] = []
        self._album: Album | None = None
        self._tracks: list[Song] = []

        self._build_ui()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # ---------------------------------------------------------- 封面墙
        grid_page = QWidget()
        grid_layout = QVBoxLayout(grid_page)
        grid_layout.setContentsMargins(20, 18, 20, 16)
        grid_layout.setSpacing(12)

        self.header = PageHeader("专辑", "")
        grid_layout.addWidget(self.header)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索专辑或艺术家…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(260)
        toolbar.addWidget(self.search_edit, 1)
        grid_layout.addLayout(toolbar)

        self.album_list = QListWidget()
        self.album_list.setViewMode(QListWidget.IconMode)
        self.album_list.setIconSize(QSize(150, 150))
        self.album_list.setGridSize(QSize(196, 246))
        self.album_list.setSpacing(8)
        self.album_list.setMovement(QListWidget.Static)
        self.album_list.setResizeMode(QListWidget.Adjust)
        self.album_list.setWordWrap(True)
        self.album_list.setUniformItemSizes(True)
        self.album_list.itemDoubleClicked.connect(self._open_album)
        self.album_empty = EmptyState(
            "还没有专辑", "扫描本地音乐后，带专辑标签的歌曲会自动归成专辑。"
        )
        self.grid_stack = QStackedWidget()
        self.grid_stack.addWidget(self.album_list)
        self.grid_stack.addWidget(self.album_empty)
        grid_layout.addWidget(self.grid_stack, 1)
        self.stack.addWidget(grid_page)

        # ------------------------------------------------------------ 详情
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(20, 18, 20, 16)
        detail_layout.setSpacing(12)

        back_row = QHBoxLayout()
        self.back_button = QPushButton("← 返回专辑")
        self.back_button.clicked.connect(self._go_back)
        back_row.addWidget(self.back_button)
        back_row.addStretch(1)
        detail_layout.addLayout(back_row)

        info_card = Card()
        info = info_card.body()
        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        self.detail_cover = CoverLabel(140)
        info_row.addWidget(self.detail_cover)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.detail_title = QLabel("")
        self.detail_title.setObjectName("albumTitle")
        self.detail_artist = QLabel("")
        self.detail_artist.setObjectName("pageSubtitle")
        self.detail_meta = muted_label("")
        text_box.addWidget(self.detail_title)
        text_box.addWidget(self.detail_artist)
        text_box.addWidget(self.detail_meta)
        text_box.addStretch(1)
        info_row.addLayout(text_box, 1)

        self.play_album_button = primary_button("播放整张专辑")
        self.play_album_button.clicked.connect(self._play_album)
        info_row.addWidget(self.play_album_button)
        info.addLayout(info_row)
        detail_layout.addWidget(info_card)

        self.track_table = SongTableView()
        detail_layout.addWidget(self.track_table, 1)
        self.stack.addWidget(detail_page)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)

    def _connect(self) -> None:
        self._search_timer.timeout.connect(self._reload_albums)
        self.search_edit.textChanged.connect(lambda _text: self._search_timer.start())
        self.track_table.song_activated.connect(self._play_track)
        self.track_table.song_context_menu.connect(self._on_context_menu)
        self._ctx.library_changed.connect(self.refresh)
        self._ctx.favorite_changed.connect(self.track_table.update_favorite)

    # ------------------------------------------------------------------ 刷新
    def refresh(self) -> None:
        self._reload_albums()
        if self._album is not None:
            self._load_detail(self._album)

    def _reload_albums(self) -> None:
        self._albums = self._ctx.albums.list(self.search_edit.text())
        self.album_list.clear()
        for album in self._albums:
            icon = QIcon(cover_pixmap(album.cover_path, 150, seed=album.name))
            item = QListWidgetItem(
                icon,
                f"{album.name}\n{album.artist_text} · {album.track_count} 首",
            )
            item.setToolTip(f"{album.name}\n{album.artist_text}\n{album.duration_text}")
            self.album_list.addItem(item)

        total = sum(album.track_count for album in self._albums)
        self.header.set_subtitle(f"共 {len(self._albums)} 张专辑 · {total} 首歌曲")
        if self._albums:
            self.grid_stack.setCurrentWidget(self.album_list)
        else:
            if self.search_edit.text().strip():
                self.album_empty.set_content(
                    "没有找到匹配的专辑", "换个关键词，或清空搜索条件。", icon="?"
                )
            else:
                self.album_empty.set_content(
                    "还没有专辑",
                    "扫描本地音乐后，带专辑标签的歌曲会自动归成专辑。",
                )
            self.grid_stack.setCurrentWidget(self.album_empty)

    # ------------------------------------------------------------------ 详情
    def _open_album(self, item: QListWidgetItem) -> None:
        row = self.album_list.row(item)
        if 0 <= row < len(self._albums):
            self._album = self._albums[row]
            self._load_detail(self._album)
            self.stack.setCurrentIndex(1)

    def _load_detail(self, album: Album) -> None:
        self.detail_cover.set_cover(album.cover_path, seed=album.name)
        self.detail_title.setText(album.name)
        self.detail_artist.setText(album.artist_text)
        meta_parts = [album.duration_text, f"{album.track_count} 首"]
        if album.year:
            meta_parts.insert(0, str(album.year))
        self.detail_meta.setText("  ·  ".join(meta_parts))

        self._tracks = self._ctx.albums.tracks(album.name, album.album_artist)
        self.track_table.set_songs(self._tracks)
        self.play_album_button.setEnabled(bool(self._tracks))

    def _go_back(self) -> None:
        self._album = None
        self.stack.setCurrentIndex(0)
        self._reload_albums()

    # ------------------------------------------------------------------ 播放
    def _play_album(self) -> None:
        if self._tracks:
            self._ctx.playback.play_songs(self._tracks, 0)

    def _play_track(self, song: Song) -> None:
        index = next((i for i, item in enumerate(self._tracks) if item.id == song.id), -1)
        if index >= 0:
            self._ctx.playback.play_songs(self._tracks, index)

    def _on_context_menu(self, song: Song, position) -> None:
        show_song_context_menu(self, self._ctx, song, position, on_play=self._play_track)
