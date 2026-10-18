import type { AlbumSummary, ArtistSummary, GenreSummary } from '@shared/domain/types'
import type { DbHandle } from '../connection'

export function listAlbums(db: DbHandle): AlbumSummary[] {
  return db
    .prepare(
      `SELECT
         album AS name,
         album_artist AS albumArtist,
         MAX(year) AS year,
         COUNT(*) AS trackCount,
         SUM(COALESCE(duration_ms, 0)) AS durationMs,
         (SELECT t2.cover_id FROM tracks t2
           WHERE t2.album_norm = t.album_norm
             AND t2.album_artist IS t.album_artist
             AND t2.cover_id IS NOT NULL
           LIMIT 1) AS coverId
       FROM tracks t
       WHERE missing = 0 AND album IS NOT NULL AND album <> ''
       GROUP BY album_norm, album_artist
       ORDER BY name COLLATE NOCASE`
    )
    .all<AlbumSummary>()
}

export function listArtists(db: DbHandle): ArtistSummary[] {
  return db
    .prepare(
      `SELECT
         artist AS name,
         COUNT(*) AS trackCount,
         COUNT(DISTINCT album_norm) AS albumCount
       FROM tracks
       WHERE missing = 0 AND artist IS NOT NULL AND artist <> ''
       GROUP BY artist_norm
       ORDER BY name COLLATE NOCASE`
    )
    .all<ArtistSummary>()
}

export function listGenres(db: DbHandle): GenreSummary[] {
  return db
    .prepare(
      `SELECT genre AS name, COUNT(*) AS trackCount
       FROM tracks
       WHERE missing = 0 AND genre IS NOT NULL AND genre <> ''
       GROUP BY genre_norm
       ORDER BY name COLLATE NOCASE`
    )
    .all<GenreSummary>()
}
