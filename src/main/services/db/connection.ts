import type { DatabaseSync } from 'node:sqlite'
import { errorMessage } from '../logging'

export type SqlParam = string | number | null | Uint8Array

export interface StatementAdapter {
  run(...params: SqlParam[]): { changes: number; lastInsertRowid: number }
  get<T>(...params: SqlParam[]): T | undefined
  all<T>(...params: SqlParam[]): T[]
}

export interface DbHandle {
  exec(sql: string): void
  prepare(sql: string): StatementAdapter
  transaction<T>(fn: () => T): T
  close(): void
}

class NodeSqliteHandle implements DbHandle {
  constructor(private readonly db: DatabaseSync) {}

  exec(sql: string): void {
    this.db.exec(sql)
  }

  prepare(sql: string): StatementAdapter {
    const statement = this.db.prepare(sql)
    return {
      run: (...params: SqlParam[]) => {
        const result = statement.run(...params)
        return {
          changes: Number(result.changes ?? 0),
          lastInsertRowid: Number(result.lastInsertRowid ?? 0)
        }
      },
      get: <T>(...params: SqlParam[]) => statement.get(...params) as T | undefined,
      all: <T>(...params: SqlParam[]) => statement.all(...params) as T[]
    }
  }

  transaction<T>(fn: () => T): T {
    this.db.exec('BEGIN IMMEDIATE')
    try {
      const result = fn()
      this.db.exec('COMMIT')
      return result
    } catch (error) {
      try {
        this.db.exec('ROLLBACK')
      } catch {
        // 回滚失败时保留原始错误
      }
      throw error
    }
  }

  close(): void {
    this.db.close()
  }
}

/**
 * 打开数据库并应用基础 pragma。
 * 选型见 docs/decisions/0001-storage.md：优先 Electron 内置 node:sqlite。
 */
export async function openDatabase(filePath: string): Promise<DbHandle> {
  const module = await import('node:sqlite')
  const db = new module.DatabaseSync(filePath)
  const handle = new NodeSqliteHandle(db)
  handle.exec('PRAGMA journal_mode = WAL')
  handle.exec('PRAGMA foreign_keys = ON')
  handle.exec('PRAGMA synchronous = NORMAL')
  return handle
}

export function describeDbError(error: unknown): string {
  return errorMessage(error)
}
