"""歌单仓库：歌单 CRUD 与曲目顺序维护。"""

from __future__ import annotations

import time

from ..db import Database
from ..models import Playlist, Song
from .songs import SONG_COLUMNS, song_from_row


class PlaylistsRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def conn(self):
        return self._db.conn

    def list(self) -> list[Playlist]:
        rows = self.conn.execute(
            """
            SELECT p.id, p.name, p.created_at, p.updated_at,
                   (SELECT COUNT(*) FROM playlist_items i WHERE i.playlist_id = p.id)
                       AS track_count
              FROM playlists p
             ORDER BY p.name COLLATE NOCASE
            """
        ).fetchall()
        return [
            Playlist(
                id=int(row["id"]),
                name=str(row["name"]),
                track_count=int(row["track_count"] or 0),
                created_at=int(row["created_at"] or 0),
                updated_at=int(row["updated_at"] or 0),
            )
            for row in rows
        ]

    def get(self, playlist_id: int) -> Playlist | None:
        row = self.conn.execute(
            """
            SELECT p.id, p.name, p.created_at, p.updated_at,
                   (SELECT COUNT(*) FROM playlist_items i WHERE i.playlist_id = p.id)
                       AS track_count
              FROM playlists p WHERE p.id = ?
            """,
            (playlist_id,),
        ).fetchone()
        if row is None:
            return None
        return Playlist(
            id=int(row["id"]),
            name=str(row["name"]),
            track_count=int(row["track_count"] or 0),
            created_at=int(row["created_at"] or 0),
            updated_at=int(row["updated_at"] or 0),
        )

    def create(self, name: str) -> Playlist:
        clean = name.strip()
        if not clean:
            raise ValueError("歌单名不能为空")
        now = int(time.time() * 1000)
        cursor = self.conn.execute(
            "INSERT INTO playlists(name, created_at, updated_at) VALUES (?, ?, ?)",
            (clean, now, now),
        )
        self._db.commit()
        created = self.get(int(cursor.lastrowid))
        if created is None:  # pragma: no cover - 插入后必然存在
            raise RuntimeError("创建歌单失败")
        return created

    def exists(self, name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM playlists WHERE name = ?", (name.strip(),)
        ).fetchone()
        return row is not None

    def rename(self, playlist_id: int, name: str) -> None:
        clean = name.strip()
        if not clean:
            raise ValueError("歌单名不能为空")
        self.conn.execute(
            "UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
            (clean, int(time.time() * 1000), playlist_id),
        )
        self._db.commit()

    def delete(self, playlist_id: int) -> None:
        self.conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self._db.commit()

    # ------------------------------------------------------------------ 曲目
    def tracks(self, playlist_id: int) -> list[Song]:
        rows = self.conn.execute(
            f"""
            SELECT {', '.join('s.' + column.strip() for column in SONG_COLUMNS.split(','))}
              FROM playlist_items i
              JOIN songs s ON s.id = i.song_id
             WHERE i.playlist_id = ?
             ORDER BY i.position
            """,
            (playlist_id,),
        ).fetchall()
        return [song_from_row(row) for row in rows]

    def add_songs(self, playlist_id: int, song_ids: list[int]) -> int:
        if not song_ids:
            return 0
        row = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS max_position"
            " FROM playlist_items WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        position = int(row["max_position"]) + 1 if row else 0
        now = int(time.time() * 1000)
        added = 0
        for song_id in song_ids:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO playlist_items(playlist_id, song_id, position, added_at)"
                " VALUES (?, ?, ?, ?)",
                (playlist_id, int(song_id), position, now),
            )
            if cursor.rowcount:
                added += 1
                position += 1
        if added:
            self._touch(playlist_id, now)
        self._db.commit()
        return added

    def remove_song(self, playlist_id: int, song_id: int) -> None:
        self.conn.execute(
            "DELETE FROM playlist_items WHERE playlist_id = ? AND song_id = ?",
            (playlist_id, song_id),
        )
        self._renumber(playlist_id)
        self._touch(playlist_id, int(time.time() * 1000))
        self._db.commit()

    def move_song(self, playlist_id: int, song_id: int, delta: int) -> bool:
        """上移/下移一首歌；返回是否发生移动。"""
        rows = self.conn.execute(
            "SELECT song_id FROM playlist_items WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ).fetchall()
        ids = [int(row["song_id"]) for row in rows]
        if song_id not in ids:
            return False
        index = ids.index(song_id)
        target = index + delta
        if target < 0 or target >= len(ids):
            return False
        ids[index], ids[target] = ids[target], ids[index]
        now = int(time.time() * 1000)
        self.conn.executemany(
            "UPDATE playlist_items SET position = ? WHERE playlist_id = ? AND song_id = ?",
            [(position, playlist_id, sid) for position, sid in enumerate(ids)],
        )
        self._touch(playlist_id, now)
        self._db.commit()
        return True

    def _renumber(self, playlist_id: int) -> None:
        rows = self.conn.execute(
            "SELECT song_id FROM playlist_items WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ).fetchall()
        self.conn.executemany(
            "UPDATE playlist_items SET position = ? WHERE playlist_id = ? AND song_id = ?",
            [(position, playlist_id, int(row["song_id"])) for position, row in enumerate(rows)],
        )

    def _touch(self, playlist_id: int, when: int) -> None:
        self.conn.execute(
            "UPDATE playlists SET updated_at = ? WHERE id = ?", (when, playlist_id)
        )
