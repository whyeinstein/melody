import type { LibraryFolder } from '@shared/domain/types'
import type { DbHandle } from '../connection'

interface FolderRow {
  id: number
  path: string
  enabled: number
  added_at: number
  track_count: number
}

function mapFolder(row: FolderRow): LibraryFolder {
  return {
    id: row.id,
    path: row.path,
    enabled: row.enabled === 1,
    addedAt: row.added_at,
    trackCount: row.track_count
  }
}

export function listFolders(db: DbHandle): LibraryFolder[] {
  const rows = db
    .prepare(
      `SELECT f.id, f.path, f.enabled, f.added_at,
              (SELECT COUNT(*) FROM tracks t WHERE t.folder_id = f.id AND t.missing = 0) AS track_count
       FROM folders f
       ORDER BY f.path COLLATE NOCASE`
    )
    .all<FolderRow>()
  return rows.map(mapFolder)
}

export function getFolder(db: DbHandle, id: number): LibraryFolder | undefined {
  const row = db
    .prepare(
      `SELECT f.id, f.path, f.enabled, f.added_at,
              (SELECT COUNT(*) FROM tracks t WHERE t.folder_id = f.id AND t.missing = 0) AS track_count
       FROM folders f WHERE f.id = ?`
    )
    .get<FolderRow>(id)
  return row ? mapFolder(row) : undefined
}

export function findFolderByPath(db: DbHandle, path: string): LibraryFolder | undefined {
  const row = db
    .prepare(
      `SELECT f.id, f.path, f.enabled, f.added_at,
              (SELECT COUNT(*) FROM tracks t WHERE t.folder_id = f.id AND t.missing = 0) AS track_count
       FROM folders f WHERE f.path = ? COLLATE NOCASE`
    )
    .get<FolderRow>(path)
  return row ? mapFolder(row) : undefined
}

export function addFolder(db: DbHandle, path: string, now: number): LibraryFolder {
  const existing = findFolderByPath(db, path)
  if (existing) return existing
  const result = db.prepare('INSERT INTO folders(path, enabled, added_at) VALUES (?, 1, ?)').run(path, now)
  const created = getFolder(db, result.lastInsertRowid)
  if (!created) throw new Error('创建音乐文件夹失败')
  return created
}

export function removeFolder(db: DbHandle, id: number): void {
  db.prepare('DELETE FROM folders WHERE id = ?').run(id)
}

export function listEnabledFolderPaths(db: DbHandle): { id: number; path: string }[] {
  return db
    .prepare('SELECT id, path FROM folders WHERE enabled = 1 ORDER BY path COLLATE NOCASE')
    .all<{ id: number; path: string }>()
}
