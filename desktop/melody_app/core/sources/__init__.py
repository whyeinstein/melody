"""音乐来源：本地 / 远程（远程当前只有接口占位）。"""

from .base import (
    SOURCE_REGISTRY,
    MusicSource,
    create_source_adapter,
    register_source,
)
from .local import LocalFolderSource
from .remote import RemoteEntry, RemoteSource
from .webdav import WebDavSource
from .webdav_client import WebDavClient, WebDavConfig, WebDavEntry, WebDavError

__all__ = [
    "LocalFolderSource",
    "MusicSource",
    "RemoteEntry",
    "RemoteSource",
    "SOURCE_REGISTRY",
    "WebDavClient",
    "WebDavConfig",
    "WebDavEntry",
    "WebDavError",
    "WebDavSource",
    "create_source_adapter",
    "register_source",
]
