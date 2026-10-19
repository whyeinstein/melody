"""远程来源通用占位实现：定义远程库需要实现的接口，但暂不接任何协议。

当前阶段只做三件事：
- 允许在数据库里登记远程来源（``sources.kind`` 为具体协议名，如 ``webdav``）；
- 给 UI 提供 ``available() / test_connection()`` 等统一入口（当前恒为不可用）；
- 用 ``NotImplementedError`` 明确标出后续要补齐的方法，避免误以为已实现。

具体协议实现见 ``webdav.py``（同样为占位）与 ``docs/remote-library-interface.md``。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Source
from .base import MusicSource, register_source


@dataclass(slots=True)
class RemoteEntry:
    """远程目录里的一个条目（文件或目录）。"""

    path: str  # 来源内相对路径，作为 songs.path 的组成部分
    size: int = 0
    mtime_ms: int = 0
    is_dir: bool = False


class RemoteSource(MusicSource):
    kind = "remote"
    protocol = "remote"

    def __init__(self, row: Source, songs_repo, credentials=None) -> None:
        super().__init__(row)
        self._songs = songs_repo
        self._credentials = credentials

    # ------------------------------------------------------------------ 状态
    def available(self) -> bool:
        # 协议尚未实现；返回 False 让 UI 显示「未连接」。
        return False

    def test_connection(self) -> tuple[bool, str]:
        return False, "远程库尚未实现（接口已预留）"

    def track_count(self) -> int:
        row = self._songs.conn.execute(
            "SELECT COUNT(*) AS c FROM songs WHERE source_id = ?", (self.id,)
        ).fetchone()
        return int(row["c"] or 0) if row else 0

    # ---------------------------------------------------------- 待实现的接口
    def connect(self) -> None:
        """建立会话/校验凭据；失败时抛出异常或在 test_connection 返回说明。"""
        raise NotImplementedError("远程库连接尚未实现（接口已预留）")

    def list_entries(self) -> list[RemoteEntry]:
        """递归（或按目录）列出远程音频文件。"""
        raise NotImplementedError("远程库列目录尚未实现（接口已预留）")

    def probe(self, path: str) -> dict | None:
        """读取远程音频的标签信息，返回结构与 ``library.ffprobe.probe`` 一致。"""
        raise NotImplementedError("远程库元数据读取尚未实现（接口已预留）")

    def fetch_cover(self, path: str, target: str) -> bool:
        """把远程音频的内嵌封面导出到本地 ``target``。"""
        raise NotImplementedError("远程库封面提取尚未实现（接口已预留）")

    def scan(self) -> None:
        raise NotImplementedError("远程库扫描尚未实现（接口已预留）")

    def stream_url(self, path: str) -> str:
        raise NotImplementedError("远程库播放尚未实现（接口已预留）")


register_source("remote", RemoteSource)
