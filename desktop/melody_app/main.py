"""应用入口。"""

from __future__ import annotations

import argparse
import faulthandler
import os
import sys
import traceback

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from .app import build_context
from .config import app_data_dir
from .ui.main_window import MainWindow
from .ui.navigation import NAV_ITEMS


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
    parser.add_argument("--autoplay", type=int, default=-1, help="扫描后自动播放歌曲页第 N 行")
    parser.add_argument(
        "--page",
        default=None,
        choices=[item.key for item in NAV_ITEMS],
        help="启动后直接打开指定页面",
    )
    parser.add_argument("--data-dir", default=None, help="覆盖数据目录（调试/测试用）")
    args = parser.parse_args(argv)

    if args.data_dir:
        os.environ["MELODY_DATA_DIR"] = os.path.abspath(args.data_dir)

    _setup_crash_log()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Melody")
    app.setApplicationDisplayName("Melody")

    ctx = build_context()
    window = MainWindow(ctx)
    window.show()

    for folder in args.scan:
        window.add_folder_and_scan(folder)

    if args.page:
        window.show_page(args.page)

    ctx.playback.restore_session()

    if args.screenshot:
        if args.autoplay >= 0:
            QTimer.singleShot(1500, lambda: window.play_index(args.autoplay))
        delay = 6000 if args.scan else (3500 if args.autoplay >= 0 else 1800)

        def capture() -> None:
            window.grab().save(args.screenshot)
            app.quit()

        QTimer.singleShot(delay, capture)
    elif args.exit_after > 0:
        QTimer.singleShot(args.exit_after, app.quit)

    return app.exec_()
