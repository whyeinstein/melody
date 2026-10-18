/** 界面展示用的格式化工具，全部为纯函数。 */
import { zhCN } from '../i18n/zh-CN'

const countFormatter = new Intl.NumberFormat('zh-CN')
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
})

/** 将毫秒格式化为 `m:ss` 或 `h:mm:ss`，非法值显示 `--:--`。 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return '--:--'
  const totalSeconds = Math.floor(ms / 1000)
  const seconds = totalSeconds % 60
  const minutes = Math.floor(totalSeconds / 60) % 60
  const hours = Math.floor(totalSeconds / 3600)
  const pad = (value: number): string => String(value).padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`
}

/** 专辑/播放列表总时长，例如 `1 小时 12 分钟`。 */
export function formatTotalDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms <= 0) {
    return zhCN.time.duration(0, 0)
  }
  const totalMinutes = Math.round(ms / 60000)
  return zhCN.time.duration(Math.floor(totalMinutes / 60), totalMinutes % 60)
}

/** 文件大小，例如 `12.4 MB`。 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB'] as const
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  const unit = units[unitIndex] ?? 'B'
  return `${unitIndex === 0 ? Math.round(value) : value.toFixed(1)} ${unit}`
}

/** 时间戳 → `2026/10/18`。 */
export function formatDate(timestamp: number | null | undefined): string {
  if (timestamp === null || timestamp === undefined || !Number.isFinite(timestamp) || timestamp <= 0) {
    return '—'
  }
  return dateFormatter.format(new Date(timestamp))
}

/** 千分位数字。 */
export function formatCount(value: number): string {
  return countFormatter.format(value)
}

export function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min
  return Math.min(Math.max(value, min), max)
}

/** 计算百分比（0~100），用于进度条/音量条。 */
export function percentOf(value: number, max: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(max) || max <= 0) return 0
  return clamp((value / max) * 100, 0, 100)
}
