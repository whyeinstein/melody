import type { Playlist } from '@shared/domain/types'
import type { DbHandle } from '../connection'

interface PlaylistRow {
  id: number
  name: string
  kind: string
  created_at: number
  updated_at: number
  track_count: number
}

function mapPlaylist(row: PlaylistRow): Playlist {
  return {
    id: row.id,
    name: row.name,
    kind: 'manual',
    trackCount: row.track_count,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  }
}

const SELECT_PLAYLISTS = `
  SELECT p.id, p.name, p.kind, p.created_at, p.updated_at,
         (SELECT COUNT(*) FROM playlist_items i WHERE i.playlist_id = p.id) AS track_count
  FROM playlists p
`

export function listPlaylists(db: DbHandle): Playlist[] {
  return db.prepare(`${SELECT_PLAYLISTS} ORDER BY p.created_at ASC`).all<PlaylistRow>().map(mapPlaylist)
}

export function getPlaylist(db: DbHandle, id: number): Playlist | undefined {
  const row = db.prepare(`${SELECT_PLAYLISTS} WHERE p.id = ?`).get<PlaylistRow>(id)
  return row ? mapPlaylist(row) : undefined
}

export function createPlaylist(db: DbHandle, name: string, now: number): Playlist {
  const result = db
    .prepare("INSERT INTO playlists(name, kind, created_at, updated_at) VALUES (?, 'manual', ?, ?)")
    .run(name, now, now)
  const created = getPlaylist(db, result.lastInsertRowid)
  if (!created) throw new Error('创建播放列表失败')
  return created
}

export function renamePlaylist(db: DbHandle, id: number, name: string, now: number): void {
  db.prepare('UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?').run(name, now, id)
}

export function deletePlaylist(db: DbHandle, id: number): void {
  db.prepare('DELETE FROM playlists WHERE id = ?').run(id)
}

export function listPlaylistTrackIds(db: DbHandle, playlistId: number): number[] {
  return db
    .prepare('SELECT track_id FROM playlist_items WHERE playlist_id = ? ORDER BY position ASC')
    .all<{ track_id: number }>(playlistId)
    .map((row) => row.track_id)
}

export function addTracksToPlaylist(db: DbHandle, playlistId: number, trackIds: number[], now: number): void {
  db.transaction(() => {
    const maxRow = db
      .prepare('SELECT COALESCE(MAX(position), -1) AS maxPosition FROM playlist_items WHERE playlist_id = ?')
      .get<{ maxPosition: number }>(playlistId)
    let position = (maxRow?.maxPosition ?? -1) + 1
    const insert = db.prepare('INSERT OR IGNORE INTO playlist_items(playlist_id, track_id, position, added_at) VALUES (?, ?, ?, ?)')
    for (const trackId of trackIds) {
      insert.run(playlistId, trackId, position, now)
      position += 1
    }
    db.prepare('UPDATE playlists SET updated_at = ? WHERE id = ?').run(now, playlistId)
  })
}

export function removeTracksFromPlaylist(db: DbHandle, playlistId: number, trackIds: number[], now: number): void {
  db.transaction(() => {
    const remove = db.prepare('DELETE FROM playlist_items WHERE playlist_id = ? AND track_id = ?')
    for (const trackId of trackIds) remove.run(playlistId, trackId)
    db.prepare('UPDATE playlists SET updated_at = ? WHERE id = ?').run(now, playlistId)
  })
}

export function reorderPlaylist(db: DbHandle, playlistId: number, orderedTrackIds: number[], now: number): void {
  db.transaction(() => {
    db.prepare('DELETE FROM playlist_items WHERE playlist_id = ?').run(playlistId)
    const insert = db.prepare('INSERT INTO playlist_items(playlist_id, track_id, position, added_at) VALUES (?, ?, ?, ?)')
    orderedTrackIds.forEach((trackId, index) => insert.run(playlistId, trackId, index, now))
    db.prepare('UPDATE playlists SET updated_at = ? WHERE id = ?').run(now, playlistId)
  })
}
