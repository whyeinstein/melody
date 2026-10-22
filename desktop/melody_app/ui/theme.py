"""设计令牌与全局 QSS。

配色参考现代深色音乐类应用（近黑底 + 分层表面 + 单一强调色），
所有页面共用同一套颜色、圆角与字号，避免各页面各自写样式。
"""

from __future__ import annotations

import os

# ------------------------------------------------------------------ 颜色令牌
BG = "#0A0C11"          # 应用底色
SIDEBAR = "#0C0F15"     # 侧边栏
SURFACE = "#12161F"     # 卡片 / 播放条
SURFACE_2 = "#171C27"   # 输入框 / 悬浮层
SURFACE_3 = "#1C2230"   # hover
BORDER = "#212836"      # 常规描边
BORDER_SOFT = "#1A202B" # 弱描边

TEXT = "#E9EDF5"
TEXT_MUTED = "#98A2B5"
TEXT_DIM = "#667086"

DANGER = "#F87171"
SUCCESS = "#3DDC97"

ACCENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("靛蓝", "#7C6CF6"),
    ("天蓝", "#4C8DFF"),
    ("青碧", "#2DD4BF"),
    ("薄荷", "#3DDC97"),
    ("琥珀", "#F5B547"),
)

DEFAULT_ACCENT = ACCENT_CHOICES[0][1]

_UI_ASSET_DIR = os.path.join(os.environ.get("TEMP") or ".", "melody-ui-assets")


def _write_asset(name: str, svg: str) -> str:
    """把 QSS 需要的 SVG（勾选/箭头）写到临时目录，返回可被 url() 使用的路径。"""
    os.makedirs(_UI_ASSET_DIR, exist_ok=True)
    path = os.path.join(_UI_ASSET_DIR, name)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(svg)
    except OSError:
        pass
    return path.replace("\\", "/")


def _to_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, channel)) for channel in rgb)


def blend(color: str, base: str, ratio: float) -> str:
    """把 color 以 ratio 的比例混入 base（ratio=1 得到 color）。"""
    r1, g1, b1 = _to_rgb(color)
    r2, g2, b2 = _to_rgb(base)
    return _to_hex(
        (
            round(r1 * ratio + r2 * (1 - ratio)),
            round(g1 * ratio + g2 * (1 - ratio)),
            round(b1 * ratio + b2 * (1 - ratio)),
        )
    )


def accent_soft(accent: str, ratio: float = 0.18) -> str:
    return blend(accent, SURFACE, ratio)


def accent_hover(accent: str) -> str:
    return blend("#ffffff", accent, 0.14)


def build_stylesheet(accent: str = DEFAULT_ACCENT) -> str:
    soft = accent_soft(accent)
    soft_strong = accent_soft(accent, 0.34)
    hover = accent_hover(accent)
    check = _write_asset(
        "check.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m5 12.5 4.5 4.5L19 7"/></svg>',
    )
    arrow = _write_asset(
        "chevron-down.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{TEXT_MUTED}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
    )
    return f"""
* {{
  font-family: "Segoe UI Variable Text", "Microsoft YaHei UI", "Segoe UI", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  color: {TEXT};
  outline: none;
}}
QMainWindow, QWidget#appRoot, QWidget#contentArea {{ background: {BG}; }}
QStackedWidget {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#dim {{ color: {TEXT_DIM}; }}
QLabel#pageTitle {{ color: {TEXT}; font-size: 24px; font-weight: 600; }}
QLabel#pageSubtitle {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#sectionTitle {{ font-size: 13px; font-weight: 600; color: {TEXT}; }}
QLabel#statValue {{ font-size: 22px; font-weight: 600; }}
QLabel#statLabel {{ color: {TEXT_MUTED}; font-size: 11px; }}
QLabel#brandName {{ font-size: 16px; font-weight: 600; }}
QLabel#brandTag {{ color: {TEXT_DIM}; font-size: 11px; }}
QLabel#navSection {{ color: {TEXT_DIM}; font-size: 10px; font-weight: 600; padding-left: 10px; }}
QLabel#playerTitle {{ font-size: 13px; font-weight: 600; }}
QLabel#playerArtist {{ color: {TEXT_MUTED}; font-size: 11px; }}
QLabel#timeLabel {{ color: {TEXT_DIM}; font-size: 11px; }}
QLabel#emptyTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#emptyHint {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#nowTitle {{ font-size: 30px; font-weight: 600; }}
QLabel#nowArtist {{ font-size: 14px; color: {TEXT_MUTED}; }}
QLabel#albumTitle {{ font-size: 20px; font-weight: 600; }}

QFrame#sidebar {{
  background: {SIDEBAR};
  border-right: 1px solid {BORDER_SOFT};
}}
QFrame#card, QFrame#panel {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 14px;
}}
QFrame#statTile {{
  background: {SURFACE_2};
  border: 1px solid {BORDER_SOFT};
  border-radius: 12px;
}}
QFrame#playerBar {{
  background: {SURFACE};
  border-top: 1px solid {BORDER_SOFT};
}}
QFrame#divider {{ background: {BORDER_SOFT}; max-height: 1px; border: none; }}

QPushButton {{
  background: {SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: 9px;
  padding: 7px 14px;
  color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_3}; }}
QPushButton:pressed {{ background: {blend("#ffffff", SURFACE_3, 0.06)}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; background: {SURFACE}; border-color: {BORDER_SOFT}; }}
QPushButton:checked {{ background: {soft}; border-color: {accent}; color: {accent}; }}

QPushButton#primary {{
  background: {accent};
  border: 1px solid {accent};
  color: #ffffff;
  font-weight: 600;
}}
QPushButton#primary:hover {{ background: {hover}; border-color: {hover}; }}
QPushButton#ghost {{
  background: transparent;
  border: 1px solid {BORDER};
}}
QPushButton#ghost:hover {{ background: {SURFACE_2}; }}
QPushButton#chip {{
  background: transparent;
  border: 1px solid transparent;
  border-radius: 13px;
  padding: 5px 14px;
  color: {TEXT_MUTED};
}}
QPushButton#chip:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
QPushButton#chip:checked {{
  background: {soft};
  border-color: {soft_strong};
  color: {accent};
  font-weight: 600;
}}
QPushButton#iconButton {{
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 4px;
}}
QPushButton#iconButton:hover {{ background: {SURFACE_3}; }}
QPushButton#iconButton:checked {{ background: {soft}; }}
QPushButton#transport {{
  background: transparent;
  border: none;
  border-radius: 18px;
  min-width: 36px; min-height: 36px;
  padding: 0;
}}
QPushButton#transport:hover {{ background: {SURFACE_3}; }}
QPushButton#transportPrimary {{
  background: {accent};
  border: none;
  border-radius: 22px;
  min-width: 44px; min-height: 44px;
  padding: 0;
}}
QPushButton#transportPrimary:hover {{ background: {hover}; }}
QPushButton#navItem {{
  text-align: left;
  padding: 0 12px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: {TEXT_MUTED};
  font-size: 13px;
  min-height: 38px;
}}
QPushButton#navItem:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
QPushButton#navItem:checked {{
  background: {soft};
  color: {accent};
  font-weight: 600;
}}

QLineEdit, QComboBox, QSpinBox {{
  background: {SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 8px 12px;
  selection-background-color: {accent};
  selection-color: #ffffff;
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {blend("#ffffff", BORDER, 0.10)}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {accent}; }}
QComboBox {{ padding-right: 22px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{arrow}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
  background: {SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: 8px;
  padding: 4px;
  selection-background-color: {soft};
  selection-color: {accent};
  outline: none;
}}

QCheckBox {{ spacing: 8px; color: {TEXT_MUTED}; }}
QCheckBox::indicator {{
  width: 16px; height: 16px;
  border-radius: 5px;
  border: 1px solid {BORDER};
  background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: url("{check}"); }}

QTableView {{
  background: transparent;
  border: none;
  gridline-color: transparent;
  selection-background-color: transparent;
  selection-color: {TEXT};
  outline: none;
}}
QTableView::item {{ border: none; padding: 0 8px; }}
QTableView::item:hover {{ background: {SURFACE_2}; }}
QTableView::item:selected {{ background: {soft}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
  background: transparent;
  color: {TEXT_DIM};
  border: none;
  border-bottom: 1px solid {BORDER_SOFT};
  padding: 0 8px;
  height: 36px;
  font-size: 11px;
  font-weight: 600;
}}
QHeaderView::section:hover {{ color: {TEXT_MUTED}; }}
QTableCornerButton::section {{ background: transparent; border: none; }}

QListWidget, QTreeWidget {{
  background: transparent;
  border: none;
  outline: none;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: 8px; margin: 1px 0; }}
QListWidget::item:selected {{ background: {soft}; color: {accent}; }}
QListWidget::item:hover {{ background: {SURFACE_2}; }}

QSlider::groove:horizontal {{ height: 4px; background: {SURFACE_3}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{
  width: 11px; height: 11px; margin: -4px 0;
  border-radius: 5px; background: #ffffff;
}}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {blend("#ffffff", BORDER, 0.12)}; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ border: none; background: transparent; }}
QWidget#scrollContent {{ background: {BG}; }}

QToolTip {{
  background: {SURFACE_3};
  color: {TEXT};
  border: 1px solid {BORDER};
  border-radius: 6px;
  padding: 6px 8px;
}}
QMenu {{
  background: {SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 6px;
}}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {soft}; color: {accent}; }}
QMenu::separator {{ height: 1px; background: {BORDER_SOFT}; margin: 5px 8px; }}
QDialog, QMessageBox {{ background: {SURFACE}; }}
QStatusBar {{ background: {BG}; color: {TEXT_DIM}; }}
QProgressBar {{
  background: {SURFACE_2};
  border: 1px solid {BORDER};
  border-radius: 5px;
  text-align: center;
  color: {TEXT};
  font-size: 10px;
  max-height: 14px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
"""
