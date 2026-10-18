import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { app } from 'electron'
import { broadcast } from '../ipc/events'
import { ConfigStore } from './config/store'
import { openDatabase, type DbHandle } from './db/connection'
import { migrate } from './db/migrations'
import { getCoverFile } from './db/repositories/covers'
import { getTrackPath } from './db/repositories/tracks'
import { LibraryScanner } from './library/scanner'
import { createMediaServer, type MediaServerHandle } from './media/server'

export interface AppPaths {
  userData: string
  dbFile: string
  coversDir: string
  configFile: string
  logsDir: string
}

export interface AppContext {
  paths: AppPaths
  db: DbHandle
  config: ConfigStore
  scanner: LibraryScanner
  media: MediaServerHandle
  dispose(): Promise<void>
}

function resolvePaths(): AppPaths {
  const userData = app.getPath('userData')
  return {
    userData,
    dbFile: join(userData, 'melody.db'),
    coversDir: join(userData, 'covers'),
    configFile: join(userData, 'config.json'),
    logsDir: join(userData, 'logs')
  }
}

/** 应用级服务容器：数据库、配置、扫描器、媒体服务在窗口创建前初始化一次。 */
export async function createAppContext(): Promise<AppContext> {
  const paths = resolvePaths()
  mkdirSync(paths.userData, { recursive: true })
  mkdirSync(paths.coversDir, { recursive: true })
  mkdirSync(paths.logsDir, { recursive: true })

  const db = await openDatabase(paths.dbFile)
  migrate(db)

  const config = ConfigStore.load(paths.configFile)

  const scanner = new LibraryScanner({
    db,
    coversDir: paths.coversDir,
    onProgress: (progress) => broadcast('scan:progress', progress)
  })

  const media = await createMediaServer({
    getTrackPath: async (trackId) => getTrackPath(db, trackId),
    getCoverPath: async (coverId) => {
      const file = getCoverFile(db, coverId)
      return file ? join(paths.coversDir, file) : null
    }
  })

  return {
    paths,
    db,
    config,
    scanner,
    media,
    async dispose() {
      await media.close().catch(() => undefined)
      db.close()
    }
  }
}
