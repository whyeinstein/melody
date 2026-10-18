"""歌单页：歌单管理 + 歌单曲目。"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Playlist, Song
from ..app_context import AppContext
from ..song_actions import show_song_context_menu
from ..widgets.common import Card, EmptyState, PageHeader, format_total_duration, primary_button
from ..widgets.song_table import SongTableView


class PlaylistsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._playlist_id: int | None = None
        self._playlists: list[Playlist] = []

        self._build_ui()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 12)
        layout.setSpacing(12)

        self.header = PageHeader("歌单", "")
        layout.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(14)

        left_card = Card(spacing=10)
        left = left_card.body()
        left_title = QLabel("我的歌单")
        left_title.setObjectName("sectionTitle")
        left.addWidget(left_title)

        self.playlist_list = QListWidget()
        self.playlist_list.setMinimumWidth(220)
        self.playlist_list.setMaximumWidth(300)
        self.playlist_list.currentRowChanged.connect(self._on_playlist_selected)
        left.addWidget(self.playlist_list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.new_button = primary_button("新建")
        self.new_button.clicked.connect(self._create_playlist)
        self.rename_button = QPushButton("重命名")
        self.rename_button.clicked.connect(self._rename_playlist)
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self._delete_playlist)
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)
        left.addLayout(buttons)
        body.addWidget(left_card)

        right_card = Card(spacing=10)
        right = right_card.body()
        right_header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        self.playlist_title = QLabel("未选择歌单")
        self.playlist_title.setObjectName("albumTitle")
        self.playlist_subtitle = QLabel("")
        self.playlist_subtitle.setObjectName("pageSubtitle")
        header_text.addWidget(self.playlist_title)
        header_text.addWidget(self.playlist_subtitle)
        right_header.addLayout(header_text)
        right_header.addStretch(1)

        self.play_all_button = primary_button("播放全部")
        self.play_all_button.clicked.connect(self._play_all)
        self.move_up_button = QPushButton("上移")
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button = QPushButton("下移")
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.remove_button = QPushButton("移除所选")
        self.remove_button.clicked.connect(self._remove_selected)
        right_header.addWidget(self.play_all_button)
        right_header.addWidget(self.move_up_button)
        right_header.addWidget(self.move_down_button)
        right_header.addWidget(self.remove_button)
        right.addLayout(right_header)

        self.table = SongTableView()
        self.empty_state = EmptyState("还没有歌单", "点击左侧「新建」创建第一个歌单。")
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty_state)
        right.addWidget(self.stack, 1)
        body.addWidget(right_card, 1)

        layout.addLayout(body, 1)

    def _connect(self) -> None:
        self.table.song_activated.connect(self._play_song)
        self.table.song_context_menu.connect(self._on_context_menu)
        self._ctx.playlists_changed.connect(self.refresh)
        self._ctx.library_changed.connect(self._load_tracks)
        self._ctx.favorite_changed.connect(self.table.update_favorite)

    # ------------------------------------------------------------------ 刷新
    def refresh(self) -> None:
        previous = self._playlist_id
        self._playlists = self._ctx.playlists.list()
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        selected_row = 0
        for row, playlist in enumerate(self._playlists):
            item = QListWidgetItem(f"{playlist.name}  ({playlist.track_count})")
            item.setData(Qt.UserRole, playlist.id)
            self.playlist_list.addItem(item)
            if playlist.id == previous:
                selected_row = row
        if self._playlists:
            self.playlist_list.setCurrentRow(selected_row)
            self._playlist_id = self._playlists[selected_row].id
        else:
            self._playlist_id = None
        self.playlist_list.blockSignals(False)
        self._load_tracks()

    def _load_tracks(self) -> None:
        if self._playlist_id is None:
            self.playlist_title.setText("未选择歌单")
            self.playlist_subtitle.setText("")
            self.stack.setCurrentWidget(self.empty_state)
            self.empty_state.set_content("还没有歌单", "点击左侧「新建」创建第一个歌单。")
            self._set_track_actions_enabled(False)
            self.header.set_subtitle(f"共 {len(self._playlists)} 个歌单")
            return

        playlist = next(
            (item for item in self._playlists if item.id == self._playlist_id), None
        )
        tracks = self._ctx.playlists.tracks(self._playlist_id)
        self.table.set_songs(tracks)
        self.playlist_title.setText(playlist.name if playlist else "歌单")
        total = sum(song.duration_ms or 0 for song in tracks)
        self.playlist_subtitle.setText(
            f"{len(tracks)} 首 · {format_total_duration(total)}"
        )
        self.header.set_subtitle(f"共 {len(self._playlists)} 个歌单")
        self._set_track_actions_enabled(True)

        if tracks:
            self.stack.setCurrentWidget(self.table)
        else:
            self.empty_state.set_content(
                "歌单还是空的", "到「歌曲」页右键任意歌曲，选择「添加到歌单」。"
            )
            self.stack.setCurrentWidget(self.empty_state)

    def _set_track_actions_enabled(self, enabled: bool) -> None:
        for button in (
            self.play_all_button,
            self.move_up_button,
            self.move_down_button,
            self.remove_button,
        ):
            button.setEnabled(enabled and self._playlist_id is not None)
        self.rename_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    # ------------------------------------------------------------------ 歌单操作
    def _on_playlist_selected(self, row: int) -> None:
        if 0 <= row < len(self._playlists):
            self._playlist_id = self._playlists[row].id
        else:
            self._playlist_id = None
        self._load_tracks()

    def _create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "新建歌单", "歌单名称：")
        if not ok or not name.strip():
            return
        if self._ctx.playlists.exists(name):
            QMessageBox.warning(self, "新建歌单", "已存在同名歌单。")
            return
        try:
            playlist = self._ctx.playlists.create(name)
        except ValueError as error:
            QMessageBox.warning(self, "新建歌单", str(error))
            return
        self._playlist_id = playlist.id
        self._ctx.playlists_changed.emit()
        self._ctx.toast(f"已创建歌单「{playlist.name}」")

    def _rename_playlist(self) -> None:
        playlist = self._current_playlist()
        if playlist is None:
            return
        name, ok = QInputDialog.getText(self, "重命名歌单", "歌单名称：", text=playlist.name)
        if not ok or not name.strip() or name.strip() == playlist.name:
            return
        if self._ctx.playlists.exists(name):
            QMessageBox.warning(self, "重命名歌单", "已存在同名歌单。")
            return
        self._ctx.playlists.rename(playlist.id, name)
        self._ctx.playlists_changed.emit()

    def _delete_playlist(self) -> None:
        playlist = self._current_playlist()
        if playlist is None:
            return
        answer = QMessageBox.question(
            self,
            "删除歌单",
            f"确定删除歌单「{playlist.name}」吗？（只删除歌单，不会删除音乐文件）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._ctx.playlists.delete(playlist.id)
        self._playlist_id = None
        self._ctx.playlists_changed.emit()
        self._ctx.toast(f"已删除歌单「{playlist.name}」")

    def _current_playlist(self) -> Playlist | None:
        return next(
            (item for item in self._playlists if item.id == self._playlist_id), None
        )

    # ------------------------------------------------------------------ 曲目
    def _play_all(self) -> None:
        tracks = self.table.songs()
        if tracks:
            self._ctx.playback.play_songs(tracks, 0)

    def _play_song(self, song: Song) -> None:
        tracks = self.table.songs()
        index = next((i for i, item in enumerate(tracks) if item.id == song.id), -1)
        if index >= 0:
            self._ctx.playback.play_songs(tracks, index)

    def _on_context_menu(self, song: Song, position) -> None:
        show_song_context_menu(self, self._ctx, song, position, on_play=self._play_song)

    def _remove_selected(self) -> None:
        if self._playlist_id is None:
            return
        song = self.table.selected_song()
        if song is None:
            self._ctx.toast("请先选中一首歌曲")
            return
        self._ctx.playlists.remove_song(self._playlist_id, song.id)
        self._ctx.playlists_changed.emit()

    def _move_selected(self, delta: int) -> None:
        if self._playlist_id is None:
            return
        song = self.table.selected_song()
        if song is None:
            self._ctx.toast("请先选中一首歌曲")
            return
        if self._ctx.playlists.move_song(self._playlist_id, song.id, delta):
            self._ctx.playlists_changed.emit()
