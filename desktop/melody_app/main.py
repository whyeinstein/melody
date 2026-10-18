"""应用入口。"""

from __future__ import annotations

import argparse
import faulthandler
import os
import sys
import traceback

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from .config import app_data_dir, db_path
from .core.db import Database
from .ui.main_window import MainWindow


def _setup_crash_log() -> None:
    """pythonw 没有控制台，把崩溃信息写到文件里便于排查。"""
    path = os.path.join(app_data_dir(), "crash.log")
    handle = open(path, "a", encoding="utf-8", buffering=1)
    faulthandler.enable(file=handle)
    sys.excepthook = lambda exc_type, exc, tb: handle.write(
        "".join(traceback.format_exception(exc_type, exc, tb)) + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="melody", description="Melody 本地音乐播放器")
    parser.add_argument("--scan", action="append", default=[], help="启动后扫描指定目录")
    parser.add_argument("--screenshot", default=None, help="把窗口截图保存到指定路径后退出")
    parser.add_argument("--exit-after", type=int, default=0, help="毫秒后自动退出")
    parser.add_argument("--autoplay", type=int, default=-1, help="扫描后自动播放第 N 行")
    args = parser.parse_args(argv)

    _setup_crash_log()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Melody")
    app.setApplicationDisplayName("Melody")

    database = Database(db_path())
    window = MainWindow(database)
    window.show()

    for folder in args.scan:
        window.add_folder_and_scan(folder)

    if args.screenshot:
        delay = 5000 if args.scan else 1500
        if args.autoplay >= 0:
            QTimer.singleShot(5500 if args.scan else 800, lambda: window.play_index(args.autoplay))
            delay = 9000

        def capture() -> None:
            window.grab().save(args.screenshot)
            app.quit()

        QTimer.singleShot(delay, capture)
    elif args.exit_after > 0:
        QTimer.singleShot(args.exit_after, app.quit)

    return app.exec_()
