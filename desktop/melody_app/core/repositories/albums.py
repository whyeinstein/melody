"""专辑仓库：按 (专辑名, 专辑艺术家) 聚合。"""

from __future__ import annotations

from ..db import Database
from ..models import Album, Song
from .songs import SONG_COLUMNS, song_from_row


class AlbumsRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def conn(self):
        return self._db.conn

    def list(self, search: str = "", source_id: int | None = None) -> list[Album]:
        where = ["album IS NOT NULL", "TRIM(album) <> ''", "missing = 0"]
        params: list[object] = []
        if source_id is not None:
            where.append("source_id = ?")
            params.append(source_id)
        if search.strip():
            like = f"%{search.strip()}%"
            where.append(
                "(album LIKE ? OR COALESCE(album_artist, '') LIKE ?"
                " OR COALESCE(artist, '') LIKE ?)"
            )
            params.extend([like, like, like])

        # 同一专辑名可能对应多个艺术家，按 (album, 专辑艺术家) 分组。
        sql = f"""
            SELECT album AS name,
                   COALESCE(album_artist, artist, '') AS album_artist,
                   MIN(year) AS year,
                   COUNT(*) AS track_count,
                   COALESCE(SUM(duration_ms), 0) AS duration_ms,
                   MAX(cover_path) AS cover_path
            FROM songs
            WHERE {' AND '.join(where)}
            GROUP BY album, COALESCE(album_artist, artist, '')
            ORDER BY album COLLATE NOCASE
        """
        rows = self.conn.execute(sql, params).fetchall()
        return [
            Album(
                name=str(row["name"]),
                album_artist=str(row["album_artist"] or ""),
                year=row["year"],
                track_count=int(row["track_count"] or 0),
                duration_ms=int(row["duration_ms"] or 0),
                cover_path=row["cover_path"],
            )
            for row in rows
        ]

    def tracks(self, album: str, album_artist: str = "") -> list[Song]:
        rows = self.conn.execute(
            f"""
            SELECT {SONG_COLUMNS} FROM songs
             WHERE album = ? AND COALESCE(album_artist, artist, '') = ? AND missing = 0
             ORDER BY COALESCE(disc_no, 0), COALESCE(track_no, 0),
                      COALESCE(title, '') COLLATE NOCASE
            """,
            (album, album_artist),
        ).fetchall()
        return [song_from_row(row) for row in rows]

    def count(self) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS c FROM (
                SELECT 1 FROM songs
                 WHERE album IS NOT NULL AND TRIM(album) <> '' AND missing = 0
                 GROUP BY album, COALESCE(album_artist, artist, '')
            )
            """
        ).fetchone()
        return int(row["c"] or 0) if row else 0
