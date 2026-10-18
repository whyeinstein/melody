import { z } from 'zod'
import { AppConfigSchema } from '../config/schema'
import type {
  AlbumSummary,
  ArtistSummary,
  GenreSummary,
  LibraryFolder,
  MediaSession,
  Playlist,
  ScanProgress,
  Track,
  TrackPage,
  TrackQuery
} from '../domain/types'

export const StorageEngineSchema = z.enum(['node:sqlite', 'better-sqlite3', 'sql.js', 'none'])
export type StorageEngine = z.infer<typeof StorageEngineSchema>

export const StorageProbeSchema = z.object({
  engine: StorageEngineSchema,
  ok: z.boolean(),
  detail: z.string().optional()
})
export type StorageProbe = z.infer<typeof StorageProbeSchema>

export const FfmpegProbeSchema = z.object({
  found: z.boolean(),
  path: z.string().optional(),
  version: z.string().optional(),
  detail: z.string().optional()
})
export type FfmpegProbe = z.infer<typeof FfmpegProbeSchema>

export const AppInfoSchema = z.object({
  name: z.string(),
  version: z.string(),
  electron: z.string(),
  chrome: z.string(),
  node: z.string(),
  platform: z.string(),
  arch: z.string(),
  isPackaged: z.boolean(),
  userDataPath: z.string(),
  storage: StorageProbeSchema,
  ffmpeg: FfmpegProbeSchema
})
export type AppInfo = z.infer<typeof AppInfoSchema>

export const IpcErrorSchema = z.object({
  code: z.string(),
  message: z.string()
})
export type IpcError = z.infer<typeof IpcErrorSchema>

export type IpcResult<T> = { ok: true; data: T } | { ok: false; error: IpcError }

/* ---------------------------------- 请求结构 --------------------------------- */

export const TrackQuerySchema = z.object({
  folderId: z.number().int().positive().optional(),
  album: z.string().min(1).optional(),
  artist: z.string().min(1).optional(),
  genre: z.string().min(1).optional(),
  favorite: z.boolean().optional(),
  search: z.string().max(200).optional(),
  sort: z
    .enum(['title', 'artist', 'album', 'duration', 'addedAt', 'year', 'trackNo'])
    .optional(),
  direction: z.enum(['asc', 'desc']).optional(),
  offset: z.number().int().min(0).max(1_000_000).optional(),
  limit: z.number().int().min(1).max(2000).optional()
}) satisfies z.ZodType<TrackQuery>

export const AppConfigPatchSchema = AppConfigSchema.omit({ version: true }).partial()

/* ------------------------------- 频道契约（类型） ------------------------------ */

export interface IpcRequestMap {
  'app:info': undefined
  'config:get': undefined
  'config:set': Partial<Omit<z.infer<typeof AppConfigSchema>, 'version'>>
  'library:chooseFolder': undefined
  'library:addFolder': { path: string }
  'library:removeFolder': { id: number }
  'library:listFolders': undefined
  'library:startScan': undefined
  'library:cancelScan': undefined
  'library:scanStatus': undefined
  'tracks:query': TrackQuery
  'tracks:get': { id: number }
  'tracks:setFavorite': { id: number; favorite: boolean }
  'tracks:markPlayed': { id: number }
  'albums:list': undefined
  'artists:list': undefined
  'genres:list': undefined
  'playlists:list': undefined
  'media:session': undefined
}

export interface IpcResponseMap {
  'app:info': AppInfo
  'config:get': z.infer<typeof AppConfigSchema>
  'config:set': z.infer<typeof AppConfigSchema>
  'library:chooseFolder': string[]
  'library:addFolder': LibraryFolder
  'library:removeFolder': void
  'library:listFolders': LibraryFolder[]
  'library:startScan': ScanProgress
  'library:cancelScan': void
  'library:scanStatus': ScanProgress
  'tracks:query': TrackPage
  'tracks:get': Track | null
  'tracks:setFavorite': void
  'tracks:markPlayed': void
  'albums:list': AlbumSummary[]
  'artists:list': ArtistSummary[]
  'genres:list': GenreSummary[]
  'playlists:list': Playlist[]
  'media:session': MediaSession
}

export type IpcChannel = keyof IpcRequestMap
export type IpcRequest<C extends IpcChannel> = IpcRequestMap[C]
export type IpcResponse<C extends IpcChannel> = IpcResponseMap[C]

/** 主进程 → 渲染进程的推送事件。 */
export interface IpcEventMap {
  'scan:progress': ScanProgress
}

export type IpcEventChannel = keyof IpcEventMap

export const IPC_EVENT_CHANNELS: IpcEventChannel[] = ['scan:progress']

/** 需要运行时校验的请求结构；未列出的频道视为无参数。 */
export const ipcRequestSchemas: Partial<Record<IpcChannel, z.ZodType>> = {
  'config:set': AppConfigPatchSchema,
  'library:addFolder': z.object({ path: z.string().min(1) }),
  'library:removeFolder': z.object({ id: z.number().int().positive() }),
  'tracks:query': TrackQuerySchema,
  'tracks:get': z.object({ id: z.number().int().positive() }),
  'tracks:setFavorite': z.object({ id: z.number().int().positive(), favorite: z.boolean() }),
  'tracks:markPlayed': z.object({ id: z.number().int().positive() })
}

export const IPC_CHANNELS: IpcChannel[] = [
  'app:info',
  'config:get',
  'config:set',
  'library:chooseFolder',
  'library:addFolder',
  'library:removeFolder',
  'library:listFolders',
  'library:startScan',
  'library:cancelScan',
  'library:scanStatus',
  'tracks:query',
  'tracks:get',
  'tracks:setFavorite',
  'tracks:markPlayed',
  'albums:list',
  'artists:list',
  'genres:list',
  'playlists:list',
  'media:session'
]
