import { spawnSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

export interface FixtureTrackOptions {
  format: 'mp3' | 'flac' | 'ogg' | 'wav'
  title: string
  artist: string
  album: string
  trackNo?: number
  genre?: string
  durationSeconds?: number
}

const ENCODER_BY_FORMAT: Record<FixtureTrackOptions['format'], string[]> = {
  mp3: ['-c:a', 'libmp3lame', '-q:a', '9'],
  flac: ['-c:a', 'flac', '-compression_level', '8'],
  ogg: ['-c:a', 'libvorbis', '-q:a', '2'],
  wav: ['-c:a', 'pcm_s16le']
}

export function hasFfmpeg(): boolean {
  return spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0
}

/** 用 ffmpeg 合成一个带标签的短音频文件，返回绝对路径。 */
export function writeFixtureTrack(directory: string, options: FixtureTrackOptions): string {
  mkdirSync(directory, { recursive: true })
  const fileName = `${String(options.trackNo ?? 1).padStart(2, '0')} - ${options.artist} - ${options.title}.${options.format}`
  const target = join(directory, fileName)

  const args = [
    '-y',
    '-f',
    'lavfi',
    '-i',
    `sine=frequency=440:duration=${options.durationSeconds ?? 1}`,
    ...ENCODER_BY_FORMAT[options.format],
    '-metadata',
    `title=${options.title}`,
    '-metadata',
    `artist=${options.artist}`,
    '-metadata',
    `album=${options.album}`,
    '-metadata',
    `album_artist=${options.artist}`,
    '-metadata',
    `track=${options.trackNo ?? 1}`,
    '-metadata',
    `genre=${options.genre ?? 'Ambient'}`,
    target
  ]

  const result = spawnSync('ffmpeg', args, { stdio: 'ignore' })
  if (result.status !== 0) throw new Error(`生成测试音频失败: ${target}`)
  return target
}
