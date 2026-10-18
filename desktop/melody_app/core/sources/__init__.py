"""音乐来源：本地 / 远程。"""

from .base import (
    SOURCE_REGISTRY,
    MusicSource,
    create_source_adapter,
    register_source,
)
from .local import LocalFolderSource
from .remote import RemoteSource

__all__ = [
    "LocalFolderSource",
    "MusicSource",
    "RemoteSource",
    "SOURCE_REGISTRY",
    "create_source_adapter",
    "register_source",
]
