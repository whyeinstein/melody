"""导航定义：六个一级页面。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    icon: str
    hint: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("songs", "歌曲", "♪", "浏览与筛选全部歌曲"),
    NavItem("playlists", "歌单", "≡", "管理自建歌单"),
    NavItem("library", "音乐库", "▤", "来源、扫描与曲库工具"),
    NavItem("albums", "专辑", "◉", "按专辑封面浏览"),
    NavItem("player", "播放", "▶", "正在播放与队列"),
    NavItem("settings", "设置", "⚙", "播放、外观与数据"),
)

NAV_BY_KEY = {item.key: item for item in NAV_ITEMS}

DEFAULT_PAGE = "songs"
