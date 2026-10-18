"""深色简洁风格（后续再美化，先保证可读可用）。"""

APP_STYLESHEET = """
* { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; }
QMainWindow, QWidget { background: #14161c; color: #e6e8ee; }
QLineEdit, QListWidget, QTableView {
  background: #1b1e26; border: 1px solid #2a2e3a; border-radius: 6px;
  selection-background-color: #6c5ce7; selection-color: #ffffff;
}
QLineEdit { padding: 6px 10px; }
QTableView { gridline-color: #22262f; border-radius: 6px; }
QHeaderView::section {
  background: #1b1e26; color: #9aa1b1; border: none;
  border-bottom: 1px solid #2a2e3a; padding: 6px 8px;
}
QTableView::item { padding: 4px 6px; }
QTableView::item:selected { background: #3a3358; color: #ffffff; }
QPushButton {
  background: #232734; border: 1px solid #313746; border-radius: 6px;
  padding: 6px 12px; color: #e6e8ee;
}
QPushButton:hover { background: #2b3040; }
QPushButton:pressed { background: #343a4d; }
QPushButton#transport {
  min-width: 40px; min-height: 32px; font-size: 15px; padding: 2px 8px;
}
QPushButton#transportPrimary {
  min-width: 52px; min-height: 36px; font-size: 17px;
  background: #6c5ce7; border-color: #6c5ce7;
}
QSlider::groove:horizontal {
  height: 4px; background: #2a2e3a; border-radius: 2px;
}
QSlider::sub-page:horizontal { background: #6c5ce7; border-radius: 2px; }
QSlider::handle:horizontal {
  width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; background: #e6e8ee;
}
QStatusBar { color: #9aa1b1; }
QSplitter::handle { background: #22262f; }
QLabel#titleLabel { font-size: 14px; font-weight: 600; }
QLabel#mutedLabel { color: #9aa1b1; }
QListWidget::item { padding: 8px 10px; border-radius: 6px; }
QListWidget::item:selected { background: #2f2a46; }
"""
