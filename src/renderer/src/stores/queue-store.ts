import type { Track } from '@shared/domain/types'
import { create } from 'zustand'
import {
  appendToOrder,
  clampIndex,
  createPlayOrder,
  insertAfter,
  moveItem,
  normalizeOrder,
  positionOf,
  removeFromOrder,
  stepOrder,
  type RandomSource,
  type RepeatMode
} from '../lib/queue-order'

/** 队列增删/切歌的结果，供播放控制器决定是否继续播放。 */
export interface RemoveResult {
  removedCurrent: boolean
  nextId: number | null
}

export interface QueueState {
  /** 队列的展示顺序（用户拖拽调整的就是它）。 */
  items: Track[]
  currentId: number | null
  /** 实际的播放顺序（trackId 序列）；随机播放时是 items 的一个排列。 */
  order: number[]
  orderPosition: number

  /** 用新的曲目集合替换队列，并从 startIndex 开始播放。 */
  setQueue: (tracks: readonly Track[], startIndex?: number, shuffle?: boolean, random?: RandomSource) => void
  /** 跳转到队列中的某首歌。 */
  jumpTo: (trackId: number) => boolean
  /** 播放顺序中的下一首。返回 null 表示已到边界。 */
  next: (repeat: RepeatMode, auto?: boolean) => number | null
  /** 播放顺序中的上一首。返回 null 表示已到边界。 */
  previous: (repeat: RepeatMode) => number | null
  /** 随机模式变化后重建播放顺序（保持当前曲目为第一首）。 */
  rebuildOrder: (shuffle: boolean, random?: RandomSource) => void
  /** 追加曲目（自动去重），返回实际新增数量。 */
  append: (tracks: readonly Track[]) => number
  /** 插入到当前曲目之后，返回是否插入成功。 */
  insertNext: (track: Track) => boolean
  /** 拖拽排序（只影响展示顺序，不影响随机播放顺序）。 */
  move: (from: number, to: number) => void
  /** 同步收藏状态（图书馆里收藏后，队列/播放条中的同一首歌保持一致）。 */
  setFavorite: (trackId: number, favorite: boolean) => void
  /** 移除某首歌；如果移除的是当前曲目，会顺延到下一首。 */
  remove: (trackId: number) => RemoveResult
  clear: () => void
}

export const useQueueStore = create<QueueState>()((set, get) => ({
  items: [],
  currentId: null,
  order: [],
  orderPosition: -1,

  setQueue: (tracks, startIndex = 0, shuffle = false, random = Math.random) => {
    const items = tracks.slice()
    const safeIndex = clampIndex(startIndex, items.length)
    const current = safeIndex >= 0 ? items[safeIndex] : undefined
    const ids = items.map((track) => track.id)
    const order = createPlayOrder(ids, shuffle, current?.id ?? null, random)
    set({
      items,
      currentId: current?.id ?? null,
      order,
      orderPosition: positionOf(order, current?.id ?? null)
    })
  },

  jumpTo: (trackId) => {
    const { items, order } = get()
    if (!items.some((track) => track.id === trackId)) return false
    const position = order.indexOf(trackId)
    if (position === -1) {
      // order 与 items 失配时兜底重建，保证跳转一定成功。
      const rebuilt = normalizeOrder(order, items.map((track) => track.id))
      set({ order: rebuilt, orderPosition: positionOf(rebuilt, trackId), currentId: trackId })
      return true
    }
    set({ currentId: trackId, orderPosition: position })
    return true
  },

  next: (repeat, auto = false) => {
    const { order, orderPosition } = get()
    const position = stepOrder(order.length, orderPosition, 1, repeat, auto)
    if (position === null) return null
    const trackId = order[position]
    if (trackId === undefined) return null
    set({ currentId: trackId, orderPosition: position })
    return trackId
  },

  previous: (repeat) => {
    const { order, orderPosition } = get()
    const position = stepOrder(order.length, orderPosition, -1, repeat, false)
    if (position === null) return null
    const trackId = order[position]
    if (trackId === undefined) return null
    set({ currentId: trackId, orderPosition: position })
    return trackId
  },

  rebuildOrder: (shuffle, random = Math.random) => {
    const { items, currentId } = get()
    const order = createPlayOrder(
      items.map((track) => track.id),
      shuffle,
      currentId,
      random
    )
    set({ order, orderPosition: positionOf(order, currentId) })
  },

  append: (tracks) => {
    const { items, order } = get()
    const existing = new Set(items.map((track) => track.id))
    const fresh = tracks.filter((track) => !existing.has(track.id))
    if (fresh.length === 0) return 0
    const nextItems = [...items, ...fresh]
    const nextOrder = appendToOrder(
      order,
      fresh.map((track) => track.id)
    )
    set({ items: nextItems, order: nextOrder })
    return fresh.length
  },

  insertNext: (track) => {
    const { items, order, currentId } = get()
    if (items.some((item) => item.id === track.id)) return false
    const nextItems = items.slice()
    const currentIndex = nextItems.findIndex((item) => item.id === currentId)
    if (currentIndex === -1) nextItems.push(track)
    else nextItems.splice(currentIndex + 1, 0, track)
    const nextOrder = insertAfter(order, currentId, track.id)
    set({
      items: nextItems,
      order: nextOrder,
      orderPosition: positionOf(nextOrder, currentId)
    })
    return true
  },

  move: (from, to) => {
    set({ items: moveItem(get().items, from, to) })
  },

  setFavorite: (trackId, favorite) => {
    set((state) => ({
      items: state.items.map((track) =>
        track.id === trackId ? { ...track, favorite } : track
      )
    }))
  },

  remove: (trackId) => {
    const { items, order, currentId, orderPosition } = get()
    const removedCurrent = currentId === trackId
    const nextItems = items.filter((track) => track.id !== trackId)
    let nextOrder = removeFromOrder(order, trackId)

    let nextCurrentId = currentId
    if (removedCurrent) {
      // 当前歌曲被移除：顺延到播放顺序中的下一首，若已到末尾则回退到最后一首。
      const fallbackIndex = Math.min(Math.max(orderPosition, 0), nextOrder.length - 1)
      nextCurrentId = nextOrder[fallbackIndex] ?? null
    }

    nextOrder = normalizeOrder(nextOrder, nextItems.map((track) => track.id))
    set({
      items: nextItems,
      order: nextOrder,
      currentId: nextCurrentId,
      orderPosition: positionOf(nextOrder, nextCurrentId)
    })
    return { removedCurrent, nextId: nextCurrentId }
  },

  clear: () => set({ items: [], currentId: null, order: [], orderPosition: -1 })
}))

/** 当前曲目（不存在时返回 null）。 */
export function selectCurrentTrack(state: QueueState): Track | null {
  return state.items.find((track) => track.id === state.currentId) ?? null
}

/** 当前曲目在展示列表中的下标，未在播放时为 -1。 */
export function selectCurrentIndex(state: QueueState): number {
  return state.items.findIndex((track) => track.id === state.currentId)
}

/**
 * 按播放顺序返回曲目列表。
 * 注意：每次调用都会生成新数组，只能在渲染函数里配合 useMemo 使用，
 * 不要直接作为 zustand selector（会导致不必要的重渲染）。
 */
export function orderedTracks(state: Pick<QueueState, 'items' | 'order'>): Track[] {
  const byId = new Map(state.items.map((track) => [track.id, track] as const))
  const result: Track[] = []
  for (const id of state.order) {
    const track = byId.get(id)
    if (track !== undefined) result.push(track)
  }
  return result
}
