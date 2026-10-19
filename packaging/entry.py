"""打包入口：PyInstaller 从这里启动 Melody。"""

from __future__ import annotations

import sys

from melody_app.main import main

if __name__ == "__main__":
    sys.exit(main())
