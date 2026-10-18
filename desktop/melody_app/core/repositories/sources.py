"""音乐来源仓库：本地文件夹与远程库（远程当前仅登记，不参与扫描）。"""

from __future__ import annotations

import json
import os
import time

from ..db import Database
from ..models import Source


def _source_from_row(row) -> Source:
    try:
        config = json.loads(row["config"] or "{}")
    except (TypeError, ValueError):
        config = {}
    if not isinstance(config, dict):
        config = {}
    return Source(
        id=int(row["id"]),
        kind=str(row["kind"]),
        name=str(row["name"]),
        path=row["path"],
        config=config,
        enabled=bool(row["enabled"]),
        added_at=int(row["added_at"] or 0),
    )


class SourcesRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def conn(self):
        return self._db.conn

    def list(self, include_disabled: bool = True) -> list[Source]:
        sql = "SELECT * FROM sources"
        if not include_disabled:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY (kind = 'local') DESC, name COLLATE NOCASE"
        rows = self.conn.execute(sql).fetchall()
        return [_source_from_row(row) for row in rows]

    def get(self, source_id: int) -> Source | None:
        row = self.conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return _source_from_row(row) if row else None

    def find_local(self, path: str) -> Source | None:
        normalized = os.path.normpath(path)
        row = self.conn.execute(
            "SELECT * FROM sources WHERE kind = 'local' AND lower(path) = lower(?)",
            (normalized,),
        ).fetchone()
        return _source_from_row(row) if row else None

    def add_local(self, path: str) -> Source:
        normalized = os.path.normpath(path)
        existing = self.find_local(normalized)
        if existing is not None:
            if not existing.enabled:
                self.set_enabled(existing.id, True)
                existing.enabled = True
            return existing
        name = os.path.basename(normalized.rstrip("\\/")) or normalized
        cursor = self.conn.execute(
            "INSERT INTO sources(kind, name, path, config, enabled, added_at)"
            " VALUES('local', ?, ?, '{}', 1, ?)",
            (name, normalized, int(time.time() * 1000)),
        )
        self._db.commit()
        created = self.get(int(cursor.lastrowid))
        if created is None:  # pragma: no cover
            raise RuntimeError("创建本地来源失败")
        return created

    def add_remote(self, name: str, path: str, config: dict | None = None) -> Source:
        """登记远程来源（当前为占位，后续接入 WebDAV / Navidrome 等）。"""
        cursor = self.conn.execute(
            "INSERT INTO sources(kind, name, path, config, enabled, added_at)"
            " VALUES('remote', ?, ?, ?, 1, ?)",
            (
                name.strip() or "远程库",
                path.strip(),
                json.dumps(config or {}, ensure_ascii=False),
                int(time.time() * 1000),
            ),
        )
        self._db.commit()
        created = self.get(int(cursor.lastrowid))
        if created is None:  # pragma: no cover
            raise RuntimeError("创建远程来源失败")
        return created

    def set_enabled(self, source_id: int, enabled: bool) -> None:
        self.conn.execute(
            "UPDATE sources SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, source_id),
        )
        self._db.commit()

    def remove(self, source_id: int) -> None:
        self.conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        self._db.commit()

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM sources").fetchone()
        return int(row["c"] or 0) if row else 0
