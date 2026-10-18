import type { MediaSession } from '@shared/domain/types'
import { invoke } from './ipc'

/**
 * 媒体服务（主进程）访问封装。
 *
 * 约定（与主进程 `src/main/services/media/server.ts` 保持一致）：
 * - 音频流：`GET {baseUrl}/audio/{trackId}?token={token}`（支持 Range 206）
 * - 封面图：`GET {baseUrl}/covers/{coverId}?token={token}`
 *
 * 注意：渲染层用 WebAudio（MediaElementAudioSourceNode）接管音频输出，
 * Chromium 要求音频请求可跨域，因此主进程媒体服务需要返回
 * `Access-Control-Allow-Origin` 响应头；音频引擎会在首次播放前探测，
 * 探测不到时退化为 <audio> 直接播放（可正常出声，但没有 analyser/EQ）。
 */

let cachedSession: MediaSession | null = null
let inflight: Promise<MediaSession | null> | null = null

/** 获取（并缓存）媒体会话；主进程频道尚未实现时返回 null，由界面展示降级提示。 */
export async function ensureMediaSession(force = false): Promise<MediaSession | null> {
  if (force) clearMediaSession()
  if (cachedSession !== null) return cachedSession
  inflight ??= (async () => {
    const result = await invoke('media:session')
    if (!result.ok) return null
    cachedSession = result.data
    return cachedSession
  })().finally(() => {
    inflight = null
  })
  return inflight
}

export function clearMediaSession(): void {
  cachedSession = null
  inflight = null
}

/** 根据媒体会话构造音频流地址。 */
export function buildTrackStreamUrl(session: MediaSession, trackId: number): string {
  const base = session.baseUrl.replace(/\/+$/, '')
  const token = encodeURIComponent(session.token)
  return `${base}/audio/${trackId}?token=${token}`
}

/** 根据媒体会话构造封面地址（阶段 2 用于专辑封面显示）。 */
export function buildCoverUrl(session: MediaSession, coverId: number): string {
  const base = session.baseUrl.replace(/\/+$/, '')
  const token = encodeURIComponent(session.token)
  return `${base}/covers/${coverId}?token=${token}`
}
