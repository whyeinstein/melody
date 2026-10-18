import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { AppConfigSchema, DEFAULT_CONFIG, type AppConfig, type AppConfigPatch } from '@shared/config/schema'
import { logWarn } from '../logging'

/**
 * 配置文件读写：JSON + 原子替换（先写 .tmp 再 rename），
 * 损坏或字段不合法时回退到默认配置而不是让应用起不来。
 */
export class ConfigStore {
  private config: AppConfig

  private constructor(
    private readonly filePath: string,
    config: AppConfig
  ) {
    this.config = config
  }

  static load(filePath: string): ConfigStore {
    if (existsSync(filePath)) {
      try {
        const raw: unknown = JSON.parse(readFileSync(filePath, 'utf8'))
        const parsed = AppConfigSchema.safeParse(raw)
        if (parsed.success) return new ConfigStore(filePath, parsed.data)
        logWarn('配置文件字段不合法，已回退默认值:', parsed.error.message)
      } catch (error) {
        logWarn('配置文件读取失败，已回退默认值:', error)
      }
    }
    const store = new ConfigStore(filePath, { ...DEFAULT_CONFIG })
    store.persist()
    return store
  }

  get(): AppConfig {
    return { ...this.config }
  }

  update(patch: AppConfigPatch): AppConfig {
    this.config = AppConfigSchema.parse({ ...this.config, ...patch, version: 1 })
    this.persist()
    return this.get()
  }

  private persist(): void {
    const directory = dirname(this.filePath)
    if (!existsSync(directory)) mkdirSync(directory, { recursive: true })
    const temporary = `${this.filePath}.tmp`
    writeFileSync(temporary, `${JSON.stringify(this.config, null, 2)}\n`, 'utf8')
    renameSync(temporary, this.filePath)
  }
}
