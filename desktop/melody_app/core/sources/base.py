"""音乐来源抽象：本地文件夹与远程库统一接口。

后续接入 WebDAV / Navidrome / SMB 时，只需：
1. 在 `sources/` 下新增一个 `MusicSource` 子类；
2. 用 `register_source("kind", 子类)` 注册；
3. UI 只依赖 `Source` 行与 `create_source_adapter()`，无需改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Source


class MusicSource(ABC):
    """一个具体来源的运行时适配器。"""

    kind: str = "base"

    def __init__(self, row: Source) -> None:
        self.row = row

    @property
    def id(self) -> int:
        return self.row.id

    @property
    def name(self) -> str:
        return self.row.name

    @property
    def enabled(self) -> bool:
        return self.row.enabled

    @property
    def path(self) -> str | None:
        return self.row.path

    @abstractmethod
    def available(self) -> bool:
        """当前环境下来源是否可用（本地：目录存在；远程：连接成功）。"""

    @abstractmethod
    def track_count(self) -> int:
        """来源下的曲目数量。"""

    def scan(self) -> None:
        raise NotImplementedError(f"{self.kind} 来源暂不支持扫描")

    def stream_url(self, path: str) -> str:
        """播放地址：本地返回文件路径，远程返回可交给播放器的 URL。"""
        return path


SOURCE_REGISTRY: dict[str, type[MusicSource]] = {}


def register_source(kind: str, source_type: type[MusicSource]) -> type[MusicSource]:
    SOURCE_REGISTRY[kind] = source_type
    return source_type


def create_source_adapter(row: Source, songs_repo) -> MusicSource:
    """按 kind 创建适配器；未知类型回退到占位实现。"""
    from .local import LocalFolderSource
    from .remote import RemoteSource

    cls = SOURCE_REGISTRY.get(row.kind)
    if cls is None:
        cls = LocalFolderSource if row.kind == "local" else RemoteSource
    return cls(row, songs_repo)
