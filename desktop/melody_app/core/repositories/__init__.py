"""仓储层：页面只通过这些类访问数据库。"""

from .albums import AlbumsRepo
from .playlists import PlaylistsRepo
from .settings import SettingsRepo
from .songs import SongsRepo
from .sources import SourcesRepo

__all__ = [
    "AlbumsRepo",
    "PlaylistsRepo",
    "SettingsRepo",
    "SongsRepo",
    "SourcesRepo",
]
