import type { DbHandle } from './connection'

/**
 * 迁移采用「顺序 SQL + meta.schema_version」，新增版本时只追加，不改旧条目。
 * 不使用 FTS5：1 万条规模的 LIKE + 归一化列已在 10ms 级，阶段 3 再评估。
 */
const INIT_SQL = `
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE folders (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  enabled INTEGER NOT NULL DEFAULT 1,
  added_at INTEGER NOT NULL
);

CREATE TABLE covers (
  id INTEGER PRIMARY KEY,
  hash TEXT NOT NULL UNIQUE,
  file TEXT NOT NULL,
  mime TEXT,
  width INTEGER,
  height INTEGER,
  source TEXT
);

CREATE TABLE tracks (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE COLLATE NOCASE,
  folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  title_norm TEXT NOT NULL,
  artist TEXT,
  artist_norm TEXT,
  album_artist TEXT,
  album TEXT,
  album_norm TEXT,
  year INTEGER,
  genre TEXT,
  genre_norm TEXT,
  track_no INTEGER,
  disc_no INTEGER,
  duration_ms INTEGER,
  bitrate INTEGER,
  sample_rate INTEGER,
  channels INTEGER,
  format TEXT,
  codec TEXT,
  size INTEGER NOT NULL,
  mtime_ms INTEGER NOT NULL,
  cover_id INTEGER REFERENCES covers(id) ON DELETE SET NULL,
  favorite INTEGER NOT NULL DEFAULT 0,
  play_count INTEGER NOT NULL DEFAULT 0,
  last_played_at INTEGER,
  rating INTEGER NOT NULL DEFAULT 0,
  added_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  missing INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_tracks_folder ON tracks(folder_id);
CREATE INDEX idx_tracks_artist ON tracks(artist_norm);
CREATE INDEX idx_tracks_album ON tracks(album_norm, album_artist);
CREATE INDEX idx_tracks_added ON tracks(added_at DESC);
CREATE INDEX idx_tracks_favorite ON tracks(favorite);
CREATE INDEX idx_tracks_genre ON tracks(genre_norm);

CREATE TABLE playlists (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'manual',
  query TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE playlist_items (
  playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  added_at INTEGER NOT NULL,
  PRIMARY KEY (playlist_id, position)
);

CREATE INDEX idx_playlist_items_track ON playlist_items(track_id);

CREATE TABLE play_history (
  id INTEGER PRIMARY KEY,
  track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  played_at INTEGER NOT NULL
);

CREATE INDEX idx_play_history_played ON play_history(played_at DESC);

CREATE TABLE scan_errors (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL,
  message TEXT NOT NULL,
  occurred_at INTEGER NOT NULL
);
`

export interface Migration {
  version: number
  sql: string
}

const MIGRATIONS: Migration[] = [{ version: 1, sql: INIT_SQL }]

export const LATEST_SCHEMA_VERSION = MIGRATIONS[MIGRATIONS.length - 1]?.version ?? 0

function readSchemaVersion(db: DbHandle): number {
  try {
    const row = db.prepare('SELECT value FROM meta WHERE key = ?').get<{ value: string }>('schema_version')
    return row ? Number(row.value) : 0
  } catch {
    return 0
  }
}

export function migrate(db: DbHandle): number {
  const current = readSchemaVersion(db)
  for (const migration of MIGRATIONS) {
    if (migration.version <= current) continue
    db.transaction(() => {
      db.exec(migration.sql)
      db.prepare('INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value').run(
        'schema_version',
        String(migration.version)
      )
    })
  }
  return LATEST_SCHEMA_VERSION
}
