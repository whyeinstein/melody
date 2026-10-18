"""曲目仓库：查询、扫描写入、收藏/播放记录、统计。"""

from __future__ import annotations

import sqlite3
import time
from typing import Iterable

from ..db import Database
from ..models import LibraryStats, Song

SONG_COLUMNS = """
    id, path, source_id, title, artist, album, album_artist, genre, year, track_no,
    disc_no, duration_ms, bitrate, sample_rate, channels, format, size, mtime_ms,
    cover_path, favorite, play_count, last_played_at, missing, added_at, updated_at
"""

SORT_FIELDS = {
    "title": "COALESCE(title, '') COLLATE NOCASE",
    "artist": "COALESCE(artist, '') COLLATE NOCASE",
    "album": "COALESCE(album, '') COLLATE NOCASE",
    "duration": "COALESCE(duration_ms, 0)",
    "format": "COALESCE(format, '') COLLATE NOCASE",
    "year": "COALESCE(year, 0)",
    "added": "added_at",
}


def song_from_row(row: sqlite3.Row) -> Song:
    return Song(
        id=int(row["id"]),
        path=str(row["path"]),
        source_id=row["source_id"],
        title=str(row["title"]),
        artist=row["artist"],
        album=row["album"],
        album_artist=row["album_artist"],
        genre=row["genre"],
        year=row["year"],
        track_no=row["track_no"],
        disc_no=row["disc_no"],
        duration_ms=row["duration_ms"],
        bitrate=row["bitrate"],
        sample_rate=row["sample_rate"],
        channels=row["channels"],
        format=row["format"],
        size=int(row["size"] or 0),
        mtime_ms=int(row["mtime_ms"] or 0),
        cover_path=row["cover_path"],
        favorite=bool(row["favorite"]),
        play_count=int(row["play_count"] or 0),
        last_played_at=row["last_played_at"],
        missing=bool(row["missing"]),
        added_at=int(row["added_at"] or 0),
        updated_at=int(row["updated_at"] or 0),
    )


class SongsRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self._db.conn

    @property
    def database_path(self) -> str:
        """扫描线程需要独立连接时使用。"""
        return self._db.path

    def commit(self) -> None:
        self._db.commit()

    # ------------------------------------------------------------------ 查询
    def query(
        self,
        *,
        search: str = "",
        source_id: int | None = None,
        favorite: bool | None = None,
        album: str | None = None,
        album_artist: str | None = None,
        artist: str | None = None,
        recent: bool = False,
        include_missing: bool = False,
        sort: str = "artist",
        direction: str = "asc",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Song]:
        where: list[str] = []
        params: list[object] = []

        if not include_missing:
            where.append("missing = 0")
        if favorite is not None:
            where.append("favorite = ?")
            params.append(1 if favorite else 0)
        if source_id is not None:
            where.append("source_id = ?")
            params.append(source_id)
        if album is not None:
            where.append("album = ?")
            params.append(album)
        if album_artist is not None:
            where.append("COALESCE(album_artist, artist, '') = ?")
            params.append(album_artist)
        if artist is not None:
            where.append("artist = ?")
            params.append(artist)
        if recent:
            where.append("last_played_at IS NOT NULL")
        if search.strip():
            like = f"%{search.strip()}%"
            where.append(
                "(title LIKE ? OR COALESCE(artist, '') LIKE ?"
                " OR COALESCE(album, '') LIKE ? OR COALESCE(album_artist, '') LIKE ?)"
            )
            params.extend([like, like, like, like])

        order = self._order_clause(sort, direction, recent)
        sql = f"SELECT {SONG_COLUMNS} FROM songs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + order
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([max(0, limit), max(0, offset)])

        rows = self.conn.execute(sql, params).fetchall()
        return [song_from_row(row) for row in rows]

    def _order_clause(self, sort: str, direction: str, recent: bool) -> str:
        if recent:
            return "last_played_at DESC, COALESCE(title, '') COLLATE NOCASE"
        key = SORT_FIELDS.get(sort, SORT_FIELDS["artist"])
        dir_sql = "DESC" if str(direction).lower() == "desc" else "ASC"
        return (
            f"{key} {dir_sql}, COALESCE(album, '') COLLATE NOCASE,"
            " COALESCE(disc_no, 0), COALESCE(track_no, 0),"
            " COALESCE(title, '') COLLATE NOCASE"
        )

    def get(self, song_id: int) -> Song | None:
        row = self.conn.execute(
            f"SELECT {SONG_COLUMNS} FROM songs WHERE id = ?", (song_id,)
        ).fetchone()
        return song_from_row(row) if row else None

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM songs").fetchone()
        return int(row["c"]) if row else 0

    def stats(self) -> LibraryStats:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS songs,
                   COUNT(DISTINCT CASE WHEN album IS NOT NULL AND TRIM(album) <> ''
                                       THEN album END) AS albums,
                   COUNT(DISTINCT CASE WHEN artist IS NOT NULL AND TRIM(artist) <> ''
                                       THEN artist END) AS artists,
                   COALESCE(SUM(duration_ms), 0) AS duration_ms,
                   COALESCE(SUM(missing), 0) AS missing
            FROM songs
            """
        ).fetchone()
        sources = self.conn.execute("SELECT COUNT(*) AS c FROM sources").fetchone()
        return LibraryStats(
            songs=int(row["songs"] or 0),
            albums=int(row["albums"] or 0),
            artists=int(row["artists"] or 0),
            sources=int(sources["c"] or 0) if sources else 0,
            duration_ms=int(row["duration_ms"] or 0),
            missing=int(row["missing"] or 0),
        )

    # -------------------------------------------------------------- 扫描写入
    def find_file(self, path: str) -> tuple[int, int, int] | None:
        row = self.conn.execute(
            "SELECT id, size, mtime_ms FROM songs WHERE path = ?", (path,)
        ).fetchone()
        return (int(row["id"]), int(row["size"]), int(row["mtime_ms"])) if row else None

    def find_files_for_source(self, source_id: int) -> dict[str, tuple[int, int, int]]:
        """扫描前一次性取回该来源的已有文件状态（键为小写路径），避免在子线程里查库。"""
        rows = self.conn.execute(
            "SELECT path, id, size, mtime_ms FROM songs WHERE source_id = ?", (source_id,)
        ).fetchall()
        return {
            str(row["path"]).lower(): (
                int(row["id"]),
                int(row["size"]),
                int(row["mtime_ms"]),
            )
            for row in rows
        }

    def upsert_scan(self, data: dict) -> None:
        existing = self.find_file(data["path"])
        now = int(time.time() * 1000)
        if existing:
            self.conn.execute(
                """
                UPDATE songs SET source_id = ?, title = ?, artist = ?, album = ?,
                       album_artist = ?, genre = ?, year = ?, track_no = ?, disc_no = ?,
                       duration_ms = ?, bitrate = ?, sample_rate = ?, channels = ?,
                       format = ?, size = ?, mtime_ms = ?, cover_path = ?, missing = 0,
                       updated_at = ?
                 WHERE id = ?
                """,
                (
                    data["source_id"], data["title"], data.get("artist"), data.get("album"),
                    data.get("album_artist"), data.get("genre"), data.get("year"),
                    data.get("track_no"), data.get("disc_no"), data.get("duration_ms"),
                    data.get("bitrate"), data.get("sample_rate"), data.get("channels"),
                    data.get("format"), data["size"], data["mtime_ms"],
                    data.get("cover_path"), now, existing[0],
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO songs (
                    path, source_id, title, artist, album, album_artist, genre, year,
                    track_no, disc_no, duration_ms, bitrate, sample_rate, channels,
                    format, size, mtime_ms, cover_path, favorite, play_count,
                    last_played_at, missing, added_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,NULL,0,?,?)
                """,
                (
                    data["path"], data["source_id"], data["title"], data.get("artist"),
                    data.get("album"), data.get("album_artist"), data.get("genre"),
                    data.get("year"), data.get("track_no"), data.get("disc_no"),
                    data.get("duration_ms"), data.get("bitrate"), data.get("sample_rate"),
                    data.get("channels"), data.get("format"), data["size"],
                    data["mtime_ms"], data.get("cover_path"), now, now,
                ),
            )

    def remove_missing_source_files(self, source_id: int, seen_paths: Iterable[str]) -> int:
        seen = {p.lower() for p in seen_paths}
        rows = self.conn.execute(
            "SELECT id, path FROM songs WHERE source_id = ?", (source_id,)
        ).fetchall()
        stale = [int(row["id"]) for row in rows if str(row["path"]).lower() not in seen]
        for song_id in stale:
            self.conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        return len(stale)

    # ---------------------------------------------------------------- 交互写
    def set_favorite(self, song_id: int, favorite: bool) -> None:
        self.conn.execute(
            "UPDATE songs SET favorite = ? WHERE id = ?",
            (1 if favorite else 0, song_id),
        )
        self._db.commit()

    def record_play(self, song_id: int, when: int | None = None) -> None:
        now = int(when if when is not None else time.time() * 1000)
        self.conn.execute(
            "UPDATE songs SET play_count = play_count + 1, last_played_at = ? WHERE id = ?",
            (now, song_id),
        )
        self.conn.execute(
            "INSERT INTO play_history(song_id, played_at) VALUES (?, ?)", (song_id, now)
        )
        self._db.commit()

    def set_missing(self, song_ids: Iterable[int], missing: bool = True) -> None:
        ids = [int(i) for i in song_ids]
        if not ids:
            return
        self.conn.executemany(
            "UPDATE songs SET missing = ? WHERE id = ?",
            [(1 if missing else 0, song_id) for song_id in ids],
        )
        self._db.commit()

    def delete_missing(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM songs WHERE missing = 1").fetchone()
        total = int(row["c"] or 0) if row else 0
        if total:
            self.conn.execute("DELETE FROM songs WHERE missing = 1")
            self._db.commit()
        return total
