"""本地文件夹来源。"""

from __future__ import annotations

import os

from ..models import Source
from .base import MusicSource, register_source


class LocalFolderSource(MusicSource):
    kind = "local"

    def __init__(self, row: Source, songs_repo) -> None:
        super().__init__(row)
        self._songs = songs_repo

    def available(self) -> bool:
        return bool(self.path) and os.path.isdir(str(self.path))

    def track_count(self) -> int:
        row = self._songs.conn.execute(
            "SELECT COUNT(*) AS c FROM songs WHERE source_id = ?", (self.id,)
        ).fetchone()
        return int(row["c"] or 0) if row else 0

    def stream_url(self, path: str) -> str:
        return path


register_source("local", LocalFolderSource)
