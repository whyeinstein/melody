"""启动脚本：python desktop/run.py"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from melody_app.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
