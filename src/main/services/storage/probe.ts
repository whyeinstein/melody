import type { StorageProbe } from '@shared/ipc/contracts'
import { errorMessage, logInfo } from '../logging'

interface StatementLike {
  run(...params: unknown[]): unknown
  get(...params: unknown[]): unknown
}

interface DatabaseLike {
  exec(sql: string): void
  prepare(sql: string): StatementLike
  close(): void
}

interface SqliteModuleLike {
  DatabaseSync: new (location: string) => DatabaseLike
}

/**
 * 阶段 0 的存储选型闸门：
 * Electron 主进程若能使用内置 node:sqlite，就零原生依赖落库；
 * 否则记录原因，后续降级 better-sqlite3 或 sql.js（上层只依赖 DbHandle 接口）。
 */
export async function probeStorage(): Promise<StorageProbe> {
  try {
    const mod = (await import('node:sqlite')) as unknown as SqliteModuleLike
    const db = new mod.DatabaseSync(':memory:')
    try {
      db.exec('CREATE TABLE probe(value TEXT NOT NULL)')
      db.prepare('INSERT INTO probe(value) VALUES (?)').run('ok')
      const row = db.prepare('SELECT value FROM probe LIMIT 1').get() as { value?: string } | undefined
      if (row?.value !== 'ok') {
        return { engine: 'none', ok: false, detail: 'node:sqlite 可用但自检结果异常' }
      }
      return { engine: 'node:sqlite', ok: true }
    } finally {
      db.close()
    }
  } catch (error) {
    const detail = errorMessage(error)
    logInfo('node:sqlite 不可用:', detail)
    return { engine: 'none', ok: false, detail }
  }
}
