"""SQLite 连接与 schema 管理（v2）。

v2 相对 v1 的变化：
- 新增 sources / playlists / playlist_items / settings / play_history / meta；
- songs 用 source_id 取代 folder_id，并新增 favorite / play_count / last_played_at / missing / disc_no；
- 旧库打开时自动迁移，迁移前备份为 ``<db>.v1.bak``。
"""

from __future__ import annotations

import os
import sqlite3

SCHEMA_VERSION = 2

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT,
  config TEXT NOT NULL DEFAULT '{}',
  enabled INTEGER NOT NULL DEFAULT 1,
  added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  artist TEXT,
  album TEXT,
  album_artist TEXT,
  genre TEXT,
  year INTEGER,
  track_no INTEGER,
  disc_no INTEGER,
  duration_ms INTEGER,
  bitrate INTEGER,
  sample_rate INTEGER,
  channels INTEGER,
  format TEXT,
  size INTEGER NOT NULL,
  mtime_ms INTEGER NOT NULL,
  cover_path TEXT,
  favorite INTEGER NOT NULL DEFAULT 0,
  play_count INTEGER NOT NULL DEFAULT 0,
  last_played_at INTEGER,
  missing INTEGER NOT NULL DEFAULT 0,
  added_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS playlists (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS playlist_items (
  playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  added_at INTEGER NOT NULL,
  PRIMARY KEY (playlist_id, song_id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS play_history (
  id INTEGER PRIMARY KEY,
  song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  played_at INTEGER NOT NULL
);
"""

INDEXES_V2 = (
    "CREATE INDEX IF NOT EXISTS idx_songs_source ON songs(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_songs_favorite ON songs(favorite)",
    "CREATE INDEX IF NOT EXISTS idx_songs_last_played ON songs(last_played_at)",
    "CREATE INDEX IF NOT EXISTS idx_songs_missing ON songs(missing)",
    "CREATE INDEX IF NOT EXISTS idx_playlist_items_song ON playlist_items(song_id)",
    "CREATE INDEX IF NOT EXISTS idx_play_history_time ON play_history(played_at)",
)

SONGS_V2_DDL = """
CREATE TABLE songs_v2 (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  artist TEXT,
  album TEXT,
  album_artist TEXT,
  genre TEXT,
  year INTEGER,
  track_no INTEGER,
  disc_no INTEGER,
  duration_ms INTEGER,
  bitrate INTEGER,
  sample_rate INTEGER,
  channels INTEGER,
  format TEXT,
  size INTEGER NOT NULL,
  mtime_ms INTEGER NOT NULL,
  cover_path TEXT,
  favorite INTEGER NOT NULL DEFAULT 0,
  play_count INTEGER NOT NULL DEFAULT 0,
  last_played_at INTEGER,
  missing INTEGER NOT NULL DEFAULT 0,
  added_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
"""


def _basename(path: str) -> str:
    normalized = os.path.normpath(path)
    name = os.path.basename(normalized.rstrip("\\/"))
    return name or normalized


def _statements(script: str) -> list[str]:
    """把多语句 DDL 拆成单条（sqlite3.execute 一次只接受一条语句）。"""
    return [part.strip() for part in script.split(";") if part.strip()]


class Database:
    """单连接 SQLite 封装。扫描线程与界面线程共用，靠 WAL 与 SQLite 自身锁协调。"""

    def __init__(self, path: str) -> None:
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # 自动提交模式：迁移用显式 BEGIN/COMMIT，其余写入由 repository 主动 commit。
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    # ---------------------------------------------------------------- schema
    def _table_exists(self, name: str) -> bool:
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        return row is not None

    def _columns(self, table: str) -> set[str]:
        return {str(row["name"]) for row in self.conn.execute(f"PRAGMA table_info({table})")}

    def _migrate(self) -> None:
        if not self._table_exists("songs"):
            self._create_v2()
            return
        if "favorite" not in self._columns("songs"):
            self._migrate_v1_to_v2()
            return
        # 已经是 v2：补齐可能缺失的对象（旧版本增量升级）。
        self.conn.executescript(SCHEMA_V2)
        for statement in INDEXES_V2:
            self.conn.execute(statement)
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.conn.commit()

    def _create_v2(self) -> None:
        self.conn.executescript(SCHEMA_V2)
        for statement in INDEXES_V2:
            self.conn.execute(statement)
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.conn.commit()

    def _migrate_v1_to_v2(self) -> None:
        """v1（folders + songs.folder_id）→ v2（sources + songs.source_id）。"""
        self._backup_v1()

        conn = self.conn
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute("BEGIN")
            for statement in _statements(SCHEMA_V2):
                conn.execute(statement)
            folders_columns = (
                self._columns("folders") if self._table_exists("folders") else set()
            )
            if folders_columns:
                for row in conn.execute(
                    "SELECT id, path, added_at FROM folders ORDER BY id"
                ).fetchall():
                    path = str(row["path"])
                    conn.execute(
                        "INSERT INTO sources(kind, name, path, config, enabled, added_at)"
                        " VALUES('local', ?, ?, '{}', 1, ?)",
                        (_basename(path), path, int(row["added_at"])),
                    )

            conn.execute(SONGS_V2_DDL)
            conn.execute(
                """
                INSERT INTO songs_v2 (
                    id, path, source_id, title, artist, album, album_artist, genre, year,
                    track_no, disc_no, duration_ms, bitrate, sample_rate, channels, format,
                    size, mtime_ms, cover_path, favorite, play_count, last_played_at,
                    missing, added_at, updated_at
                )
                SELECT
                    s.id, s.path,
                    (SELECT src.id FROM sources src
                      WHERE src.path = (SELECT f.path FROM folders f WHERE f.id = s.folder_id)
                      LIMIT 1),
                    s.title, s.artist, s.album, s.album_artist, s.genre, s.year,
                    s.track_no, NULL, s.duration_ms, s.bitrate, s.sample_rate, s.channels,
                    s.format, s.size, s.mtime_ms, s.cover_path, 0, 0, NULL, 0,
                    s.added_at, s.updated_at
                FROM songs s
                """
            )
            conn.execute("DROP TABLE songs")
            conn.execute("ALTER TABLE songs_v2 RENAME TO songs")
            if self._table_exists("folders"):
                conn.execute("DROP TABLE folders")
            for statement in INDEXES_V2:
                conn.execute(statement)
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys=ON")

    def _backup_v1(self) -> None:
        if self.path == ":memory:" or not os.path.exists(self.path):
            return
        backup = self.path + ".v1.bak"
        if os.path.exists(backup):
            return
        try:
            # 用 SQLite 备份 API，确保 WAL 中尚未 checkpoint 的数据也写进备份。
            target = sqlite3.connect(backup)
            try:
                self.conn.backup(target)
            finally:
                target.close()
        except (OSError, sqlite3.Error):
            pass

    # ---------------------------------------------------------------- 事务/收尾
    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def schema_version(self) -> int:
        try:
            row = self.conn.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.Error:
            return 1
        return int(row["value"]) if row else SCHEMA_VERSION
