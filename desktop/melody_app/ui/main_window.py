"""主窗口外壳：左侧导航 + 六个页面 + 底部播放条。"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_NAME, APP_TAGLINE, APP_VERSION
from .app_context import AppContext
from .navigation import DEFAULT_PAGE, NAV_BY_KEY, NAV_ITEMS
from .pages.albums_page import AlbumsPage
from .pages.library_page import LibraryPage
from .pages.player_page import PlayerPage
from .pages.playlists_page import PlaylistsPage
from .pages.settings_page import SettingsPage
from .pages.songs_page import SongsPage
from .player_bar import PlayerBar
from .theme import build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}
        self._current_key = ""

        self.setWindowTitle(APP_NAME)
        self.resize(1320, 860)
        self.setMinimumSize(1080, 700)

        self._build_ui()
        self._connect()
        self._apply_theme()
        self.navigate(DEFAULT_PAGE)
        self._update_sidebar_counts()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(196)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 16, 14, 12)
        side_layout.setSpacing(4)

        logo = QLabel(APP_NAME)
        logo.setStyleSheet("font-size:18px; font-weight:700;")
        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("muted")
        tagline.setStyleSheet("font-size:11px;")
        side_layout.addWidget(logo)
        side_layout.addWidget(tagline)
        side_layout.addSpacing(14)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for item in NAV_ITEMS:
            button = QPushButton(f"{item.icon}   {item.label}")
            button.setObjectName("navItem")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(item.hint)
            button.clicked.connect(
                lambda _checked=False, key=item.key: self.navigate(key)
            )
            self._nav_group.addButton(button)
            self._nav_buttons[item.key] = button
            side_layout.addWidget(button)

        side_layout.addStretch(1)
        self.library_label = QLabel("曲库：—")
        self.library_label.setObjectName("muted")
        self.library_label.setStyleSheet("font-size:11px;")
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("muted")
        self.version_label.setStyleSheet("font-size:11px;")
        side_layout.addWidget(self.library_label)
        side_layout.addWidget(self.version_label)
        content_row.addWidget(sidebar)

        self._stack = QStackedWidget()
        self._stack.setContentsMargins(0, 0, 0, 0)
        content_row.addWidget(self._stack, 1)
        root.addLayout(content_row, 1)

        self._pages = {
            "songs": SongsPage(self._ctx),
            "playlists": PlaylistsPage(self._ctx),
            "library": LibraryPage(self._ctx),
            "albums": AlbumsPage(self._ctx),
            "player": PlayerPage(self._ctx),
            "settings": SettingsPage(self._ctx),
        }
        for key in NAV_BY_KEY:
            self._stack.addWidget(self._pages[key])

        self.player_bar = PlayerBar(self._ctx)
        root.addWidget(self.player_bar)

        self.setCentralWidget(central)
        self.statusBar().showMessage("就绪", 3000)

    def _connect(self) -> None:
        self.player_bar.open_player.connect(lambda: self.navigate("player"))
        self._ctx.status_message.connect(self._show_status)
        self._ctx.open_songs_requested.connect(self._open_songs)
        self._ctx.theme_changed.connect(self._apply_theme)
        self._ctx.library_changed.connect(self._update_sidebar_counts)
        self._ctx.playlists_changed.connect(self._update_sidebar_counts)

    # ------------------------------------------------------------------ 导航
    def navigate(self, key: str, refresh: bool = True) -> None:
        if key not in self._pages:
            return
        page = self._pages[key]
        self._stack.setCurrentWidget(page)
        button = self._nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        self._current_key = key
        if refresh and hasattr(page, "refresh"):
            page.refresh()  # type: ignore[call-arg]

    def show_page(self, key: str) -> None:
        self.navigate(key)

    @property
    def current_page_key(self) -> str:
        return self._current_key

    def _open_songs(self, source_id) -> None:
        page: SongsPage = self._pages["songs"]  # type: ignore[assignment]
        self.navigate("songs", refresh=False)
        page.refresh()
        page.set_source_filter(source_id)

    # ------------------------------------------------------------------ 主题
    def _apply_theme(self) -> None:
        accent = self._ctx.settings.accent
        self.setStyleSheet(build_stylesheet(accent))
        for page in self._pages.values():
            for attr in ("table", "track_table"):
                widget = getattr(page, attr, None)
                if widget is not None and hasattr(widget, "set_accent"):
                    widget.set_accent(accent)

    # ------------------------------------------------------------------ 杂项
    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)

    def _update_sidebar_counts(self) -> None:
        stats = self._ctx.library.stats()
        self.library_label.setText(
            f"曲库：{stats.songs} 首 / {stats.albums} 张专辑"
        )

    # ------------------------------------------------------------------ CLI
    def add_folder_and_scan(self, directory: str) -> None:
        try:
            source = self._ctx.library.add_local_folder(directory)
        except ValueError as error:
            self._show_status(str(error))
            return
        self._show_status(f"已添加来源「{source.name}」，开始扫描…")
        self._ctx.library.start_scan([source.id])

    def play_index(self, row: int) -> None:
        page: SongsPage = self._pages["songs"]  # type: ignore[assignment]
        song = page.table.song_at(row)
        if song is None:
            return
        self._ctx.playback.play_songs(page.table.songs(), row)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._ctx.playback.save_session()
        self._ctx.playback.stop()
        super().closeEvent(event)
