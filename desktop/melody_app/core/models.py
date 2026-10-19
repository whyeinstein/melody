"""领域模型：曲目、专辑、歌单、音乐来源与统计。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Song:
    id: int
    path: str
    source_id: int | None
    title: str
    artist: str | None
    album: str | None
    album_artist: str | None = None
    genre: str | None = None
    year: int | None = None
    track_no: int | None = None
    disc_no: int | None = None
    duration_ms: int | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    format: str | None = None
    size: int = 0
    mtime_ms: int = 0
    cover_path: str | None = None
    favorite: bool = False
    play_count: int = 0
    last_played_at: int | None = None
    missing: bool = False
    added_at: int = 0
    updated_at: int = 0

    @property
    def duration_text(self) -> str:
        if not self.duration_ms:
            return "--:--"
        seconds = max(0, int(self.duration_ms / 1000))
        return f"{seconds // 60}:{seconds % 60:02d}"

    @property
    def artist_text(self) -> str:
        return self.artist or "未知艺术家"

    @property
    def album_text(self) -> str:
        return self.album or "未知专辑"

    @property
    def format_text(self) -> str:
        return (self.format or "").upper()

    @property
    def album_key(self) -> tuple[str, str]:
        """专辑唯一键：(专辑名, 专辑艺术家)。"""
        return (self.album or "", self.album_artist or self.artist or "")


@dataclass(slots=True)
class Album:
    name: str
    album_artist: str
    year: int | None
    track_count: int
    duration_ms: int
    cover_path: str | None = None

    @property
    def artist_text(self) -> str:
        return self.album_artist or "未知艺术家"

    @property
    def duration_text(self) -> str:
        seconds = max(0, int((self.duration_ms or 0) / 1000))
        hours, rest = divmod(seconds, 3600)
        minutes, secs = divmod(rest, 60)
        if hours:
            return f"{hours} 小时 {minutes} 分"
        return f"{minutes} 分 {secs} 秒"

    @property
    def key(self) -> tuple[str, str]:
        return (self.name, self.album_artist)


@dataclass(slots=True)
class Playlist:
    id: int
    name: str
    track_count: int = 0
    created_at: int = 0
    updated_at: int = 0


@dataclass(slots=True)
class Source:
    id: int
    kind: str  # local | webdav | remote（其他协议将来可自行扩展）
    name: str
    path: str | None
    config: dict = field(default_factory=dict)
    enabled: bool = True
    added_at: int = 0

    @property
    def is_local(self) -> bool:
        return self.kind == "local"

    @property
    def kind_text(self) -> str:
        labels = {"local": "本地", "webdav": "WebDAV", "remote": "远程"}
        return labels.get(self.kind, self.kind.upper())


@dataclass(slots=True)
class LibraryStats:
    songs: int = 0
    albums: int = 0
    artists: int = 0
    sources: int = 0
    duration_ms: int = 0
    missing: int = 0

    @property
    def duration_text(self) -> str:
        seconds = max(0, int(self.duration_ms / 1000))
        hours, rest = divmod(seconds, 3600)
        minutes, _ = divmod(rest, 60)
        if hours:
            return f"{hours} 小时 {minutes} 分"
        return f"{minutes} 分"
