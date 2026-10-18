"""封面加载与占位图：带内存缓存，避免滚动封面墙时反复读盘。"""

from __future__ import annotations

import os

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QLabel

_COVER_CACHE: dict[tuple[str, int], QPixmap] = {}
_PLACEHOLDER_CACHE: dict[tuple[str, int], QPixmap] = {}


def _hue(seed: str) -> int:
    if not seed:
        return 262  # 默认紫色系
    return sum(ord(ch) * (index + 7) for index, ch in enumerate(seed)) % 360


def placeholder_pixmap(size: int, seed: str = "") -> QPixmap:
    key = (seed, size)
    cached = _PLACEHOLDER_CACHE.get(key)
    if cached is not None:
        return cached

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    hue = _hue(seed)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor.fromHsv(hue, 90, 78))
    gradient.setColorAt(1.0, QColor.fromHsv((hue + 42) % 360, 120, 44))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient)
    radius = max(6, int(size * 0.1))
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.setPen(QColor(255, 255, 255, int(255 * 0.55)))
    font = QFont("Microsoft YaHei")
    font.setPixelSize(max(10, int(size * 0.36)))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, "♪")
    painter.end()
    _PLACEHOLDER_CACHE[key] = pixmap
    return pixmap


def _rounded(pixmap: QPixmap, size: int) -> QPixmap:
    scaled = pixmap.scaled(
        size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    radius = max(4, int(size * 0.08))
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


def cover_pixmap(cover_path: str | None, size: int, seed: str = "") -> QPixmap:
    key = (cover_path or "", size)
    cached = _COVER_CACHE.get(key)
    if cached is not None:
        return cached
    if cover_path and os.path.exists(cover_path):
        source = QPixmap(cover_path)
        if not source.isNull():
            result = _rounded(source, size)
            _COVER_CACHE[key] = result
            return result
    return placeholder_pixmap(size, seed)


def clear_cover_cache() -> None:
    _COVER_CACHE.clear()
    _PLACEHOLDER_CACHE.clear()


class CoverLabel(QLabel):
    """固定尺寸的圆角封面。"""

    def __init__(self, size: int = 48, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setScaledContents(False)

    def set_cover(self, cover_path: str | None, seed: str = "") -> None:
        self.setPixmap(cover_pixmap(cover_path, self._size, seed or (cover_path or "")))
