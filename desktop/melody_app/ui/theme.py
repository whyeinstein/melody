"""深色主题与 QSS 生成（强调色可配置）。"""

from __future__ import annotations

BORDER = "#2a2e3a"

ACCENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("紫", "#6c5ce7"),
    ("蓝", "#4c8dff"),
    ("青", "#14b8a6"),
    ("绿", "#22c55e"),
    ("橙", "#f59e0b"),
)

DEFAULT_ACCENT = ACCENT_CHOICES[0][1]


def _to_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def blend(color: str, base: str, ratio: float) -> str:
    """把 color 以 ratio 的比例混入 base。"""
    r1, g1, b1 = _to_rgb(color)
    r2, g2, b2 = _to_rgb(base)
    return _to_hex(
        (
            round(r1 * ratio + r2 * (1 - ratio)),
            round(g1 * ratio + g2 * (1 - ratio)),
            round(b1 * ratio + b2 * (1 - ratio)),
        )
    )


def accent_soft(accent: str) -> str:
    return blend(accent, "#1b1e26", 0.28)


def build_stylesheet(accent: str = DEFAULT_ACCENT) -> str:
    hover = blend(accent, "#ffffff", 0.85)
    soft = accent_soft(accent)
    return f"""
* {{
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
  font-size: 13px;
  color: #e6e8ee;
}}
QMainWindow, QWidget {{ background: #14161c; }}
QLabel, QCheckBox {{ background: transparent; }}
QLabel#pageTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#pageSubtitle {{ color: #9aa1b1; font-size: 12px; }}
QLabel#sectionTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#muted {{ color: #9aa1b1; }}
QLabel#statValue {{ font-size: 20px; font-weight: 700; }}
QLabel#statLabel {{ color: #9aa1b1; font-size: 12px; }}
QLabel#playerTitle {{ font-size: 13px; font-weight: 600; }}
QLabel#playerArtist {{ color: #9aa1b1; font-size: 12px; }}
QLabel#nowTitle {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 26px; font-weight: 700; }}
QLabel#albumTitle {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 20px; font-weight: 700; }}
QLabel#nowArtist {{ font-size: 15px; color: #9aa1b1; }}
QLabel#emptyIcon {{ font-size: 40px; color: #3a4052; }}
QLabel#emptyTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#emptyHint {{ color: #9aa1b1; }}

QFrame#card {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  border-radius: 10px;
}}
QFrame#statTile {{
  background: #202430;
  border: 1px solid {BORDER};
  border-radius: 10px;
}}
QFrame#playerBar {{
  background: #181b23;
  border-top: 1px solid {BORDER};
}}
QFrame#sidebar {{
  background: #171a21;
  border-right: 1px solid #23262f;
}}
QFrame#divider {{ background: {BORDER}; max-height: 1px; border: none; }}

QPushButton {{
  background: #232734;
  border: 1px solid #313746;
  border-radius: 7px;
  padding: 6px 12px;
}}
QPushButton:hover {{ background: #2b3040; }}
QPushButton:pressed {{ background: #343a4d; }}
QPushButton:checked {{
  background: {soft};
  border-color: {accent};
  color: {accent};
  font-weight: 600;
}}
QPushButton:disabled {{ color: #5a6072; background: #1d2029; border-color: {BORDER}; }}
QPushButton#primary {{
  background: {accent};
  border-color: {accent};
  color: #ffffff;
  font-weight: 600;
}}
QPushButton#primary:hover {{ background: {hover}; }}
QPushButton#transport {{
  min-width: 38px;
  min-height: 32px;
  padding: 2px 8px;
  font-size: 15px;
}}
QPushButton#transportPrimary {{
  min-width: 42px;
  min-height: 34px;
  padding: 2px 8px;
  font-size: 16px;
  background: {accent};
  border-color: {accent};
  color: #ffffff;
}}
QPushButton#transportPrimary:hover {{ background: {hover}; }}
QPushButton#navItem {{
  text-align: left;
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #9aa1b1;
  font-size: 14px;
}}
QPushButton#navItem:hover {{ background: #20242f; color: #e6e8ee; }}
QPushButton#navItem:checked {{ background: {soft}; color: {accent}; font-weight: 600; }}

QLineEdit, QComboBox, QSpinBox {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  border-radius: 7px;
  padding: 7px 10px;
  selection-background-color: {accent};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  selection-background-color: {soft};
  selection-color: #ffffff;
  outline: none;
}}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
  width: 16px; height: 16px;
  border-radius: 4px;
  border: 1px solid #3a4052;
  background: #1b1e26;
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}

QTableView {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  border-radius: 8px;
  gridline-color: transparent;
  selection-background-color: {soft};
  selection-color: #ffffff;
  outline: none;
}}
QTableView::item {{ padding: 4px 6px; border: none; }}
QHeaderView::section {{
  background: #1b1e26;
  color: #9aa1b1;
  border: none;
  border-bottom: 1px solid {BORDER};
  padding: 8px 6px;
  font-weight: 600;
}}
QHeaderView::section:hover {{ color: #e6e8ee; }}
QTableCornerButton::section {{ background: #1b1e26; border: none; }}

QListWidget {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  border-radius: 8px;
  outline: none;
}}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; margin: 2px 4px; }}
QListWidget::item:selected {{ background: {soft}; color: #ffffff; }}
QListWidget::item:hover {{ background: #20242f; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{
  width: 12px; height: 12px; margin: -5px 0;
  border-radius: 6px; background: #e6e8ee;
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #333a4a; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #414a5e; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollArea {{ border: none; background: transparent; }}

QStatusBar {{ color: #9aa1b1; background: #12141a; border-top: 1px solid #23262f; }}
QMenu {{ background: #1b1e26; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {soft}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QSplitter::handle {{ background: #22262f; }}
QProgressBar {{
  background: #1b1e26;
  border: 1px solid {BORDER};
  border-radius: 5px;
  text-align: center;
  color: #e6e8ee;
  font-size: 10px;
  max-height: 14px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
QToolTip {{
  background: #232734;
  color: #e6e8ee;
  border: 1px solid #3a4052;
  padding: 4px 6px;
}}
"""
