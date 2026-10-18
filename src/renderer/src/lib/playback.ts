import type { Track } from '@shared/domain/types'
import { zhCN } from '../i18n/zh-CN'
import { clearMediaSession } from './media'
import type { RepeatMode } from './queue-order'
import { persistPreferences } from './preferences'
import { usePlayerStore } from '../stores/player-store'
import { useQueueStore } from '../stores/queue-store'
import { useUiStore, type ToastKind } from '../stores/ui-store'

/**
 * 播放控制器：把「队列（放什么）」和「播放器（怎么放）」两个 store 组合成
 * 界面可调用的动作。组件与音频引擎都只调用这里的函数，避免把业务逻辑散落在 UI 里。
 */

/** 上一首时，已播放超过该时长则回到本曲开头，而不是切到上一首。 */
const RESTART_THRESHOLD_MS = 3000

function toast(kind: ToastKind, title: string, description?: string): void {
  useUiStore.getState().pushToast({ kind, title, description })
}

/** 用给定的歌曲列表替换队列，并从 startIndex 开始播放。 */
export function playTracks(tracks: readonly Track[], startIndex = 0): void {
  if (tracks.length === 0) {
    toast('info', zhCN.errors.noTrackSelected)
    return
  }
  const player = usePlayerStore.getState()
  useQueueStore.getState().setQueue(tracks, startIndex, player.shuffle)
  player.play()
}

/** 点击队列中的某一首播放。 */
export function playQueueItem(trackId: number): void {
  if (!useQueueStore.getState().jumpTo(trackId)) return
  usePlayerStore.getState().play()
}

/** 追加到队尾。 */
export function enqueueTracks(tracks: readonly Track[]): void {
  if (tracks.length === 0) return
  const added = useQueueStore.getState().append(tracks)
  if (added > 0) toast('success', zhCN.toasts.addedToQueue)
  else toast('info', zhCN.toasts.alreadyInQueue)
}

/** 插入到当前曲目之后（「下一首播放」）。 */
export function playTrackNext(track: Track): void {
  if (useQueueStore.getState().insertNext(track)) toast('success', zhCN.toasts.willPlayNext)
  else toast('info', zhCN.toasts.alreadyInQueue)
}

/** 下一首。auto=true 表示由「播放结束」触发。 */
export function playNext(auto = false): void {
  const player = usePlayerStore.getState()
  const queue = useQueueStore.getState()
  const nextId = queue.next(player.repeat, auto)
  if (nextId === null) {
    player.pause()
    if (!auto) toast('info', zhCN.errors.queueEnded)
    return
  }
  player.play()
}

/** 上一首：播放超过 3 秒时先回到本曲开头。 */
export function playPrevious(): void {
  const player = usePlayerStore.getState()
  if (player.currentTimeMs > RESTART_THRESHOLD_MS) {
    seekTo(0)
    return
  }
  const queue = useQueueStore.getState()
  const previousId = queue.previous(player.repeat)
  if (previousId === null) {
    seekTo(0)
    return
  }
  player.play()
}

/** 播放/暂停切换（空格快捷键与播放条按钮共用）。 */
export function togglePlay(): void {
  const player = usePlayerStore.getState()
  if (player.status === 'playing') {
    player.pause()
    return
  }
  const queue = useQueueStore.getState()
  if (queue.items.length === 0) {
    toast('info', zhCN.errors.noTrackSelected)
    return
  }
  if (queue.currentId === null) {
    const firstId = queue.order[0] ?? queue.items[0]?.id
    if (firstId === undefined) return
    queue.jumpTo(firstId)
  }
  // 错误态重试时丢弃旧的媒体会话缓存，重新向主进程获取。
  if (player.status === 'error') clearMediaSession()
  player.play()
}

/** 跳转到指定位置（毫秒）。 */
export function seekTo(positionMs: number): void {
  usePlayerStore.getState().requestSeek(positionMs)
}

/** 相对快进/快退（毫秒），供方向键使用。 */
export function seekBy(deltaMs: number): void {
  const player = usePlayerStore.getState()
  player.requestSeek(player.currentTimeMs + deltaMs)
}

/** 切换随机播放，并重建播放顺序。 */
export function toggleShuffle(): void {
  const player = usePlayerStore.getState()
  const next = !player.shuffle
  player.setShuffle(next)
  useQueueStore.getState().rebuildOrder(next)
  persistPreferences()
  toast('info', next ? zhCN.player.shuffleOn : zhCN.player.shuffleOff)
}

const REPEAT_LABEL: Record<RepeatMode, string> = {
  off: zhCN.player.repeatOff,
  all: zhCN.player.repeatAll,
  one: zhCN.player.repeatOne
}

/** 循环模式：关闭 → 列表循环 → 单曲循环。 */
export function cycleRepeat(): void {
  const player = usePlayerStore.getState()
  player.cycleRepeat()
  persistPreferences()
  toast('info', REPEAT_LABEL[usePlayerStore.getState().repeat])
}

/** 设置音量（0~1），并持久化偏好。 */
export function setVolume(volume: number): void {
  const player = usePlayerStore.getState()
  player.setVolume(volume)
  if (volume > 0 && player.muted) player.toggleMute()
  persistPreferences()
}

/** 静音切换。 */
export function toggleMute(): void {
  usePlayerStore.getState().toggleMute()
  persistPreferences()
}

/** 清空队列并停止播放。 */
export function clearQueue(): void {
  useQueueStore.getState().clear()
  const player = usePlayerStore.getState()
  player.pause()
  player.setProgress(0, 0)
  player.setStatus('idle')
  toast('info', zhCN.toasts.queueCleared)
}

/** 从队列移除一首歌；如果移除的是当前曲目，按剩余队列继续或停止。 */
export function removeQueueItem(trackId: number): void {
  const player = usePlayerStore.getState()
  const wasPlaying = player.status === 'playing'
  const result = useQueueStore.getState().remove(trackId)
  if (!result.removedCurrent) return
  if (result.nextId === null) {
    player.pause()
    player.setStatus('idle')
    player.setProgress(0, 0)
    return
  }
  if (wasPlaying) player.play()
}
