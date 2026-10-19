"""设置页：播放默认值、外观、音乐库工具入口、远程库占位与数据信息。"""

from __future__ import annotations

import sys

from PyQt5.QtCore import QUrl, QT_VERSION_STR
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt

from ...config import APP_VERSION, app_data_dir
from ...core.library import ffprobe
from ...core.playback.queue import RepeatMode
from ...core.repositories.settings import KEY_RESTORE_SESSION
from ..app_context import AppContext
from ..theme import ACCENT_CHOICES
from ..widgets.common import (
    Card,
    Divider,
    PageHeader,
    human_size,
    muted_label,
    section_title,
)
from ..widgets.cover import clear_cover_cache

REPEAT_CHOICES = (
    ("顺序播放", RepeatMode.OFF.value),
    ("列表循环", RepeatMode.ALL.value),
    ("单曲循环", RepeatMode.ONE.value),
)


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._build_ui()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        self.header = PageHeader("设置", "播放、外观、音乐库与数据")
        layout.addWidget(self.header)

        layout.addWidget(self._build_playback_card())
        layout.addWidget(self._build_appearance_card())
        layout.addWidget(self._build_library_card())
        layout.addWidget(self._build_remote_card())
        layout.addWidget(self._build_data_card())
        layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_playback_card(self) -> Card:
        card = Card()
        body = card.body()
        body.addWidget(section_title("播放"))

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("默认音量"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(220)
        volume_row.addWidget(self.volume_slider)
        self.volume_value = muted_label("80")
        self.volume_value.setFixedWidth(36)
        volume_row.addWidget(self.volume_value)
        volume_row.addStretch(1)
        body.addLayout(volume_row)

        body.addWidget(Divider())

        self.restore_checkbox = QCheckBox("启动时恢复上次播放的歌曲与进度")
        body.addWidget(self.restore_checkbox)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("默认播放模式"))
        self.repeat_combo = QComboBox()
        for label, value in REPEAT_CHOICES:
            self.repeat_combo.addItem(label, value)
        mode_row.addWidget(self.repeat_combo)
        mode_row.addStretch(1)
        body.addLayout(mode_row)

        self.shuffle_checkbox = QCheckBox("默认随机播放")
        body.addWidget(self.shuffle_checkbox)
        return card

    def _build_appearance_card(self) -> Card:
        card = Card()
        body = card.body()
        body.addWidget(section_title("外观"))
        row = QHBoxLayout()
        row.addWidget(QLabel("强调色"))
        self.accent_combo = QComboBox()
        for name, color in ACCENT_CHOICES:
            self.accent_combo.addItem(name, color)
        row.addWidget(self.accent_combo)
        row.addStretch(1)
        body.addLayout(row)
        body.addWidget(muted_label("修改后立即生效，并记录在设置中。"))
        return card

    def _build_library_card(self) -> Card:
        card = Card()
        body = card.body()
        body.addWidget(section_title("音乐库"))
        self.ffprobe_label = muted_label("")
        self.ffmpeg_label = muted_label("")
        body.addWidget(self.ffprobe_label)
        body.addWidget(self.ffmpeg_label)
        body.addWidget(muted_label("扫描使用 4 个并发线程解析标签；扫描工具在「音乐库」页。"))
        return card

    def _build_remote_card(self) -> Card:
        card = Card()
        body = card.body()
        body.addWidget(section_title("远程库"))
        body.addWidget(
            muted_label(
                "远程音乐库当前只预留了接口（core/sources/webdav.py、docs/remote-library-interface.md），"
                "尚未实现连接、扫描与播放；后续按 WebDAV 优先接入，全程保持纯本地、不引入在线服务。"
            )
        )
        return card

    def _build_data_card(self) -> Card:
        card = Card()
        body = card.body()
        body.addWidget(section_title("数据"))
        self.stats_label = muted_label("")
        self.cache_label = muted_label("")
        self.version_label = muted_label("")
        body.addWidget(self.stats_label)
        body.addWidget(self.cache_label)

        buttons = QHBoxLayout()
        data_button = _button("打开数据目录", self._open_data_dir)
        transcode_button = _button("清理转码缓存", self._clear_transcode)
        cover_button = _button("清理封面缓存", self._clear_covers)
        for widget in (data_button, transcode_button, cover_button):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        body.addLayout(buttons)
        body.addWidget(self.version_label)
        return card

    def _connect(self) -> None:
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.restore_checkbox.toggled.connect(
            lambda checked: self._ctx.settings.set(KEY_RESTORE_SESSION, bool(checked))
        )
        self.repeat_combo.currentIndexChanged.connect(self._on_repeat_changed)
        self.shuffle_checkbox.toggled.connect(self._on_shuffle_changed)
        self.accent_combo.currentIndexChanged.connect(self._on_accent_changed)
        self._ctx.playback.mode_changed.connect(self._sync_playback_modes)
        self._ctx.playback.volume_changed.connect(self._sync_volume)

    # ------------------------------------------------------------------ 刷新
    def refresh(self) -> None:
        settings = self._ctx.settings
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(self._ctx.playback.volume)
        self.volume_slider.blockSignals(False)
        self.volume_value.setText(str(self._ctx.playback.volume))
        self.restore_checkbox.blockSignals(True)
        self.restore_checkbox.setChecked(settings.get_bool(KEY_RESTORE_SESSION, True))
        self.restore_checkbox.blockSignals(False)
        self._sync_playback_modes()
        self._sync_accent()
        self._sync_library_tools()
        self._sync_data()

    def _sync_playback_modes(self) -> None:
        playback = self._ctx.playback
        self.repeat_combo.blockSignals(True)
        index = self.repeat_combo.findData(playback.repeat.value)
        self.repeat_combo.setCurrentIndex(index if index >= 0 else 0)
        self.repeat_combo.blockSignals(False)
        self.shuffle_checkbox.blockSignals(True)
        self.shuffle_checkbox.setChecked(playback.shuffle)
        self.shuffle_checkbox.blockSignals(False)

    def _sync_volume(self, volume: int) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)
        self.volume_value.setText(str(volume))

    def _sync_accent(self) -> None:
        self.accent_combo.blockSignals(True)
        index = self.accent_combo.findData(self._ctx.settings.accent)
        self.accent_combo.setCurrentIndex(index if index >= 0 else 0)
        self.accent_combo.blockSignals(False)

    def _sync_library_tools(self) -> None:
        status = ffprobe.tool_status()
        probe_path = status["ffprobe"]
        ffmpeg_path = status["ffmpeg"]
        self.ffprobe_label.setText(
            f"ffprobe（{ffprobe.tool_source(probe_path)}）："
            f"{probe_path or '未找到（标签解析不可用）'}"
        )
        self.ffmpeg_label.setText(
            f"ffmpeg（{ffprobe.tool_source(ffmpeg_path)}）："
            f"{ffmpeg_path or '未找到（封面与转码不可用）'}"
        )

    def _sync_data(self) -> None:
        stats = self._ctx.library.stats()
        self.stats_label.setText(
            f"曲库：{stats.songs} 首歌曲 · {stats.albums} 张专辑 · "
            f"{stats.artists} 位艺术家 · 总时长 {stats.duration_text}"
        )
        cache = self._ctx.library.cache_status()
        self.cache_label.setText(
            f"缓存：转码 {human_size(cache['transcode_bytes'])} · "
            f"封面 {human_size(cache['cover_bytes'])} · 数据目录 {app_data_dir()}"
        )
        self.version_label.setText(
            f"Melody {APP_VERSION} · Python {sys.version.split()[0]} · Qt {QT_VERSION_STR}"
        )

    # ------------------------------------------------------------------ 动作
    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(str(value))
        self._ctx.playback.set_volume(value)

    def _on_repeat_changed(self) -> None:
        value = self.repeat_combo.currentData() or RepeatMode.OFF.value
        self._ctx.playback.set_repeat(RepeatMode.from_value(value))

    def _on_shuffle_changed(self, checked: bool) -> None:
        self._ctx.playback.set_shuffle(bool(checked))

    def _on_accent_changed(self) -> None:
        color = self.accent_combo.currentData()
        if not color:
            return
        self._ctx.settings.accent = color
        self._ctx.theme_changed.emit()
        self._ctx.toast("强调色已更新")

    def _open_data_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(app_data_dir()))

    def _clear_transcode(self) -> None:
        freed = self._ctx.library.clear_transcode_cache()
        self._ctx.toast(f"已清理转码缓存 {human_size(freed)}")
        self._sync_data()

    def _clear_covers(self) -> None:
        answer = QMessageBox.question(
            self,
            "清理封面缓存",
            "将删除所有已缓存的封面图片（下次播放时按需重新提取），继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        freed = self._ctx.library.clear_cover_cache()
        clear_cover_cache()
        self._ctx.toast(f"已清理封面缓存 {human_size(freed)}")
        self._sync_data()


def _button(text: str, handler) -> QWidget:
    from PyQt5.QtWidgets import QPushButton

    button = QPushButton(text)
    button.clicked.connect(handler)
    return button
