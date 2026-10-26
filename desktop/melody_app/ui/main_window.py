"""主窗外壳：品牌侧边栏 + 六个页面 + 底部播放条。"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt, QTimer
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

from ..config import APP_NAME, APP_TAGLINE, APP_VERSION, avatar_file
from ..core.profile import has_avatar
from ..core.sources.webdav_proxy import shutdown_all
from .app_context import AppContext
from .avatar_actions import choose_avatar, clear_avatar
from .icons import icon
from .navigation import DEFAULT_PAGE, NAV_BY_KEY, NAV_ITEMS
from .pages.albums_page import AlbumsPage
from .pages.library_page import LibraryPage
from .pages.player_page import PlayerPage
from .pages.playlists_page import PlaylistsPage
from .pages.settings_page import SettingsPage
from .pages.songs_page import SongsPage
from .player_bar import PlayerBar
from .theme import DEFAULT_ACCENT, TEXT_DIM, TEXT_MUTED, build_stylesheet
from .widgets.avatar import AvatarButton

NAV_ICONS = {
    "songs": "music",
    "playlists": "list",
    "library": "folder",
    "albums": "album",
    "player": "play",
    "settings": "settings",
}


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}
        self._current_key = ""
        self._accent = DEFAULT_ACCENT
        self._toast: QLabel | None = None
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._hide_toast)

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
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        # ---------------------------------------------------------- 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        self.avatar = AvatarButton(44)
        self.avatar.clicked.connect(self._choose_avatar)
        self.avatar.remove_requested.connect(self._remove_avatar)
        self._refresh_avatar()
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setObjectName("brandName")
        tag = QLabel(f"本地用户 · {APP_TAGLINE}")
        tag.setObjectName("brandTag")
        brand_text.addWidget(name)
        brand_text.addWidget(tag)
        brand_row.addWidget(self.avatar)
        brand_row.addLayout(brand_text, 1)
        side_layout.addLayout(brand_row)
        side_layout.addSpacing(22)

        section = QLabel("浏览")
        section.setObjectName("navSection")
        side_layout.addWidget(section)
        side_layout.addSpacing(6)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for item in NAV_ITEMS:
            button = QPushButton(f"  {item.label}")
            button.setObjectName("navItem")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(item.hint)
            button.setIcon(icon(NAV_ICONS.get(item.key, "music"), TEXT_MUTED, 18))
            button.setIconSize(QSize(18, 18))
            button.clicked.connect(
                lambda _checked=False, key=item.key: self.navigate(key)
            )
            self._nav_group.addButton(button)
            self._nav_buttons[item.key] = button
            side_layout.addWidget(button)

        side_layout.addStretch(1)

        self.library_label = QLabel("曲库：—")
        self.library_label.setObjectName("dim")
        self.library_label.setStyleSheet("font-size: 11px;")
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("dim")
        self.version_label.setStyleSheet("font-size: 11px;")
        side_layout.addWidget(self.library_label)
        side_layout.addWidget(self.version_label)
        content_row.addWidget(sidebar)

        # ---------------------------------------------------------- 页面区
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self._stack = QStackedWidget()
        content_layout.addWidget(self._stack)
        content_row.addWidget(content, 1)
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
        self.statusBar().hide()

        self._toast = QLabel(central)
        self._toast.setObjectName("toast")
        self._toast.setStyleSheet(
            "background: rgba(28,34,48,235); border: 1px solid #2b3444;"
            "border-radius: 10px; padding: 8px 16px; color: #E9EDF5;"
        )
        self._toast.hide()

    def _connect(self) -> None:
        self.player_bar.open_player.connect(lambda: self.navigate("player"))
        self._ctx.status_message.connect(self._show_status)
        self._ctx.open_songs_requested.connect(self._open_songs)
        self._ctx.theme_changed.connect(self._apply_theme)
        self._ctx.library_changed.connect(self._update_sidebar_counts)
        self._ctx.playlists_changed.connect(self._update_sidebar_counts)
        self._ctx.avatar_changed.connect(self._refresh_avatar)

    # ------------------------------------------------------------------ 导航
    def navigate(self, key: str, refresh: bool = True) -> None:
        if key not in self._pages:
            return
        page = self._pages[key]
        self._stack.setCurrentWidget(page)
        for nav_key, button in self._nav_buttons.items():
            button.setChecked(nav_key == key)
        self._current_key = key
        if refresh and hasattr(page, "refresh"):
            page.refresh()  # type: ignore[call-arg]

    def _fade_in(self, page: QWidget) -> None:
        # 保留方法以便后续做更安全的过渡（QGraphicsOpacityEffect 包裹 QScrollArea
        # 时会出现局部半透明残留，暂时不启用）。
        return

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

    # ------------------------------------------------------------------ 头像
    def _choose_avatar(self) -> None:
        choose_avatar(self, self._ctx)

    def _remove_avatar(self) -> None:
        clear_avatar(self, self._ctx)

    def _refresh_avatar(self) -> None:
        self.avatar.set_avatar(avatar_file() if has_avatar() else None)
        self.avatar.set_accent(self._accent)

    # ------------------------------------------------------------------ 主题
    def _apply_theme(self) -> None:
        accent = self._ctx.settings.accent
        self._accent = accent
        self.setStyleSheet(build_stylesheet(accent))
        self.avatar.set_accent(accent)
        for key, button in self._nav_buttons.items():
            checked = key == self._current_key
            color = accent if checked else TEXT_MUTED
            button.setIcon(icon(NAV_ICONS.get(key, "music"), color, 18))
        for page in self._pages.values():
            for attr in ("table", "track_table"):
                widget = getattr(page, attr, None)
                if widget is not None and hasattr(widget, "set_accent"):
                    widget.set_accent(accent)
        self.player_bar.set_accent(accent)

    # ------------------------------------------------------------------ 提示
    def _show_status(self, message: str) -> None:
        if self._toast is None:
            return
        self._toast.setText(message)
        self._toast.adjustSize()
        self._reposition_toast()
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(2600)

    def _hide_toast(self) -> None:
        if self._toast is not None:
            self._toast.hide()

    def _reposition_toast(self) -> None:
        if self._toast is None or self.centralWidget() is None:
            return
        parent = self.centralWidget()
        hint = self._toast.sizeHint()
        x = (parent.width() - hint.width()) // 2
        y = parent.height() - self.player_bar.height() - hint.height() - 24
        self._toast.move(max(12, x), max(12, y))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reposition_toast()

    def _update_sidebar_counts(self) -> None:
        stats = self._ctx.library.stats()
        self.library_label.setText(f"曲库：{stats.songs} 首 · {stats.albums} 张专辑")

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
        shutdown_all()
        super().closeEvent(event)
