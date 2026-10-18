"""远程来源占位实现。

当前阶段只登记、不扫描、不播放：UI 上体现为「远程库」开关，`available()` 恒为 False。
接入具体协议时替换此文件即可（WebDAV / Navidrome / Jellyfin / SMB）。
"""

from __future__ import annotations

from ..models import Source
from .base import MusicSource, register_source


class RemoteSource(MusicSource):
    kind = "remote"

    def __init__(self, row: Source, songs_repo) -> None:
        super().__init__(row)
        self._songs = songs_repo

    def available(self) -> bool:
        # 远程协议尚未接入；这里返回 False 让 UI 显示「未连接」。
        return False

    def track_count(self) -> int:
        row = self._songs.conn.execute(
            "SELECT COUNT(*) AS c FROM songs WHERE source_id = ?", (self.id,)
        ).fetchone()
        return int(row["c"] or 0) if row else 0

    def scan(self) -> None:
        raise NotImplementedError("远程库扫描尚未实现（接口已预留）")

    def stream_url(self, path: str) -> str:
        raise NotImplementedError("远程库播放尚未实现（接口已预留）")


# 显式注册（装饰器在类定义时已注册，这里再确保一次，便于阅读）。
register_source("remote", RemoteSource)
