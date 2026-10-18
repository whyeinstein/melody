import { z } from 'zod'

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

/**
 * 单一事实来源：每个频道声明请求与响应结构。
 * 新增频道时在这里追加，preload 白名单与主进程路由会同步获得类型约束。
 */
export const ipcContracts = {
  'app:info': { request: z.undefined(), response: AppInfoSchema }
} as const

export type IpcChannel = keyof typeof ipcContracts
export type IpcRequest<C extends IpcChannel> = z.infer<(typeof ipcContracts)[C]['request']>
export type IpcResponse<C extends IpcChannel> = z.infer<(typeof ipcContracts)[C]['response']>

export const IPC_CHANNELS = Object.keys(ipcContracts) as IpcChannel[]
