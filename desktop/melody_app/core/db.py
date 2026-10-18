"""SQLite 数据层：文件夹、曲目与基础查询。"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  artist TEXT,
  album TEXT,
  album_artist TEXT,
  genre TEXT,
  year INTEGER,
  track_no INTEGER,
  duration_ms INTEGER,
  bitrate INTEGER,
  sample_rate INTEGER,
  channels INTEGER,
  format TEXT,
  size INTEGER NOT NULL,
  mtime_ms INTEGER NOT NULL,
  cover_path TEXT,
  added_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_songs_folder ON songs(folder_id);
"""


@dataclass
class Song:
    id: int
    path: str
    title: str
    artist: str | None
    album: str | None
    duration_ms: int | None
    format: str | None
    cover_path: str | None
    folder_id: int

    @property
    def duration_text(self) -> str:
        if not self.duration_ms:
            return "--:--"
        seconds = int(self.duration_ms / 1000)
        return f"{seconds // 60}:{seconds % 60:02d}"


class Database:
    def __init__(self, path: str) -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------------------------------------------------------------- 文件夹
    def add_folder(self, path: str) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO folders(path, added_at) VALUES (?, ?)",
            (path, int(time.time() * 1000)),
        )
        self.conn.commit()
        # 不能用 lastrowid：INSERT OR IGNORE 被忽略时它会返回上一次插入（可能是曲目）的 id。
        row = self.conn.execute("SELECT id FROM folders WHERE path = ?", (path,)).fetchone()
        if row is None:
            raise RuntimeError(f"无法创建文件夹记录: {path}")
        return int(row["id"])

    def list_folders(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT f.id, f.path,
                      (SELECT COUNT(*) FROM songs s WHERE s.folder_id = f.id) AS song_count
               FROM folders f ORDER BY f.path COLLATE NOCASE"""
        ).fetchall()
        return [dict(row) for row in rows]

    def remove_folder(self, folder_id: int) -> None:
        self.conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.conn.commit()

    # ---------------------------------------------------------------- 曲目
    def find_song_file(self, path: str) -> tuple[int, int, int] | None:
        row = self.conn.execute(
            "SELECT id, size, mtime_ms FROM songs WHERE path = ?", (path,)
        ).fetchone()
        return (int(row["id"]), int(row["size"]), int(row["mtime_ms"])) if row else None

    def upsert_song(self, data: dict) -> None:
        existing = self.find_song_file(data["path"])
        now = int(time.time() * 1000)
        if existing:
            self.conn.execute(
                """UPDATE songs SET folder_id=?, title=?, artist=?, album=?, album_artist=?,
                       genre=?, year=?, track_no=?, duration_ms=?, bitrate=?, sample_rate=?,
                       channels=?, format=?, size=?, mtime_ms=?, cover_path=?, updated_at=?
                   WHERE id=?""",
                (
                    data["folder_id"], data["title"], data.get("artist"), data.get("album"),
                    data.get("album_artist"), data.get("genre"), data.get("year"),
                    data.get("track_no"), data.get("duration_ms"), data.get("bitrate"),
                    data.get("sample_rate"), data.get("channels"), data.get("format"),
                    data["size"], data["mtime_ms"], data.get("cover_path"), now, existing[0],
                ),
            )
        else:
            self.conn.execute(
                """INSERT INTO songs(path, folder_id, title, artist, album, album_artist,
                       genre, year, track_no, duration_ms, bitrate, sample_rate, channels,
                       format, size, mtime_ms, cover_path, added_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data["path"], data["folder_id"], data["title"], data.get("artist"),
                    data.get("album"), data.get("album_artist"), data.get("genre"),
                    data.get("year"), data.get("track_no"), data.get("duration_ms"),
                    data.get("bitrate"), data.get("sample_rate"), data.get("channels"),
                    data.get("format"), data["size"], data["mtime_ms"],
                    data.get("cover_path"), now, now,
                ),
            )

    def commit(self) -> None:
        self.conn.commit()

    def remove_missing(self, folder_id: int, seen_paths: Iterable[str]) -> int:
        seen = {p.lower() for p in seen_paths}
        rows = self.conn.execute(
            "SELECT id, path FROM songs WHERE folder_id = ?", (folder_id,)
        ).fetchall()
        stale = [int(r["id"]) for r in rows if str(r["path"]).lower() not in seen]
        for song_id in stale:
            self.conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        self.conn.commit()
        return len(stale)

    def list_songs(self, search: str = "", folder_id: int | None = None) -> list[Song]:
        sql = (
            "SELECT id, path, title, artist, album, duration_ms, format, cover_path, folder_id "
            "FROM songs"
        )
        where: list[str] = []
        params: list = []
        if folder_id is not None:
            where.append("folder_id = ?")
            params.append(folder_id)
        if search.strip():
            like = f"%{search.strip()}%"
            where.append("(title LIKE ? OR artist LIKE ? OR album LIKE ?)")
            params.extend([like, like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY artist COLLATE NOCASE, album COLLATE NOCASE, track_no, title COLLATE NOCASE"
        rows = self.conn.execute(sql, params).fetchall()
        return [
            Song(
                id=int(r["id"]),
                path=str(r["path"]),
                title=str(r["title"]),
                artist=r["artist"],
                album=r["album"],
                duration_ms=r["duration_ms"],
                format=r["format"],
                cover_path=r["cover_path"],
                folder_id=int(r["folder_id"]),
            )
            for r in rows
        ]

    def song_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM songs").fetchone()
        return int(row["c"]) if row else 0
