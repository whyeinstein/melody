import { execFile } from 'node:child_process'
import { existsSync } from 'node:fs'
import { delimiter, join } from 'node:path'
import { promisify } from 'node:util'
import type { FfmpegProbe } from '@shared/ipc/contracts'
import { errorMessage } from '../logging'

const execFileAsync = promisify(execFile)

function findOnPath(executable: string): string | undefined {
  const pathValue = process.env['PATH'] ?? ''
  const names = process.platform === 'win32' ? [`${executable}.exe`, executable] : [executable]
  for (const dir of pathValue.split(delimiter)) {
    if (!dir) continue
    for (const name of names) {
      const candidate = join(dir, name)
      if (existsSync(candidate)) return candidate
    }
  }
  return undefined
}

/** 探测 ffmpeg：阶段 2 的转码后端依赖它，设置页会展示结果。 */
export async function probeFfmpeg(): Promise<FfmpegProbe> {
  const path = findOnPath('ffmpeg')
  if (!path) {
    return { found: false, detail: '未在 PATH 中找到 ffmpeg' }
  }
  try {
    const { stdout } = await execFileAsync(path, ['-version'], { timeout: 5000, windowsHide: true })
    const firstLine = stdout.split(/\r?\n/, 1)[0]?.trim() ?? ''
    const version = /version\s+(\S+)/.exec(firstLine)?.[1]
    return { found: true, path, version, detail: firstLine }
  } catch (error) {
    return { found: true, path, detail: `无法执行 ffmpeg: ${errorMessage(error)}` }
  }
}
