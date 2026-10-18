import { existsSync, readFileSync } from 'node:fs'
import { stat } from 'node:fs/promises'
import { basename, dirname, extname, join } from 'node:path'
import { EMPTY_SCAN_PROGRESS, type ScanProgress } from '@shared/domain/types'
import type { DbHandle } from '../db/connection'
import { saveCover } from '../db/repositories/covers'
import { listEnabledFolderPaths } from '../db/repositories/folders'
import {
  clearSeen,
  ensureSeenTable,
  findTrackByPath,
  insertTrack,
  markMissingFromSeen,
  rememberSeen,
  updateTrack,
  type TrackWriteInput
} from '../db/repositories/tracks'
import { errorMessage } from '../logging'
import { inferFromFilename } from './filename'
import { readMetadata } from './metadata'
import { collectAudioFiles } from './walk'

export interface ScannerOptions {
  db: DbHandle
  coversDir: string
  onProgress?: (progress: ScanProgress) => void
  concurrency?: number
}

const PROGRESS_INTERVAL_MS = 100

/**
 * 音乐库扫描器：遍历已注册文件夹、增量解析标签、抽取封面、标记消失文件。
 * 扫描串行执行；并发只用于单文件的 IO/解析，写库仍是同步语句。
 */
export class LibraryScanner {
  private progress: ScanProgress = { ...EMPTY_SCAN_PROGRESS }
  private controller: AbortController | null = null
  private lastEmit = 0
  private running = false
  private readonly folderCoverCache = new Map<string, string | null>()

  constructor(private readonly options: ScannerOptions) {
    ensureSeenTable(options.db)
  }

  getProgress(): ScanProgress {
    return { ...this.progress }
  }

  isRunning(): boolean {
    return this.running
  }

  cancel(): void {
    this.controller?.abort()
  }

  async scan(folders?: { id: number; path: string }[]): Promise<ScanProgress> {
    if (this.running) return this.getProgress()

    const db = this.options.db
    const targets = folders ?? listEnabledFolderPaths(db)
    const startedAt = Date.now()

    this.running = true
    this.controller = new AbortController()
    const signal = this.controller.signal
    this.progress = {
      ...EMPTY_SCAN_PROGRESS,
      state: 'scanning',
      folders: targets.length,
      startedAt
    }
    this.emit(true)

    try {
      for (const folder of targets) {
        if (signal.aborted) break
        this.progress.currentPath = folder.path
        this.emit(true)

        clearSeen(db)
        const files = await collectAudioFiles(folder.path, {
          signal,
          onError: (path, error) => this.recordError(path, error)
        })

        await this.processFiles(folder.id, files, signal)

        if (!signal.aborted) {
          this.progress.removed += markMissingFromSeen(db, folder.id)
          this.emit(true)
        }
      }
      this.progress.state = signal.aborted ? 'cancelled' : 'done'
    } catch (error) {
      this.progress.state = 'error'
      this.progress.message = errorMessage(error)
    } finally {
      this.progress.finishedAt = Date.now()
      this.progress.currentPath = undefined
      this.running = false
      this.controller = null
      this.emit(true)
    }

    return this.getProgress()
  }

  private async processFiles(folderId: number, files: string[], signal: AbortSignal): Promise<void> {
    const concurrency = Math.max(1, Math.min(this.options.concurrency ?? 4, 8))
    let cursor = 0

    const worker = async (): Promise<void> => {
      while (!signal.aborted) {
        const index = cursor
        cursor += 1
        const file = files[index]
        if (!file) return
        await this.processFile(folderId, file)
      }
    }

    await Promise.all(Array.from({ length: Math.min(concurrency, files.length || 1) }, worker))
  }

  private async processFile(folderId: number, filePath: string): Promise<void> {
    const db = this.options.db
    this.progress.visited += 1

    try {
      const stats = await stat(filePath)
      const mtimeMs = Math.round(stats.mtimeMs)
      const existing = findTrackByPath(db, filePath)
      rememberSeen(db, filePath)

      // 未变化则跳过解析，保证增量扫描的开销只与新增/修改文件相关。
      if (existing && existing.size === stats.size && existing.mtimeMs === mtimeMs) {
        return
      }

      const parsed = await readMetadata(filePath)
      const hints = inferFromFilename(basename(filePath))

      let coverId = existing?.coverId ?? null
      if (parsed.picture) {
        const cover = saveCover(db, this.options.coversDir, parsed.picture.data, parsed.picture.mime, filePath)
        if (cover) coverId = cover.id
      } else if (coverId === null) {
        const folderCover = this.findFolderCover(filePath)
        if (folderCover) {
          try {
            const data = readFileSync(folderCover)
            const mime = extname(folderCover).toLowerCase() === '.png' ? 'image/png' : 'image/jpeg'
            const cover = saveCover(db, this.options.coversDir, data, mime, folderCover)
            if (cover) coverId = cover.id
          } catch {
            // 文件夹封面读取失败时保持无封面
          }
        }
      }

      const input: TrackWriteInput = {
        path: filePath,
        folderId,
        title: parsed.title ?? hints.title,
        artist: parsed.artist ?? hints.artist ?? null,
        albumArtist: parsed.albumArtist,
        album: parsed.album,
        year: parsed.year,
        genre: parsed.genre,
        trackNo: parsed.trackNo ?? hints.trackNo ?? null,
        discNo: parsed.discNo,
        durationMs: parsed.durationMs,
        bitrate: parsed.bitrate,
        sampleRate: parsed.sampleRate,
        channels: parsed.channels,
        format: parsed.format,
        codec: parsed.codec,
        size: stats.size,
        mtimeMs,
        coverId
      }

      const now = Date.now()
      if (existing) {
        updateTrack(db, existing.id, input, now)
        this.progress.updated += 1
      } else {
        insertTrack(db, input, now)
        this.progress.added += 1
      }
      this.progress.parsed += 1
    } catch (error) {
      this.recordError(filePath, error)
    } finally {
      this.emit()
    }
  }

  /** 同目录下常见的封面文件名，命中后缓存，避免每个文件都探测磁盘。 */
  private findFolderCover(filePath: string): string | null {
    const directory = dirname(filePath)
    const cached = this.folderCoverCache.get(directory)
    if (cached !== undefined) return cached

    let found: string | null = null
    for (const name of ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'front.jpg', 'front.png']) {
      const candidate = join(directory, name)
      if (existsSync(candidate)) {
        found = candidate
        break
      }
    }
    this.folderCoverCache.set(directory, found)
    return found
  }

  private recordError(path: string, error: unknown): void {
    const message = errorMessage(error)
    this.progress.failed += 1
    try {
      this.options.db
        .prepare('INSERT INTO scan_errors(path, message, occurred_at) VALUES (?, ?, ?)')
        .run(path, message, Date.now())
    } catch {
      // 扫描错误记录失败不应中断扫描
    }
    this.emit()
  }

  private emit(force = false): void {
    const now = Date.now()
    if (!force && now - this.lastEmit < PROGRESS_INTERVAL_MS) return
    this.lastEmit = now
    this.options.onProgress?.(this.getProgress())
  }
}
