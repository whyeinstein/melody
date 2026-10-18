/** 音乐库领域模型（主进程与渲染进程共用）。 */

export interface Track {
  id: number
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
  favorite: boolean
  playCount: number
  lastPlayedAt: number | null
  rating: number
  addedAt: number
  updatedAt: number
  missing: boolean
}

export type TrackSortField =
  | 'title'
  | 'artist'
  | 'album'
  | 'duration'
  | 'addedAt'
  | 'year'
  | 'trackNo'

export interface TrackQuery {
  folderId?: number
  album?: string
  artist?: string
  genre?: string
  favorite?: boolean
  search?: string
  sort?: TrackSortField
  direction?: 'asc' | 'desc'
  offset?: number
  limit?: number
}

export interface TrackPage {
  items: Track[]
  total: number
}

export interface AlbumSummary {
  name: string
  albumArtist: string | null
  year: number | null
  trackCount: number
  durationMs: number
  coverId: number | null
}

export interface ArtistSummary {
  name: string
  trackCount: number
  albumCount: number
}

export interface GenreSummary {
  name: string
  trackCount: number
}

export interface LibraryFolder {
  id: number
  path: string
  enabled: boolean
  addedAt: number
  trackCount: number
}

export type ScanState = 'idle' | 'scanning' | 'done' | 'cancelled' | 'error'

export interface ScanProgress {
  state: ScanState
  folders: number
  visited: number
  parsed: number
  added: number
  updated: number
  removed: number
  failed: number
  currentPath?: string
  startedAt?: number
  finishedAt?: number
  message?: string
}

export interface Playlist {
  id: number
  name: string
  kind: 'manual'
  trackCount: number
  createdAt: number
  updatedAt: number
}

export interface PlaylistItem {
  playlistId: number
  trackId: number
  position: number
  addedAt: number
}

export interface MediaSession {
  baseUrl: string
  token: string
}

export const EMPTY_SCAN_PROGRESS: ScanProgress = {
  state: 'idle',
  folders: 0,
  visited: 0,
  parsed: 0,
  added: 0,
  updated: 0,
  removed: 0,
  failed: 0
}
