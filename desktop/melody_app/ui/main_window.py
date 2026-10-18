"""主窗口：侧边栏 + 歌曲表 + 播放条。"""

from __future__ import annotations

import os

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..core.db import Database, Song
from ..core.player import Player
from ..core.scanner import ScanWorker
from .song_table import SongTableModel
from .styles import APP_STYLESHEET


def _format_ms(ms: int) -> str:
    seconds = max(0, int(ms / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self._db = database
        self._player = Player()
        self._model = SongTableModel()
        self._current_index = -1
        self._current_folder_id: int | None = None
        self._scanner: ScanWorker | None = None
        self._scan_folders: list[tuple[int, str]] = []
        self._seeking = False

        self.setWindowTitle("Melody")
        self.resize(1180, 780)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_ui()
        self._connect_player()
        self.refresh_folders()
        self.refresh_songs()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.add_button = QPushButton("添加文件夹")
        self.add_button.clicked.connect(self.choose_folder)
        self.rescan_button = QPushButton("重新扫描")
        self.rescan_button.clicked.connect(self.rescan_all)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索标题、艺术家或专辑…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.rescan_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.search_edit, 1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧导航
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_title = QLabel("音乐库")
        left_title.setObjectName("mutedLabel")
        self.folder_list = QListWidget()
        self.folder_list.currentRowChanged.connect(self._on_folder_selected)
        self.remove_folder_button = QPushButton("移除所选文件夹")
        self.remove_folder_button.clicked.connect(self.remove_selected_folder)
        left_layout.addWidget(left_title)
        left_layout.addWidget(self.folder_list, 1)
        left_layout.addWidget(self.remove_folder_button)
        left.setMaximumWidth(260)
        splitter.addWidget(left)

        # 歌曲表
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._on_row_activated)
        splitter.addWidget(self.table)
        splitter.setSizes([220, 900])
        root.addWidget(splitter, 1)

        # 底部播放条
        player_bar = QHBoxLayout()
        player_bar.setSpacing(10)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setStyleSheet("background:#1b1e26;border-radius:6px;color:#5a6072;")
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("♪")
        player_bar.addWidget(self.cover_label)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.title_label = QLabel("未在播放")
        self.title_label.setObjectName("titleLabel")
        self.artist_label = QLabel("—")
        self.artist_label.setObjectName("mutedLabel")
        info.addWidget(self.title_label)
        info.addWidget(self.artist_label)
        player_bar.addLayout(info, 1)

        style = self.style()
        self.prev_button = QPushButton()
        self.prev_button.setObjectName("transport")
        self.prev_button.setIcon(style.standardIcon(self.style().SP_MediaSkipBackward))
        self.prev_button.setIconSize(QSize(18, 18))
        self.prev_button.setToolTip("上一首")
        self.prev_button.clicked.connect(self.play_previous)
        self.play_button = QPushButton()
        self.play_button.setObjectName("transportPrimary")
        self.play_button.setIcon(style.standardIcon(self.style().SP_MediaPlay))
        self.play_button.setIconSize(QSize(20, 20))
        self.play_button.setToolTip("播放 / 暂停")
        self.play_button.clicked.connect(self.toggle_play)
        self.next_button = QPushButton()
        self.next_button.setObjectName("transport")
        self.next_button.setIcon(style.standardIcon(self.style().SP_MediaSkipForward))
        self.next_button.setIconSize(QSize(18, 18))
        self.next_button.setToolTip("下一首")
        self.next_button.clicked.connect(self.play_next)
        player_bar.addWidget(self.prev_button)
        player_bar.addWidget(self.play_button)
        player_bar.addWidget(self.next_button)

        self.position_label = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.duration_label = QLabel("0:00")
        self.duration_label.setObjectName("mutedLabel")
        player_bar.addWidget(self.position_label)
        player_bar.addWidget(self.seek_slider, 2)
        player_bar.addWidget(self.duration_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self._player.volume)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.valueChanged.connect(self._player.set_volume)
        player_bar.addWidget(QLabel("音量"))
        player_bar.addWidget(self.volume_slider)

        root.addLayout(player_bar)
        self.setCentralWidget(central)
        self.statusBar().showMessage("就绪")

    # ---------------------------------------------------------------- 数据
    def refresh_folders(self) -> None:
        self.folder_list.blockSignals(True)
        self.folder_list.clear()
        self.folder_list.addItem(QListWidgetItem("全部歌曲"))
        for folder in self._db.list_folders():
            item = QListWidgetItem(f"{os.path.basename(folder['path'])}  ({folder['song_count']})")
            item.setData(Qt.UserRole, folder["id"])
            item.setToolTip(folder["path"])
            self.folder_list.addItem(item)
        self.folder_list.blockSignals(False)
        self.folder_list.setCurrentRow(0)

    def refresh_songs(self) -> None:
        songs = self._db.list_songs(self.search_edit.text(), self._current_folder_id)
        self._model.set_songs(songs)
        self.statusBar().showMessage(f"共 {len(songs)} 首")

    def _on_search_changed(self) -> None:
        QTimer.singleShot(200, self.refresh_songs)

    def _on_folder_selected(self, row: int) -> None:
        if row <= 0:
            self._current_folder_id = None
        else:
            item = self.folder_list.item(row)
            self._current_folder_id = item.data(Qt.UserRole) if item else None
        self.refresh_songs()

    # ---------------------------------------------------------------- 扫描
    def choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if directory:
            self.add_folder_and_scan(directory)

    def add_folder_and_scan(self, directory: str) -> None:
        folder_id = self._db.add_folder(directory)
        self._scan_folders = [(folder_id, directory)]
        self.refresh_folders()
        self._start_next_scan()

    def rescan_all(self) -> None:
        self._scan_folders = [
            (int(f["id"]), str(f["path"])) for f in self._db.list_folders()
        ]
        self._start_next_scan()

    def _start_next_scan(self) -> None:
        if not self._scan_folders:
            self.statusBar().showMessage("扫描完成")
            self.refresh_folders()
            self.refresh_songs()
            return
        folder_id, path = self._scan_folders.pop(0)
        self.statusBar().showMessage(f"正在扫描 {path} …")
        self._scanner = ScanWorker(self._db, folder_id, path)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.finished_scan.connect(self._on_scan_finished)
        self._scanner.failed.connect(self._on_scan_failed)
        self._scanner.start()

    def _on_scan_progress(self, done: int, total: int, current: str) -> None:
        self.statusBar().showMessage(f"扫描中 {done}/{total}  {os.path.basename(current)}")

    def _on_scan_finished(self, stats: dict) -> None:
        self.statusBar().showMessage(
            f"扫描完成：新增 {stats['added']}，更新 {stats['updated']}，"
            f"移除 {stats['removed']}，失败 {stats['failed']}"
        )
        self._start_next_scan()

    def _on_scan_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"扫描失败：{message}")
        self._start_next_scan()

    def remove_selected_folder(self) -> None:
        item = self.folder_list.currentItem()
        if item is None:
            return
        folder_id = item.data(Qt.UserRole)
        if folder_id is None:
            return
        self._db.remove_folder(int(folder_id))
        self._current_folder_id = None
        self.refresh_folders()
        self.refresh_songs()

    # ---------------------------------------------------------------- 播放
    def _connect_player(self) -> None:
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.state_changed.connect(self._on_player_state)
        self._player.error_occurred.connect(self._on_player_error)

    def _on_row_activated(self, index) -> None:
        self.play_index(index.row())

    def play_index(self, row: int) -> None:
        song = self._model.song_at(row)
        if song is None:
            return
        self._current_index = row
        self._load_song(song)
        self._player.play_path(song.path, autoplay=True)
        self.table.selectRow(row)

    def _load_song(self, song: Song) -> None:
        self.title_label.setText(song.title)
        self.artist_label.setText(
            " · ".join(part for part in [song.artist, song.album] if part) or "—"
        )
        if song.cover_path and os.path.exists(song.cover_path):
            pixmap = QPixmap(song.cover_path).scaled(
                56, 56, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(pixmap)
            self.cover_label.setText("")
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("♪")

    def toggle_play(self) -> None:
        if self._current_index < 0:
            if self._model.rowCount() > 0:
                self.play_index(0)
            return
        self._player.toggle()

    def play_next(self) -> None:
        if self._model.rowCount() == 0:
            return
        next_index = (self._current_index + 1) % self._model.rowCount()
        self.play_index(next_index)

    def play_previous(self) -> None:
        if self._model.rowCount() == 0:
            return
        previous_index = (self._current_index - 1) % self._model.rowCount()
        self.play_index(previous_index)

    def _on_position_changed(self, position: int) -> None:
        if not self._seeking:
            self.seek_slider.setValue(position)
        self.position_label.setText(_format_ms(position))

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, max(0, duration))
        self.duration_label.setText(_format_ms(duration))

    def _on_player_state(self, state: str) -> None:
        style = self.style()
        if state == "playing":
            self.play_button.setIcon(style.standardIcon(style.SP_MediaPause))
            song = self._model.song_at(self._current_index)
            if song is not None:
                self.statusBar().showMessage(f"正在播放：{song.title}")
        elif state in {"paused", "stopped"}:
            self.play_button.setIcon(style.standardIcon(style.SP_MediaPlay))
            self.statusBar().showMessage("已暂停" if state == "paused" else "就绪")
        elif state == "loading":
            self.play_button.setIcon(style.standardIcon(style.SP_MediaPlay))
            self.statusBar().showMessage("正在解码音频…")
        elif state == "error":
            self.play_button.setIcon(style.standardIcon(style.SP_MediaPlay))
        elif state == "ended":
            self.play_next()

    def _on_player_error(self, message: str) -> None:
        self.statusBar().showMessage(f"播放失败：{message}")

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self._player.seek(self.seek_slider.value())

    def closeEvent(self, event) -> None:  # noqa: N802
        self._player.stop()
        super().closeEvent(event)
