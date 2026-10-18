export interface FilenameHints {
  artist?: string
  title: string
  trackNo?: number
}

const TRAILING_BRACKETS = /\s*[([（【][^)）】]*[)）】]\s*$/g

/**
 * 从文件名推断标签，仅在缺少内嵌元数据时兜底：
 *   01 - Artist - Title
 *   Artist - Title
 *   01. Title / 01 Title
 *   Title
 */
export function inferFromFilename(fileName: string): FilenameHints {
  const withoutExtension = fileName.replace(/\.[^.]+$/, '').trim()
  if (!withoutExtension) return { title: fileName }

  let working = withoutExtension.replace(TRAILING_BRACKETS, '').trim() || withoutExtension

  let trackNo: number | undefined
  const trackMatch = /^(\d{1,3})[\s._-]+(.*)$/.exec(working)
  if (trackMatch?.[1] && trackMatch[2]) {
    const parsed = Number.parseInt(trackMatch[1], 10)
    if (Number.isFinite(parsed)) {
      trackNo = parsed
      working = trackMatch[2].trim()
    }
  }

  const parts = working.split(/\s+-\s+/)
  if (parts.length >= 2) {
    const artist = parts[0]?.trim()
    const title = parts.slice(1).join(' - ').trim()
    if (artist && title) {
      return trackNo === undefined ? { artist, title } : { artist, title, trackNo }
    }
  }

  return trackNo === undefined ? { title: working } : { title: working, trackNo }
}
