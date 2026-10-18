import { readdir } from 'node:fs/promises'
import { join } from 'node:path'
import { isAudioFile } from '@shared/constants/audio'

/** 不进入的目录：版本库、依赖、回收站与系统卷信息。 */
const SKIPPED_DIRECTORIES = new Set([
  '$recycle.bin',
  'system volume information',
  'node_modules',
  '.git',
  '.svn',
  '.hg'
])

export interface WalkOptions {
  signal?: AbortSignal
  onError?: (path: string, error: unknown) => void
}

/**
 * 迭代式遍历目录（避免深目录递归栈溢出），返回音频文件的绝对路径。
 * 不跟随符号链接、跳过隐藏目录与常见系统目录；权限错误计入 onError 后继续。
 */
export async function collectAudioFiles(root: string, options: WalkOptions = {}): Promise<string[]> {
  const files: string[] = []
  const pending: string[] = [root]

  while (pending.length > 0) {
    if (options.signal?.aborted) break
    const directory = pending.pop()
    if (!directory) break

    let entries
    try {
      entries = await readdir(directory, { withFileTypes: true })
    } catch (error) {
      options.onError?.(directory, error)
      continue
    }

    for (const entry of entries) {
      if (options.signal?.aborted) break
      const fullPath = join(directory, entry.name)
      if (entry.isSymbolicLink()) continue
      if (entry.isDirectory()) {
        const lower = entry.name.toLowerCase()
        if (SKIPPED_DIRECTORIES.has(lower) || entry.name.startsWith('.')) continue
        pending.push(fullPath)
        continue
      }
      if (entry.isFile() && isAudioFile(entry.name)) {
        files.push(fullPath)
      }
    }
  }

  return files
}
