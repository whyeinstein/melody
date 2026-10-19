"""应用装配：数据库 → 仓储 → 服务 → 播放控制器 → AppContext。"""

from __future__ import annotations

from . import config
from .core.credentials import CredentialStore
from .core.db import Database
from .core.library.service import LibraryService
from .core.playback.controller import PlaybackController
from .core.playback.engine import AudioEngine
from .core.playback.queue import PlayQueue
from .core.repositories.albums import AlbumsRepo
from .core.repositories.playlists import PlaylistsRepo
from .core.repositories.settings import SettingsRepo
from .core.repositories.songs import SongsRepo
from .core.repositories.sources import SourcesRepo
from .ui.app_context import AppContext


def build_context(db_file: str | None = None) -> AppContext:
    database = Database(db_file or config.db_path())
    songs = SongsRepo(database)
    albums = AlbumsRepo(database)
    playlists = PlaylistsRepo(database)
    sources = SourcesRepo(database)
    settings = SettingsRepo(database)

    credentials = CredentialStore(config.credentials_dir())
    library = LibraryService(songs, sources, credentials)
    playback = PlaybackController(AudioEngine(), PlayQueue(), songs, settings)

    return AppContext(
        songs=songs,
        albums=albums,
        playlists=playlists,
        sources=sources,
        settings=settings,
        library=library,
        playback=playback,
        credentials=credentials,
    )
