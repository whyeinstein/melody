import { create } from 'zustand'
import { clamp } from '../lib/format'
import type { RepeatMode } from '../lib/queue-order'

/** 播放器输出状态（与队列解耦：队列负责「放什么」，这里负责「怎么放」）。 */
export type PlaybackStatus = 'idle' | 'loading' | 'playing' | 'paused' | 'error'

/** 一次 seek 请求。用 nonce 区分连续两次 seek 到同一位置的情况。 */
export interface SeekRequest {
  positionMs: number
  nonce: number
}

export interface PlayerState {
  status: PlaybackStatus
  volume: number
  muted: boolean
  shuffle: boolean
  repeat: RepeatMode
  currentTimeMs: number
  durationMs: number
  error: string | null
  seekRequest: SeekRequest | null
  /** 播放失败后重新加载当前曲目的请求计数（音频引擎监听它重试）。 */
  retryNonce: number

  /** 请求播放（真正的 audio.play() 由音频引擎响应状态变化完成）。 */
  play: () => void
  pause: () => void
  toggle: () => void
  setStatus: (status: PlaybackStatus) => void
  setVolume: (volume: number) => void
  toggleMute: () => void
  setShuffle: (shuffle: boolean) => void
  setRepeat: (repeat: RepeatMode) => void
  cycleRepeat: () => void
  setProgress: (currentTimeMs: number, durationMs?: number) => void
  requestSeek: (positionMs: number, durationMs?: number) => void
  setError: (message: string | null) => void
  /** 用配置里的偏好初始化播放器。 */
  hydrate: (preferences: { volume?: number; shuffle?: boolean; repeat?: RepeatMode }) => void
}

const REPEAT_CYCLE: readonly RepeatMode[] = ['off', 'all', 'one']

let seekNonce = 0

export const usePlayerStore = create<PlayerState>()((set, get) => ({
  status: 'idle',
  volume: 0.8,
  muted: false,
  shuffle: false,
  repeat: 'off',
  currentTimeMs: 0,
  durationMs: 0,
  error: null,
  seekRequest: null,
  retryNonce: 0,

  play: () => {
    // 处于错误态时重新触发一次音源加载（例如媒体服务刚就绪）。
    if (get().status === 'error') {
      set((state) => ({ status: 'playing', error: null, retryNonce: state.retryNonce + 1 }))
      return
    }
    set({ status: 'playing', error: null })
  },

  pause: () => set({ status: 'paused' }),

  toggle: () => {
    if (get().status === 'playing') set({ status: 'paused' })
    else set({ status: 'playing', error: null })
  },

  setStatus: (status) => set({ status }),

  setVolume: (volume) => {
    const next = clamp(volume, 0, 1)
    set({ volume: next, muted: next === 0 ? get().muted : false })
  },

  toggleMute: () => set({ muted: !get().muted }),

  setShuffle: (shuffle) => set({ shuffle }),

  setRepeat: (repeat) => set({ repeat }),

  cycleRepeat: () => {
    const index = REPEAT_CYCLE.indexOf(get().repeat)
    const next = REPEAT_CYCLE[(index + 1) % REPEAT_CYCLE.length] ?? 'off'
    set({ repeat: next })
  },

  setProgress: (currentTimeMs, durationMs) => {
    set((state) => ({
      currentTimeMs: Number.isFinite(currentTimeMs) ? Math.max(0, Math.round(currentTimeMs)) : 0,
      durationMs:
        durationMs !== undefined && Number.isFinite(durationMs)
          ? Math.max(0, Math.round(durationMs))
          : state.durationMs
    }))
  },

  requestSeek: (positionMs, durationMs) => {
    const duration = durationMs ?? get().durationMs
    const target =
      duration > 0 ? clamp(positionMs, 0, duration) : Math.max(0, Number.isFinite(positionMs) ? positionMs : 0)
    seekNonce += 1
    set({ currentTimeMs: Math.round(target), seekRequest: { positionMs: target, nonce: seekNonce } })
  },

  setError: (message) => set({ error: message }),

  hydrate: (preferences) => {
    set((state) => ({
      volume: preferences.volume !== undefined ? clamp(preferences.volume, 0, 1) : state.volume,
      shuffle: preferences.shuffle ?? state.shuffle,
      repeat: preferences.repeat ?? state.repeat
    }))
  }
}))

/** 播放器是否处于「播放中」状态。 */
export function selectIsPlaying(state: PlayerState): boolean {
  return state.status === 'playing'
}

/** 当前是否处于加载中（用于播放按钮的加载态）。 */
export function selectIsLoading(state: PlayerState): boolean {
  return state.status === 'loading'
}
