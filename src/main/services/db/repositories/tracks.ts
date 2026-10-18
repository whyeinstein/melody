import type { Track, TrackPage, TrackQuery, TrackSortField } from '@shared/domain/types'
import { normalizeText, toLikePattern } from '@shared/text/normalize'
import type { DbHandle, SqlParam } from '../connection'

interface TrackRow {
  id: number
  path: string
  folder_id: number
  title: string
  artist: string | null
  album_artist: string | null
  album: string | null
  year: number | null
  genre: string | null
  track_no: number | null
  disc_no: number | null
  duration_ms: number | null
  bitrate: number | null
  sample_rate: number | null
  channels: number | null
  format: string | null
  codec: string | null
  size: number
  mtime_ms: number
  cover_id: number | null
  favorite: number
  play_count: number
  last_played_at: number | null
  rating: number
  added_at: number
  updated_at: number
  missing: number
}

export function mapTrackRow(row: TrackRow): Track {
  return {
    id: row.id,
    path: row.path,
    folderId: row.folder_id,
    title: row.title,
    artist: row.artist,
    albumArtist: row.album_artist,
    album: row.album,
    year: row.year,
    genre: row.genre,
    trackNo: row.track_no,
    discNo: row.disc_no,
    durationMs: row.duration_ms,
    bitrate: row.bitrate,
    sampleRate: row.sample_rate,
    channels: row.channels,
    format: row.format,
    codec: row.codec,
    size: row.size,
    mtimeMs: row.mtime_ms,
    coverId: row.cover_id,
    favorite: row.favorite === 1,
    playCount: row.play_count,
    lastPlayedAt: row.last_played_at,
    rating: row.rating,
    addedAt: row.added_at,
    updatedAt: row.updated_at,
    missing: row.missing === 1
  }
}

const SORT_COLUMNS: Record<TrackSortField, string> = {
  title: 'title_norm',
  artist: 'artist_norm',
  album: 'album_norm',
  duration: 'duration_ms',
  addedAt: 'added_at',
  year: 'year',
  trackNo: 'track_no'
}

const DEFAULT_LIMIT = 500
const MAX_LIMIT = 2000

export function queryTracks(db: DbHandle, query: TrackQuery): TrackPage {
  const where: string[] = ['missing = 0']
  const params: SqlParam[] = []

  if (query.folderId !== undefined) {
    where.push('folder_id = ?')
    params.push(query.folderId)
  }
  if (query.album) {
    where.push('album_norm = ?')
    params.push(normalizeText(query.album))
  }
  if (query.artist) {
    where.push('artist_norm = ?')
    params.push(normalizeText(query.artist))
  }
  if (query.genre) {
    where.push('genre_norm = ?')
    params.push(normalizeText(query.genre))
  }
  if (query.favorite) {
    where.push('favorite = 1')
  }
  if (query.search && query.search.trim()) {
    const like = toLikePattern(query.search)
    where.push("(title_norm LIKE ? ESCAPE '\\' OR artist_norm LIKE ? ESCAPE '\\' OR album_norm LIKE ? ESCAPE '\\')")
    params.push(like, like, like)
  }

  const whereSql = where.join(' AND ')
  const sortColumn = SORT_COLUMNS[query.sort ?? 'title'] ?? SORT_COLUMNS.title
  const direction = query.direction === 'desc' ? 'DESC' : 'ASC'
  const limit = Math.min(Math.max(query.limit ?? DEFAULT_LIMIT, 1), MAX_LIMIT)
  const offset = Math.max(query.offset ?? 0, 0)

  const totalRow = db.prepare(`SELECT COUNT(*) AS count FROM tracks WHERE ${whereSql}`).get<{ count: number }>(...params)

  const rows = db
    .prepare(`SELECT * FROM tracks WHERE ${whereSql} ORDER BY ${sortColumn} ${direction}, id ASC LIMIT ? OFFSET ?`)
    .all<TrackRow>(...params, limit, offset)

  return { items: rows.map(mapTrackRow), total: Number(totalRow?.count ?? 0) }
}

export function getTrack(db: DbHandle, id: number): Track | null {
  const row = db.prepare('SELECT * FROM tracks WHERE id = ?').get<TrackRow>(id)
  return row ? mapTrackRow(row) : null
}

export function getTrackPath(db: DbHandle, id: number): string | null {
  const row = db.prepare('SELECT path FROM tracks WHERE id = ? AND missing = 0').get<{ path: string }>(id)
  return row?.path ?? null
}

export function setFavorite(db: DbHandle, id: number, favorite: boolean): void {
  db.prepare('UPDATE tracks SET favorite = ?, updated_at = ? WHERE id = ?').run(favorite ? 1 : 0, Date.now(), id)
}

export function markPlayed(db: DbHandle, id: number, playedAt: number): void {
  db.transaction(() => {
    db.prepare('UPDATE tracks SET play_count = play_count + 1, last_played_at = ? WHERE id = ?').run(playedAt, id)
    db.prepare('INSERT INTO play_history(track_id, played_at) VALUES (?, ?)').run(id, playedAt)
  })
}

/* --------------------------------- 扫描写入 --------------------------------- */

export interface TrackWriteInput {
  path: string
  folderId: number
  title: string
  artist: string | null
  albumArtist: string | null
  album: string | null
  year: number | null
  genre: string | null
  trackNo: number | null
  discNo: number | null
  durationMs: number | null
  bitrate: number | null
  sampleRate: number | null
  channels: number | null
  format: string | null
  codec: string | null
  size: number
  mtimeMs: number
  coverId: number | null
}

export interface ExistingTrack {
  id: number
  size: number
  mtimeMs: number
  coverId: number | null
}

export function findTrackByPath(db: DbHandle, path: string): ExistingTrack | undefined {
  return db
    .prepare('SELECT id, size, mtime_ms AS mtimeMs, cover_id AS coverId FROM tracks WHERE path = ?')
    .get<ExistingTrack>(path)
}

export function insertTrack(db: DbHandle, input: TrackWriteInput, now: number): number {
  const result = db
    .prepare(
      `INSERT INTO tracks (
        path, folder_id, title, title_norm, artist, artist_norm, album_artist,
        album, album_norm, year, genre, genre_norm, track_no, disc_no,
        duration_ms, bitrate, sample_rate, channels, format, codec,
        size, mtime_ms, cover_id, favorite, play_count, rating,
        added_at, updated_at, missing
      ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, 0
      )`
    )
    .run(
      input.path,
      input.folderId,
      input.title,
      normalizeText(input.title),
      input.artist,
      normalizeText(input.artist),
      input.albumArtist,
      input.album,
      normalizeText(input.album),
      input.year,
      input.genre,
      normalizeText(input.genre),
      input.trackNo,
      input.discNo,
      input.durationMs,
      input.bitrate,
      input.sampleRate,
      input.channels,
      input.format,
      input.codec,
      input.size,
      input.mtimeMs,
      input.coverId,
      now,
      now
    )
  return result.lastInsertRowid
}

export function updateTrack(db: DbHandle, id: number, input: TrackWriteInput, now: number): void {
  db.prepare(
    `UPDATE tracks SET
      folder_id = ?, title = ?, title_norm = ?, artist = ?, artist_norm = ?,
      album_artist = ?, album = ?, album_norm = ?, year = ?, genre = ?, genre_norm = ?,
      track_no = ?, disc_no = ?, duration_ms = ?, bitrate = ?, sample_rate = ?, channels = ?,
      format = ?, codec = ?, size = ?, mtime_ms = ?, cover_id = ?, updated_at = ?, missing = 0
     WHERE id = ?`
  ).run(
    input.folderId,
    input.title,
    normalizeText(input.title),
    input.artist,
    normalizeText(input.artist),
    input.albumArtist,
    input.album,
    normalizeText(input.album),
    input.year,
    input.genre,
    normalizeText(input.genre),
    input.trackNo,
    input.discNo,
    input.durationMs,
    input.bitrate,
    input.sampleRate,
    input.channels,
    input.format,
    input.codec,
    input.size,
    input.mtimeMs,
    input.coverId,
    now,
    id
  )
}

/** 扫描期间记录「本次确实见到」的路径，用于把消失的文件标记为 missing。 */
export function markMissingFromSeen(db: DbHandle, folderId: number): number {
  const result = db
    .prepare(
      `UPDATE tracks SET missing = 1
       WHERE folder_id = ? AND missing = 0
         AND path NOT IN (SELECT path FROM scan_seen)`
    )
    .run(folderId)
  return result.changes
}

export function clearSeen(db: DbHandle): void {
  db.exec('DELETE FROM scan_seen')
}

export function rememberSeen(db: DbHandle, path: string): void {
  db.prepare('INSERT OR IGNORE INTO scan_seen(path) VALUES (?)').run(path)
}

export function ensureSeenTable(db: DbHandle): void {
  db.exec('CREATE TEMP TABLE IF NOT EXISTS scan_seen (path TEXT PRIMARY KEY)')
}
