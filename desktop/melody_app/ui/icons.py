"""线性图标（Lucide 风格 SVG，内置无需额外依赖）。

所有图标统一 24x24 视框、圆角端点、1.7 描边，可按颜色/尺寸生成 QIcon。
"""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

# 只保留用到的图标，路径来自 Lucide（ISC 许可）的 24x24 线性图标。
_PATHS: dict[str, str] = {
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "disc": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>',
    "list": '<path d="M3 6h11M3 12h11M3 18h7"/><circle cx="18" cy="7" r="2"/><circle cx="18" cy="15" r="2"/><path d="M20 9v6"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "play": '<path d="M7 4.5v15l13-7.5z"/>',
    "pause": '<rect x="6.5" y="4.5" width="3.5" height="15" rx="1.2"/><rect x="14" y="4.5" width="3.5" height="15" rx="1.2"/>',
    "prev": '<path d="M18.5 5v14L8 12z"/><path d="M5 5v14"/>',
    "next": '<path d="M5.5 5v14L16 12z"/><path d="M19 5v14"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    "heart": '<path d="M12 20s-7.5-4.6-7.5-9.3A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 3.7C19.5 15.4 12 20 12 20z"/>',
    "volume": '<path d="M4 9.5h3l4.5-4v13L7 14.5H4z"/><path d="M16 8.5a5 5 0 0 1 0 7"/><path d="M18.8 6a8.5 8.5 0 0 1 0 12"/>',
    "volume-mute": '<path d="M4 9.5h3l4.5-4v13L7 14.5H4z"/><path d="m16 9 5 5M21 9l-5 5"/>',
    "queue": '<path d="M4 6h10M4 12h10M4 18h6"/><path d="M16 15.5v-7l5-1.2v7"/><circle cx="14.5" cy="16.5" r="1.8"/><circle cx="19.5" cy="15.5" r="1.8"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9v.09a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1z"/>',
    "shuffle": '<path d="M16 4h4v4"/><path d="m20 4-6.5 6.5"/><path d="M4 20l6.5-6.5"/><path d="M16 20h4v-4"/><path d="m20 20-4.5-4.5M4 4l4.5 4.5"/>',
    "repeat": '<path d="M17 3.5 20.5 7 17 10.5"/><path d="M20.5 7H7a3.5 3.5 0 0 0-3.5 3.5V12"/><path d="M7 20.5 3.5 17 7 13.5"/><path d="M3.5 17H17a3.5 3.5 0 0 0 3.5-3.5V12"/>',
    "repeat-one": '<path d="M17 3.5 20.5 7 17 10.5"/><path d="M20.5 7H7a3.5 3.5 0 0 0-3.5 3.5V12"/><path d="M7 20.5 3.5 17 7 13.5"/><path d="M3.5 17H17a3.5 3.5 0 0 0 3.5-3.5V12"/><path d="M11 9.5h1.5v5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.6"/><path d="M20 4.5V11h-6.5"/>',
    "trash": '<path d="M4 7h16M9 7V5h6v2M6.5 7l1 12.5h9L17.5 7"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "album": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.8v.4"/>',
    "more": '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
}

_cache: dict[tuple[str, str, int], QIcon] = {}


def icon(name: str, color: str = "#E9EDF5", size: int = 20) -> QIcon:
    """返回指定颜色与逻辑尺寸的 QIcon（内部按 2x 渲染，适配高 DPI）。"""
    key = (name, color.lower(), size)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    path = _PATHS.get(name)
    if path is None:
        return QIcon()

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        f"{path}</svg>"
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scale = 2
    pixmap = QPixmap(QSize(size * scale, size * scale))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    result = QIcon(pixmap)
    _cache[key] = result
    return result


def svg_pixmap(name: str, color: str, size: int) -> QPixmap:
    """需要直接绘制到 QLabel 时使用。"""
    return icon(name, color, size).pixmap(QSize(size, size))


def accent_pixmap(name: str, color: str, size: int) -> QPixmap:
    return svg_pixmap(name, color, size)
