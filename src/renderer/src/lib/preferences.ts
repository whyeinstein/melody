import { invoke } from './ipc'
import { usePlayerStore } from '../stores/player-store'

/**
 * 把播放偏好写回配置（音量/随机/循环）。
 *
 * 配置频道尚未实现时静默忽略：这属于可降级的非关键功能，
 * 不打断播放，也不向用户弹错误提示。
 */
let timer: ReturnType<typeof setTimeout> | null = null

export function persistPreferences(): void {
  if (timer !== null) clearTimeout(timer)
  timer = setTimeout(() => {
    timer = null
    const player = usePlayerStore.getState()
    void invoke('config:set', {
      volume: player.volume,
      shuffle: player.shuffle,
      repeat: player.repeat
    })
  }, 400)
}
