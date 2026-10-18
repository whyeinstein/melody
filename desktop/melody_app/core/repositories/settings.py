"""设置仓库：key → JSON 值的简单持久化。"""

from __future__ import annotations

import json

from ..db import Database

# 播放相关键
KEY_VOLUME = "playback.volume"
KEY_MUTED = "playback.muted"
KEY_SHUFFLE = "playback.shuffle"
KEY_REPEAT = "playback.repeat"
KEY_LAST_SONG = "playback.last_song_id"
KEY_LAST_POSITION = "playback.last_position_ms"
KEY_RESTORE_SESSION = "playback.restore_session"
# 外观
KEY_ACCENT = "appearance.accent"
# 音乐库
KEY_LIBRARY_SORT = "library.sort"
KEY_LIBRARY_DIRECTION = "library.direction"
KEY_LAST_PAGE = "ui.last_page"

DEFAULT_VOLUME = 80
DEFAULT_ACCENT = "#6c5ce7"


class SettingsRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def conn(self):
        return self._db.conn

    def get(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, ValueError):
            return default

    def set(self, key: str, value) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        self._db.commit()

    def remove(self, key: str) -> None:
        self.conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        self._db.commit()

    def all(self) -> dict:
        result: dict = {}
        for row in self.conn.execute("SELECT key, value FROM settings"):
            try:
                result[str(row["key"])] = json.loads(row["value"])
            except (TypeError, ValueError):
                continue
        return result

    # ------------------------------------------------------------- 类型化读取
    def get_int(self, key: str, default: int) -> int:
        value = self.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, default)
        return bool(value)

    def get_str(self, key: str, default: str = "") -> str:
        value = self.get(key, default)
        return value if isinstance(value, str) else default

    # ------------------------------------------------------------- 常用快捷
    @property
    def volume(self) -> int:
        return max(0, min(100, self.get_int(KEY_VOLUME, DEFAULT_VOLUME)))

    @volume.setter
    def volume(self, value: int) -> None:
        self.set(KEY_VOLUME, max(0, min(100, int(value))))

    @property
    def shuffle(self) -> bool:
        return self.get_bool(KEY_SHUFFLE, False)

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        self.set(KEY_SHUFFLE, bool(value))

    @property
    def repeat_mode(self) -> str:
        mode = self.get_str(KEY_REPEAT, "off")
        return mode if mode in {"off", "all", "one"} else "off"

    @repeat_mode.setter
    def repeat_mode(self, value: str) -> None:
        self.set(KEY_REPEAT, value if value in {"off", "all", "one"} else "off")

    @property
    def accent(self) -> str:
        return self.get_str(KEY_ACCENT, DEFAULT_ACCENT)

    @accent.setter
    def accent(self, value: str) -> None:
        self.set(KEY_ACCENT, value)
