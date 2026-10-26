"""圆形头像控件：点击更换、右键菜单移除，带强调色头像框。"""

from __future__ import annotations

from PyQt5.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QMenu, QWidget

from ..icons import icon
from ..theme import BORDER, DEFAULT_ACCENT, SURFACE_2, TEXT_DIM, accent_soft


class AvatarButton(QWidget):
    clicked = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, size: int = 44, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._accent = DEFAULT_ACCENT
        self._pixmap: QPixmap | None = None
        self._hover = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击更换头像（右键可移除）")
        self.setAttribute(Qt.WA_Hover, True)

    # ------------------------------------------------------------------ 数据
    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self.update()

    def set_avatar(self, path: str | None) -> None:
        self._pixmap = self._load_square(path) if path else None
        self.setToolTip(
            "点击更换头像（右键可移除）" if self._pixmap is not None else "点击设置头像"
        )
        self.update()

    @property
    def has_avatar(self) -> bool:
        return self._pixmap is not None

    def _load_square(self, path: str) -> QPixmap | None:
        source = QPixmap(path)
        if source.isNull():
            return None
        side = min(source.width(), source.height())
        left = max(0, (source.width() - side) // 2)
        top = max(0, (source.height() - side) // 2)
        cropped = source.copy(left, top, side, side)
        return cropped.scaled(
            self._size * 2,
            self._size * 2,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

    # ------------------------------------------------------------------ 绘制
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        ring_width = max(1.5, self._size * 0.045)
        rect = QRectF(
            ring_width,
            ring_width,
            self.width() - ring_width * 2,
            self.height() - ring_width * 2,
        )
        inner = rect.adjusted(ring_width * 0.9, ring_width * 0.9, -ring_width * 0.9, -ring_width * 0.9)

        path = QPainterPath()
        path.addEllipse(inner)
        painter.save()
        painter.setClipPath(path)
        if self._pixmap is not None:
            painter.drawPixmap(inner.toRect(), self._pixmap)
        else:
            painter.fillRect(inner.toRect(), QColor(SURFACE_2))
            glyph = icon("user", TEXT_DIM, max(14, int(self._size * 0.42))).pixmap(
                max(14, int(self._size * 0.42)), max(14, int(self._size * 0.42))
            )
            target = inner.toRect()
            painter.drawPixmap(
                target.center().x() - glyph.width() // 2,
                target.center().y() - glyph.height() // 2,
                glyph,
            )
        if self._hover:
            painter.fillRect(inner.toRect(), QColor(accent_soft(self._accent, 0.5)))
            text_color = QColor(self._accent)
            painter.setPen(text_color)
        painter.restore()

        pen = QPen(
            QColor(self._accent if self._hover or self._pixmap is not None else BORDER),
            ring_width,
        )
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)
        painter.end()

    # ------------------------------------------------------------------ 事件
    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._show_menu(event.globalPos())

    def _show_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        change = menu.addAction("更换头像…")
        change.triggered.connect(lambda: self.clicked.emit())
        if self.has_avatar:
            menu.addSeparator()
            remove = menu.addAction("移除头像")
            remove.triggered.connect(lambda: self.remove_requested.emit())
        menu.exec_(position)
        menu.deleteLater()
