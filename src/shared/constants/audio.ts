/** 由 Chromium 原生解码、无需转码即可播放的扩展名。 */
export const NATIVE_AUDIO_EXTENSIONS = [
  '.mp3',
  '.flac',
  '.wav',
  '.ogg',
  '.oga',
  '.opus',
  '.m4a',
  '.aac'
] as const

/** 需要 ffmpeg 转码后播放的扩展名（阶段 2 实装）。 */
export const TRANSCODE_AUDIO_EXTENSIONS = [
  '.ape',
  '.wma',
  '.wv',
  '.dsf',
  '.dff',
  '.aiff',
  '.aif',
  '.alac',
  '.m4b',
  '.mka'
] as const

export const ALL_AUDIO_EXTENSIONS = [...NATIVE_AUDIO_EXTENSIONS, ...TRANSCODE_AUDIO_EXTENSIONS] as const

const NATIVE_SET: ReadonlySet<string> = new Set(NATIVE_AUDIO_EXTENSIONS)
const AUDIO_SET: ReadonlySet<string> = new Set(ALL_AUDIO_EXTENSIONS)

export function extensionOf(fileName: string): string {
  const dot = fileName.lastIndexOf('.')
  return dot === -1 ? '' : fileName.slice(dot).toLowerCase()
}

export function isAudioFile(fileName: string): boolean {
  return AUDIO_SET.has(extensionOf(fileName))
}

export function isNativelyPlayable(fileName: string): boolean {
  return NATIVE_SET.has(extensionOf(fileName))
}

const MIME_BY_EXTENSION: Readonly<Record<string, string>> = {
  '.mp3': 'audio/mpeg',
  '.flac': 'audio/flac',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.oga': 'audio/ogg',
  '.opus': 'audio/ogg',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.aiff': 'audio/aiff',
  '.aif': 'audio/aiff',
  '.wma': 'audio/x-ms-wma',
  '.ape': 'audio/x-ape',
  '.wv': 'audio/x-wavpack',
  '.dsf': 'audio/x-dsf',
  '.dff': 'audio/x-dff',
  '.mka': 'audio/x-matroska',
  '.m4b': 'audio/mp4',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.bmp': 'image/bmp',
  '.avif': 'image/avif'
}

export function mimeForExtension(ext: string): string {
  return MIME_BY_EXTENSION[ext.toLowerCase()] ?? 'application/octet-stream'
}
