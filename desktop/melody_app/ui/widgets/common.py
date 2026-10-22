"""通用界面组件：卡片、页头、空状态、统计块与少量格式化工具。"""

from __future__ import annotations

import os
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def format_ms(ms: int) -> str:
    seconds = max(0, int(ms / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_total_duration(ms: int) -> str:
    seconds = max(0, int(ms / 1000))
    if seconds < 60:
        return f"{seconds} 秒"
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours} 小时 {minutes} 分"
    return f"{minutes} 分"


def human_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def reveal_in_explorer(path: str) -> None:
    """在 Windows 资源管理器中定位文件；失败时静默忽略。"""
    try:
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except OSError:
        pass


class Card(QFrame):
    def __init__(self, parent=None, spacing: int = 12, margins: tuple[int, int, int, int] = (16, 16, 16, 16)) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    def body(self) -> QVBoxLayout:
        return self._layout


class Divider(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


class PageHeader(QWidget):
    """页面标题 + 副标题 + 右侧操作区。"""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.subtitle_label)
        layout.addLayout(text_box)
        layout.addStretch(1)
        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)
        layout.addLayout(self._actions)

    def add_action(self, widget: QWidget) -> None:
        self._actions.addWidget(widget)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)


class EmptyState(QWidget):
    _ICON_MAP = {"♪": "music", "♥": "heart", "⏱": "info", "?": "search", "♫": "disc"}

    def __init__(self, title: str, hint: str = "", icon: str = "♪", parent=None) -> None:
        super().__init__(parent)
        from ..icons import icon as make_icon
        from ..theme import DEFAULT_ACCENT, TEXT_DIM, accent_soft

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        layout.setContentsMargins(32, 32, 32, 32)

        self._icon_wrap = QLabel()
        self._icon_wrap.setFixedSize(76, 76)
        self._icon_wrap.setAlignment(Qt.AlignCenter)
        self._icon_wrap.setStyleSheet(
            f"background: {accent_soft(DEFAULT_ACCENT, 0.16)};"
            f"border-radius: 38px;"
        )
        self._icon_wrap.setPixmap(
            make_icon(self._ICON_MAP.get(icon, "music"), DEFAULT_ACCENT, 30).pixmap(30, 30)
        )
        self._title_label = QLabel(title)
        self._title_label.setObjectName("emptyTitle")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._hint_label = QLabel(hint)
        self._hint_label.setObjectName("emptyHint")
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._hint_label.setWordWrap(True)
        self._hint_label.setMaximumWidth(420)
        layout.addWidget(self._icon_wrap, 0, Qt.AlignHCenter)
        layout.addWidget(self._title_label)
        layout.addWidget(self._hint_label, 0, Qt.AlignHCenter)

    def set_content(self, title: str, hint: str = "", icon: str | None = None) -> None:
        from ..icons import icon as make_icon
        from ..theme import DEFAULT_ACCENT

        self._title_label.setText(title)
        self._hint_label.setText(hint)
        if icon is not None:
            self._icon_wrap.setPixmap(
                make_icon(self._ICON_MAP.get(icon, "music"), DEFAULT_ACCENT, 30).pixmap(30, 30)
            )


class StatTile(QFrame):
    def __init__(self, label: str, value: str = "—", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        name_label = QLabel(label)
        name_label.setObjectName("statLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(name_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


def primary_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("primary")
    button.setCursor(Qt.PointingHandCursor)
    return button


def muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    return label


def clear_layout(layout) -> None:
    """递归清空布局（用于动态重建来源列表、浏览按钮等）。"""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child is not None:
            clear_layout(child)
