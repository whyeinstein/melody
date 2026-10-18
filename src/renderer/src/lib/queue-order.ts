/**
 * 播放队列的纯函数算法：不依赖 React / Zustand / DOM，便于直接单元测试。
 *
 * 队列模型：
 * - `items` 是队列的展示顺序（用户拖拽调整的就是它）；
 * - `order` 是实际的播放顺序（trackId 序列），随机播放时是 items 的一个排列；
 * - `orderPosition` 是当前曲目在 order 中的下标。
 */

/** 播放模式，取值与 AppConfig.repeat 保持一致。 */
export type RepeatMode = 'off' | 'all' | 'one'

/** 可注入的随机源，便于对随机算法做确定性测试。 */
export type RandomSource = () => number

/**
 * 把任意下标安全地收敛到 `[0, length-1]`。
 * 空数组返回 -1，调用方据此判断「没有当前曲目」。
 */
export function clampIndex(index: number, length: number): number {
  if (length <= 0) return -1
  if (!Number.isFinite(index)) return 0
  return Math.min(Math.max(Math.trunc(index), 0), length - 1)
}

/** Fisher-Yates 洗牌，返回新数组，不修改入参。 */
export function shuffledCopy<T>(items: readonly T[], random: RandomSource = Math.random): T[] {
  const result = items.slice()
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1))
    const a = result[i]
    const b = result[j]
    // noUncheckedIndexedAccess 下需要显式判空；下标始终合法，这里只是让类型收敛。
    if (a === undefined || b === undefined) continue
    result[i] = b
    result[j] = a
  }
  return result
}

/**
 * 生成播放顺序。
 * - 关闭随机：保持传入顺序；
 * - 开启随机：洗牌，并把 `preferredId`（通常是当前曲目）放到第一位，
 *   这样切换随机模式时不会打断正在播放的歌曲。
 */
export function createPlayOrder(
  ids: readonly number[],
  shuffle: boolean,
  preferredId: number | null = null,
  random: RandomSource = Math.random
): number[] {
  const unique = [...new Set(ids)]
  if (!shuffle) return unique
  const order = shuffledCopy(unique, random)
  if (preferredId === null) return order
  const position = order.indexOf(preferredId)
  if (position > 0) {
    const [preferred] = order.splice(position, 1)
    if (preferred !== undefined) order.unshift(preferred)
  }
  return order
}

/**
 * 计算下一首/上一首在 order 中的位置。
 *
 * @param orderLength 播放顺序长度
 * @param position    当前在 order 中的下标（-1 表示尚未开始）
 * @param direction   1 表示下一首，-1 表示上一首
 * @param repeat      循环模式
 * @param auto        true 表示「自然播放结束」触发的自动切歌：
 *                    repeat === 'one' 时停留在当前曲目（由调用方重播）；
 *                    手动切歌（auto=false）时单曲循环等同于列表循环。
 * @returns 目标位置；返回 null 表示应当停止播放（已到队列边界且不循环）。
 */
export function stepOrder(
  orderLength: number,
  position: number,
  direction: 1 | -1,
  repeat: RepeatMode,
  auto = false
): number | null {
  if (orderLength <= 0) return null
  if (position < 0 || position >= orderLength) {
    // 尚未开始播放：下一首从头部开始，上一首从末尾开始。
    return direction === 1 ? 0 : orderLength - 1
  }
  if (auto && repeat === 'one') return position

  const candidate = position + direction
  if (candidate >= 0 && candidate < orderLength) return candidate
  if (repeat === 'off') return null
  return direction === 1 ? 0 : orderLength - 1
}

/** 拖拽排序：把 from 位置的元素移动到 to 位置，返回新数组。 */
export function moveItem<T>(items: readonly T[], from: number, to: number): T[] {
  const next = items.slice()
  if (from === to) return next
  if (from < 0 || from >= next.length || to < 0 || to >= next.length) return next
  const [moved] = next.splice(from, 1)
  if (moved === undefined) return items.slice()
  next.splice(to, 0, moved)
  return next
}

/** 从播放顺序中移除某个 trackId。 */
export function removeFromOrder(order: readonly number[], id: number): number[] {
  return order.filter((entry) => entry !== id)
}

/** 查询 trackId 在播放顺序中的位置，不存在返回 -1。 */
export function positionOf(order: readonly number[], id: number | null): number {
  if (id === null) return -1
  return order.indexOf(id)
}

/** 把新 trackId 追加到播放顺序末尾（已存在则忽略）。 */
export function appendToOrder(order: readonly number[], ids: readonly number[]): number[] {
  const existing = new Set(order)
  const result = order.slice()
  for (const id of ids) {
    if (!existing.has(id)) {
      result.push(id)
      existing.add(id)
    }
  }
  return result
}

/** 把 trackId 插入到 `afterId` 之后（afterId 为 null 或不存在时追加到末尾）。 */
export function insertAfter(order: readonly number[], afterId: number | null, id: number): number[] {
  const result = order.filter((entry) => entry !== id)
  const position = afterId === null ? -1 : result.indexOf(afterId)
  if (position === -1) result.push(id)
  else result.splice(position + 1, 0, id)
  return result
}

/**
 * 让播放顺序与队列内容保持一致：丢弃已不存在的 id，并补齐遗漏的 id。
 * 用于队列增删之后兜底，避免 order / items 失配。
 */
export function normalizeOrder(order: readonly number[], ids: readonly number[]): number[] {
  const available = new Set(ids)
  const seen = new Set<number>()
  const result: number[] = []
  for (const id of order) {
    if (available.has(id) && !seen.has(id)) {
      result.push(id)
      seen.add(id)
    }
  }
  for (const id of ids) {
    if (!seen.has(id)) {
      result.push(id)
      seen.add(id)
    }
  }
  return result
}
