"""音乐库页：音乐来源（本地 + 远程占位）、浏览方式、曲库工具。"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QFrame,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...config import app_data_dir
from ...core.models import Source
from ..app_context import AppContext
from ..dialogs.remote_source_dialog import RemoteSourceDialog
from ..widgets.common import (
    Card,
    Divider,
    PageHeader,
    StatTile,
    clear_layout,
    human_size,
    muted_label,
    primary_button,
    section_title,
)


class LibraryPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._stat_tiles: dict[str, StatTile] = {}
        self._build_ui()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)

        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setAutoFillBackground(False)
        content.setObjectName("scrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(14)

        self.header = PageHeader("音乐库", "")
        layout.addWidget(self.header)

        # ---------------------------------------------------------- 音乐来源
        sources_card = Card()
        sources = sources_card.body()
        sources_header = QHBoxLayout()
        sources_header.addWidget(section_title("音乐来源"))
        sources_header.addStretch(1)
        self.add_folder_button = primary_button("添加本地文件夹")
        self.add_folder_button.clicked.connect(self._add_folder)
        sources_header.addWidget(self.add_folder_button)
        self.add_remote_button = QPushButton("添加远程库")
        self.add_remote_button.setToolTip(
            "添加 WebDAV 远程库：支持连接测试与密码加密保存；扫描/播放后续实现"
        )
        self.add_remote_button.clicked.connect(self._add_remote_source)
        sources_header.addWidget(self.add_remote_button)
        sources.addLayout(sources_header)

        self.sources_box = QVBoxLayout()
        self.sources_box.setSpacing(6)
        sources.addLayout(self.sources_box)

        sources.addWidget(
            muted_label(
                "远程库（WebDAV）：已支持连接测试与 DPAPI 加密保存密码；"
                "扫描、封面与播放待实现（见 docs/remote-library-interface.md）。"
            )
        )
        layout.addWidget(sources_card)

        # ---------------------------------------------------------- 浏览方式
        browse_card = Card()
        browse = browse_card.body()
        browse.addWidget(section_title("浏览方式"))
        self.browse_box = QHBoxLayout()
        self.browse_box.setSpacing(8)
        browse.addLayout(self.browse_box)
        browse.addWidget(muted_label("按来源浏览：点击下方来源，跳到「歌曲」页并只看该来源。"))
        layout.addWidget(browse_card)

        # --------------------------------------------------------------- 扫描
        scan_card = Card()
        scan = scan_card.body()
        scan.addWidget(section_title("扫描"))
        scan_row = QHBoxLayout()
        self.scan_button = primary_button("重新扫描全部")
        self.scan_button.clicked.connect(self._start_scan)
        scan_row.addWidget(self.scan_button)
        self.scan_status = muted_label("尚未扫描")
        scan_row.addWidget(self.scan_status, 1)
        scan.addLayout(scan_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        scan.addWidget(self.progress)
        layout.addWidget(scan_card)

        # ---------------------------------------------------------- 曲库工具
        tools_card = Card()
        tools = tools_card.body()
        tools.addWidget(section_title("曲库工具"))

        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(10)
        for key, label in (
            ("songs", "歌曲"),
            ("albums", "专辑"),
            ("artists", "艺术家"),
            ("duration", "总时长"),
            ("missing", "失效文件"),
        ):
            tile = StatTile(label)
            self._stat_tiles[key] = tile
            tiles_row.addWidget(tile)
        tools.addLayout(tiles_row)

        tools_buttons = QHBoxLayout()
        tools_buttons.setSpacing(8)
        integrity_button = QPushButton("检查失效文件")
        integrity_button.clicked.connect(self._check_integrity)
        prune_button = QPushButton("清理失效记录")
        prune_button.clicked.connect(self._prune_missing)
        cache_button = QPushButton("清理转码缓存")
        cache_button.clicked.connect(self._clear_cache)
        data_button = QPushButton("打开数据目录")
        data_button.clicked.connect(self._open_data_dir)
        for button in (integrity_button, prune_button, cache_button, data_button):
            tools_buttons.addWidget(button)
        tools_buttons.addStretch(1)
        tools.addLayout(tools_buttons)

        self.tools_status = muted_label("")
        tools.addWidget(self.tools_status)
        self.cache_label = muted_label("")
        tools.addWidget(self.cache_label)
        layout.addWidget(tools_card)

        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _connect(self) -> None:
        self._ctx.library_changed.connect(self.refresh)
        self._ctx.sources_changed.connect(self.refresh)
        library = self._ctx.library
        library.scan_state_changed.connect(self._on_scan_state)
        library.scan_progress.connect(self._on_scan_progress)
        library.scan_finished.connect(self._on_scan_finished)
        library.scan_failed.connect(self._on_scan_failed)

    # ------------------------------------------------------------------ 刷新
    def refresh(self) -> None:
        stats = self._ctx.library.stats()
        self._stat_tiles["songs"].set_value(str(stats.songs))
        self._stat_tiles["albums"].set_value(str(stats.albums))
        self._stat_tiles["artists"].set_value(str(stats.artists))
        self._stat_tiles["duration"].set_value(stats.duration_text)
        self._stat_tiles["missing"].set_value(str(stats.missing))
        self.header.set_subtitle(
            f"{stats.songs} 首歌曲 · {stats.albums} 张专辑 · {stats.sources} 个来源"
        )
        self._rebuild_sources()
        self._rebuild_browse()
        self._rebuild_cache_label()

    def _rebuild_sources(self) -> None:
        clear_layout(self.sources_box)
        sources = self._ctx.library.sources()
        adapters = self._ctx.library.adapters()
        if not sources:
            self.sources_box.addWidget(
                muted_label("还没有音乐来源。点击右上角「添加本地文件夹」开始。")
            )
            return
        for index, source in enumerate(sources):
            if index:
                self.sources_box.addWidget(Divider())
            self.sources_box.addWidget(self._source_row(source, adapters))

    def _source_row(self, source: Source, adapters: dict) -> QWidget:
        adapter = adapters.get(source.id)
        track_count = adapter.track_count() if adapter else 0
        available = adapter.available() if adapter else False

        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(2, 6, 2, 6)
        row_layout.setSpacing(10)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        name_label = QLabel(f"{source.name}  ·  {source.kind_text}")
        name_label.setStyleSheet("font-weight:600;")
        text_box.addWidget(name_label)
        if source.is_local:
            detail = source.path or ""
            if not available:
                detail = f"{detail}（目录不存在）"
            path_label = muted_label(detail)
            path_label.setToolTip(source.path or "")
            text_box.addWidget(path_label)
        else:
            target = muted_label(source.path or "未配置地址")
            target.setToolTip(source.path or "")
            text_box.addWidget(target)
            text_box.addWidget(muted_label("远程库：可测试连接，扫描/播放待实现"))
        row_layout.addLayout(text_box, 1)

        count_label = muted_label(f"{track_count} 首")
        row_layout.addWidget(count_label)

        browse_button = QPushButton("浏览")
        browse_button.setEnabled(source.enabled and track_count > 0)
        browse_button.clicked.connect(
            lambda _checked=False, sid=source.id: self._ctx.open_songs_requested.emit(sid)
        )
        row_layout.addWidget(browse_button)

        enable_checkbox = QCheckBox("启用")
        enable_checkbox.setChecked(source.enabled)
        enable_checkbox.toggled.connect(
            lambda checked, sid=source.id: self._ctx.library.set_source_enabled(sid, checked)
        )
        row_layout.addWidget(enable_checkbox)

        remove_button = QPushButton("移除")
        remove_button.clicked.connect(
            lambda _checked=False, src=source: self._remove_source(src)
        )
        row_layout.addWidget(remove_button)
        return row

    def _rebuild_browse(self) -> None:
        clear_layout(self.browse_box)
        all_button = QPushButton("全部歌曲")
        all_button.clicked.connect(
            lambda _checked=False: self._ctx.open_songs_requested.emit(None)
        )
        self.browse_box.addWidget(all_button)

        adapters = self._ctx.library.adapters()
        for source in self._ctx.library.enabled_sources():
            adapter = adapters.get(source.id)
            count = adapter.track_count() if adapter else 0
            button = QPushButton(f"{source.name}（{count}）")
            button.setEnabled(count > 0)
            button.clicked.connect(
                lambda _checked=False, sid=source.id: self._ctx.open_songs_requested.emit(sid)
            )
            self.browse_box.addWidget(button)
        self.browse_box.addStretch(1)

    def _rebuild_cache_label(self) -> None:
        cache = self._ctx.library.cache_status()
        self.cache_label.setText(
            f"缓存：转码 {human_size(cache['transcode_bytes'])} · "
            f"封面 {human_size(cache['cover_bytes'])}"
        )

    # ------------------------------------------------------------------ 来源
    def _add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if not path:
            return
        try:
            source = self._ctx.library.add_local_folder(path)
        except ValueError as error:
            QMessageBox.warning(self, "添加文件夹", str(error))
            return
        self._ctx.toast(f"已添加来源「{source.name}」，开始扫描…")
        self._ctx.library.start_scan([source.id])

    def _add_remote_source(self) -> None:
        dialog = RemoteSourceDialog(self._ctx, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh()

    def _remove_source(self, source: Source) -> None:
        answer = QMessageBox.question(
            self,
            "移除来源",
            f"移除来源「{source.name}」会同时删除它下面的曲目记录（不会删除音乐文件）。继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._ctx.library.remove_source(source.id)
        self._ctx.toast(f"已移除来源「{source.name}」")

    # ------------------------------------------------------------------ 扫描
    def _start_scan(self) -> None:
        if not self._ctx.library.start_scan():
            self._ctx.toast("没有可扫描的本地来源，请先添加文件夹")

    def _on_scan_state(self, scanning: bool) -> None:
        self.scan_button.setEnabled(not scanning)
        self.scan_button.setText("扫描中…" if scanning else "重新扫描全部")
        self.progress.setVisible(scanning)
        if scanning:
            self.progress.setRange(0, 0)

    def _on_scan_progress(self, done: int, total: int, current: str) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
        name = os.path.basename(current) if current else ""
        self.scan_status.setText(f"扫描中 {done}/{total}  {name}")

    def _on_scan_finished(self, stats: dict) -> None:
        self.scan_status.setText(
            f"扫描完成：新增 {stats.get('added', 0)}，更新 {stats.get('updated', 0)}，"
            f"移除 {stats.get('removed', 0)}，失败 {stats.get('failed', 0)}"
        )
        self._ctx.toast("扫描完成")
        self.refresh()

    def _on_scan_failed(self, message: str) -> None:
        self.scan_status.setText(f"扫描失败：{message}")
        self._ctx.toast(f"扫描失败：{message}")
        self.progress.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描全部")

    # ------------------------------------------------------------------ 工具
    def _check_integrity(self) -> None:
        result = self._ctx.library.check_integrity()
        self.tools_status.setText(
            f"检查完成：共 {result['checked']} 首，失效 {result['missing']} 首，"
            f"恢复 {result['restored']} 首"
        )
        self._ctx.toast("失效文件检查完成")

    def _prune_missing(self) -> None:
        answer = QMessageBox.question(
            self,
            "清理失效记录",
            "确定删除所有失效曲目的记录吗？（不会删除任何音乐文件）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        removed = self._ctx.library.prune_missing()
        self.tools_status.setText(f"已清理 {removed} 条失效记录")
        self._ctx.toast(f"已清理 {removed} 条失效记录")

    def _clear_cache(self) -> None:
        freed = self._ctx.library.clear_transcode_cache()
        self.tools_status.setText(f"已清理转码缓存 {human_size(freed)}")
        self._ctx.toast(f"已清理转码缓存 {human_size(freed)}")
        self._rebuild_cache_label()

    def _open_data_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(app_data_dir()))
