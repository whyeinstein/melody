import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { DbHandle } from '../connection'

const EXTENSION_BY_MIME: Record<string, string> = {
  'image/jpeg': '.jpg',
  'image/jpg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
  'image/gif': '.gif',
  'image/bmp': '.bmp'
}

export interface CoverRef {
  id: number
  hash: string
  file: string
}

/**
 * 封面按内容哈希去重，文件落在 `<userData>/covers/<hash>.<ext>`。
 * 返回 null 表示该图片已经存在或写入失败，调用方继续使用已有封面。
 */
export function saveCover(
  db: DbHandle,
  coversDir: string,
  data: Uint8Array,
  mime: string | undefined,
  source: string
): CoverRef | null {
  if (data.byteLength === 0) return null
  const hash = createHash('sha1').update(data).digest('hex')
  const existing = db.prepare('SELECT id, hash, file FROM covers WHERE hash = ?').get<CoverRef>(hash)
  if (existing) return existing

  const normalizedMime = (mime ?? '').toLowerCase()
  const extension = EXTENSION_BY_MIME[normalizedMime] ?? '.bin'
  const fileName = `${hash}${extension}`
  const absolutePath = join(coversDir, fileName)

  try {
    if (!existsSync(coversDir)) mkdirSync(coversDir, { recursive: true })
    if (!existsSync(absolutePath)) writeFileSync(absolutePath, data)
  } catch {
    return null
  }

  const result = db
    .prepare('INSERT INTO covers(hash, file, mime, source) VALUES (?, ?, ?, ?)')
    .run(hash, fileName, mime ?? null, source)
  return { id: result.lastInsertRowid, hash, file: fileName }
}

export function getCoverFile(db: DbHandle, id: number): string | null {
  const row = db.prepare('SELECT file FROM covers WHERE id = ?').get<{ file: string }>(id)
  return row?.file ?? null
}
