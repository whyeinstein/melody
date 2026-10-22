"""界面截图工具：用测试数据库渲染各页面并保存 PNG，便于视觉迭代。

用法：
    python scripts/dev/capture-ui.py --data-dir .cache/appdata4 --out-dir .cache/ui-shots
"""

from __future__ import annotations

import argparse
import os
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "desktop"))

DEFAULT_PAGES = ["songs", "albums", "player", "library", "playlists", "settings"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.path.join(ROOT, ".cache", "appdata4"))
    parser.add_argument("--out-dir", default=os.path.join(ROOT, ".cache", "ui-shots"))
    parser.add_argument("--pages", default=",".join(DEFAULT_PAGES))
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    # 让配置/凭据/缓存都落到同一个测试数据目录，避免写入 %APPDATA%
    os.environ["MELODY_DATA_DIR"] = os.path.abspath(args.data_dir)
    db_file = os.path.join(os.path.abspath(args.data_dir), "melody.db")
    if not os.path.exists(db_file):
        print(f"找不到测试数据库：{db_file}", file=sys.stderr)
        return 2

    from melody_app.app import build_context
    from melody_app.ui.main_window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Melody")

    ctx = build_context(db_file)
    window = MainWindow(ctx)
    window.resize(args.width, args.height)
    window.show()

    pages = [page.strip() for page in args.pages.split(",") if page.strip()]
    saved: list[str] = []

    def capture(index: int) -> None:
        if index >= len(pages):
            app.quit()
            return
        key = pages[index]
        window.navigate(key)
        app.processEvents()

        def shoot() -> None:
            path = os.path.join(args.out_dir, f"{args.prefix}{key}.png")
            window.grab().save(path)
            saved.append(path)
            print("saved", path)
            QTimer.singleShot(120, lambda: capture(index + 1))

        QTimer.singleShot(450, shoot)

    QTimer.singleShot(700, lambda: capture(0))
    code = app.exec_()
    ctx.playback.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())
