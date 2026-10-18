import { useEffect, useMemo, useRef } from 'react'
import { zhCN } from '../i18n/zh-CN'
import { invoke } from '../lib/ipc'
import { buildTrackStreamUrl, ensureMediaSession } from '../lib/media'
import { playNext } from '../lib/playback'
import { getAudioEngine } from '../player/audio-engine'
import { usePlayerStore } from '../stores/player-store'
import { selectCurrentTrack, useQueueStore } from '../stores/queue-store'
import { useUiStore } from '../stores/ui-store'

/**
 * 音频引擎与 store 的桥接：
 * - store 状态变化 → 引擎（加载/播放/暂停/seek/音量）；
 * - 引擎事件 → store（进度、播放结束、错误）。
 *
 * 只在应用根部调用一次。
 */
export function useAudioEngine(): void {
  const engine = useMemo(() => getAudioEngine(), [])
  const currentTrack = useQueueStore(selectCurrentTrack)
  const currentTrackId = currentTrack?.id ?? null
  const status = usePlayerStore((state) => state.status)
  const volume = usePlayerStore((state) => state.volume)
  const muted = usePlayerStore((state) => state.muted)
  const seekRequest = usePlayerStore((state) => state.seekRequest)
  const retryNonce = usePlayerStore((state) => state.retryNonce)
  const markedTrackRef = useRef<number | null>(null)

  // 引擎事件 → store
  useEffect(() => {
    engine.configure({
      onProgress: (currentTimeMs, durationMs) => {
        usePlayerStore.getState().setProgress(currentTimeMs, durationMs)
      },
      onEnded: () => {
        const player = usePlayerStore.getState()
        // 单曲循环：重播当前曲目（不重新加载音源）。
        if (player.repeat === 'one') {
          engine.seek(0)
          void engine.play()
          return
        }
        playNext(true)
      },
      onError: (message) => {
        const player = usePlayerStore.getState()
        player.setStatus('error')
        player.setError(message)
        useUiStore.getState().pushToast({
          kind: 'error',
          title: zhCN.errors.playbackFailed,
          description: message
        })
      }
    })
    return () => engine.configure({})
  }, [engine])

  // 音量 / 静音
  useEffect(() => {
    engine.setVolume(volume)
    engine.setMuted(muted)
  }, [engine, volume, muted])

  // 当前曲目变化 → 获取媒体会话并加载音源
  useEffect(() => {
    if (currentTrackId === null) {
      engine.stop()
      usePlayerStore.getState().setProgress(0, 0)
      return
    }

    // 记录「用户是否希望继续播放」：切歌前通常处于 playing 状态。
    const shouldPlay = usePlayerStore.getState().status === 'playing'
    let cancelled = false

    engine.pause()
    void (async () => {
      const player = usePlayerStore.getState()
      player.setStatus('loading')
      player.setError(null)

      const session = await ensureMediaSession()
      if (cancelled) return
      if (session === null) {
        player.setStatus('error')
        player.setError(zhCN.errors.mediaUnavailable)
        useUiStore.getState().pushToast({
          kind: 'error',
          title: zhCN.errors.mediaUnavailable,
          description: zhCN.errors.mediaUnavailableHint
        })
        return
      }

      await engine.load(buildTrackStreamUrl(session, currentTrackId))
      if (cancelled) return
      usePlayerStore.getState().setStatus(shouldPlay ? 'playing' : 'paused')
    })()

    return () => {
      cancelled = true
    }
  }, [engine, currentTrackId, retryNonce])

  // 播放/暂停状态 → 引擎
  useEffect(() => {
    if (status === 'playing') {
      void engine.play()
      return
    }
    if (status === 'paused' || status === 'idle' || status === 'error') {
      engine.pause()
    }
  }, [engine, status])

  // seek 请求 → 引擎
  useEffect(() => {
    if (seekRequest === null) return
    engine.seek(seekRequest.positionMs)
  }, [engine, seekRequest])

  // 开始播放时上报播放次数（主进程频道未实现时静默忽略）
  useEffect(() => {
    if (status !== 'playing' || currentTrackId === null) return
    if (markedTrackRef.current === currentTrackId) return
    markedTrackRef.current = currentTrackId
    void invoke('tracks:markPlayed', { id: currentTrackId })
  }, [status, currentTrackId])
}
