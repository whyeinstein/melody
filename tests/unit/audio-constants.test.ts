import { describe, expect, it } from 'vitest'
import {
  ALL_AUDIO_EXTENSIONS,
  extensionOf,
  isAudioFile,
  isNativelyPlayable,
  mimeForExtension
} from '@shared/constants/audio'

describe('音频扩展名常量', () => {
  it('按最后一个点解析扩展名并转小写', () => {
    expect(extensionOf('Song.MP3')).toBe('.mp3')
    expect(extensionOf('a.b.flac')).toBe('.flac')
    expect(extensionOf('no-extension')).toBe('')
  })

  it('识别音频文件', () => {
    expect(isAudioFile('track.mp3')).toBe(true)
    expect(isAudioFile('track.APE')).toBe(true)
    expect(isAudioFile('cover.jpg')).toBe(false)
    expect(isAudioFile('lyrics.lrc')).toBe(false)
  })

  it('区分原生可播与需要转码的格式', () => {
    expect(isNativelyPlayable('a.flac')).toBe(true)
    expect(isNativelyPlayable('a.m4a')).toBe(true)
    expect(isNativelyPlayable('a.ape')).toBe(false)
    expect(isNativelyPlayable('a.dsf')).toBe(false)
  })

  it('原生格式集合是完整集合的子集', () => {
    for (const ext of ALL_AUDIO_EXTENSIONS) {
      expect(ext.startsWith('.')).toBe(true)
    }
  })

  it('返回正确的 MIME，未知扩展名回退', () => {
    expect(mimeForExtension('.flac')).toBe('audio/flac')
    expect(mimeForExtension('.opus')).toBe('audio/ogg')
    expect(mimeForExtension('.xyz')).toBe('application/octet-stream')
  })
})
