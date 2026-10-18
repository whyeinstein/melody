import { parseFile } from 'music-metadata'
import { extensionOf } from '@shared/constants/audio'

export interface ParsedPicture {
  data: Uint8Array
  mime?: string
}

export interface ParsedTrack {
  title: string | null
  artist: string | null
  albumArtist: string | null
  album: string | null
  year: number | null
  genre: string | null
  trackNo: number | null
  discNo: number | null
  durationMs: number | null
  bitrate: number | null
  sampleRate: number | null
  channels: number | null
  format: string | null
  codec: string | null
  picture: ParsedPicture | null
}

function firstOrNull(values: string[] | undefined): string | null {
  const value = values?.find((item) => item.trim().length > 0)
  return value ? value.trim() : null
}

function numberOrNull(value: number | null | undefined): number | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null
  return Math.round(value)
}

/** 读取单个音频文件的标签与封面；解析失败抛错，由扫描器计入失败数。 */
export async function readMetadata(filePath: string): Promise<ParsedTrack> {
  const metadata = await parseFile(filePath, { duration: true, skipCovers: false })
  const common = metadata.common
  const format = metadata.format

  const picture = common.picture?.[0]

  return {
    title: common.title?.trim() || null,
    artist: firstOrNull(common.artists) ?? common.artist?.trim() ?? null,
    albumArtist: common.albumartist?.trim() ?? null,
    album: common.album?.trim() || null,
    year: numberOrNull(common.year),
    genre: firstOrNull(common.genre),
    trackNo: numberOrNull(common.track?.no),
    discNo: numberOrNull(common.disk?.no),
    durationMs: format.duration === undefined ? null : Math.round(format.duration * 1000),
    bitrate: numberOrNull(format.bitrate),
    sampleRate: numberOrNull(format.sampleRate),
    channels: numberOrNull(format.numberOfChannels),
    format: extensionOf(filePath).replace('.', '') || format.container || null,
    codec: format.codec ?? null,
    picture: picture ? { data: picture.data, mime: picture.format } : null
  }
}
