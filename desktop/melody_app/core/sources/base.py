"""音乐来源抽象：本地文件夹与远程库统一接口。

新增远程协议的步骤（详见 ``docs/remote-library-interface.md``）：

1. 在 ``sources/`` 下新增 ``MusicSource`` 子类（通常继承 ``RemoteSource``）；
2. 用 ``register_source("kind", 子类)`` 注册；
3. 数据库里的 ``sources.kind`` 使用同一个 kind 值；
4. UI 只依赖 ``Source`` 行与 ``create_source_adapter()``，不需要改动页面。
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

    def test_connection(self) -> tuple[bool, str]:
        """连接自检，返回 ``(是否可用, 说明)``；本地来源默认看目录是否存在。"""
        return self.available(), ""

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
    from .webdav import WebDavSource  # noqa: F401 - 导入以触发注册

    cls = SOURCE_REGISTRY.get(row.kind)
    if cls is None:
        cls = LocalFolderSource if row.kind == "local" else RemoteSource
    return cls(row, songs_repo)
