import { z } from 'zod'

/** 应用配置：只放界面与播放偏好；音乐文件夹以数据库为准。 */
export const AppConfigSchema = z.object({
  version: z.literal(1),
  theme: z.enum(['dark', 'light', 'system']).default('dark'),
  language: z.enum(['zh-CN', 'en-US']).default('zh-CN'),
  volume: z.number().min(0).max(1).default(0.8),
  repeat: z.enum(['off', 'all', 'one']).default('off'),
  shuffle: z.boolean().default(false),
  ffmpegPath: z.string().nullable().default(null)
})

export type AppConfig = z.infer<typeof AppConfigSchema>
export type AppConfigPatch = Partial<Omit<AppConfig, 'version'>>

export const DEFAULT_CONFIG: AppConfig = AppConfigSchema.parse({ version: 1 })
