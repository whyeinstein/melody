"""应用上下文：把仓储、服务、播放控制器与页面信号集中到一处。"""

from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal

from ..core.library.service import LibraryService
from ..core.playback.controller import PlaybackController
from ..core.repositories.albums import AlbumsRepo
from ..core.repositories.playlists import PlaylistsRepo
from ..core.repositories.settings import SettingsRepo
from ..core.repositories.songs import SongsRepo
from ..core.repositories.sources import SourcesRepo


class AppContext(QObject):
    # 数据变化
    library_changed = pyqtSignal()  # 扫描完成 / 失效清理 / 来源增删
    sources_changed = pyqtSignal()
    playlists_changed = pyqtSignal()
    favorite_changed = pyqtSignal(int, bool)  # song_id, favorite
    avatar_changed = pyqtSignal()
    # 导航与反馈
    open_songs_requested = pyqtSignal(object)  # source_id | None
    navigate_requested = pyqtSignal(str)  # 页面 key
    status_message = pyqtSignal(str)
    theme_changed = pyqtSignal()

    def __init__(
        self,
        songs: SongsRepo,
        albums: AlbumsRepo,
        playlists: PlaylistsRepo,
        sources: SourcesRepo,
        settings: SettingsRepo,
        library: LibraryService,
        playback: PlaybackController,
        credentials=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.songs = songs
        self.albums = albums
        self.playlists = playlists
        self.sources = sources
        self.settings = settings
        self.library = library
        self.playback = playback
        self.credentials = credentials

        # 音乐库的变化统一转发，页面只需订阅 AppContext。
        library.sources_changed.connect(self.sources_changed)
        library.library_changed.connect(self.library_changed)

    def toast(self, message: str) -> None:
        self.status_message.emit(message)
