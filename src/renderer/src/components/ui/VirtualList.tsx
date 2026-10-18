import { useRef } from 'react'
import type { JSX, ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { cn } from '../../lib/cn'

export interface VirtualListProps<T> {
  items: readonly T[]
  /** 行高估算值（px），实际高度以渲染结果为准。 */
  estimateSize?: number
  overscan?: number
  getItemKey?: (item: T, index: number) => string | number
  renderItem: (item: T, index: number) => ReactNode
  className?: string
  emptyState?: ReactNode
}

/**
 * 基于 @tanstack/react-virtual 的通用虚拟列表。
 * 音乐库可能有上万首歌曲，列表只渲染可视区域内的行。
 */
export function VirtualList<T>({
  items,
  estimateSize = 44,
  overscan = 8,
  getItemKey,
  renderItem,
  className,
  emptyState
}: VirtualListProps<T>): JSX.Element {
  const scrollRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    overscan,
    getItemKey: (index: number) => {
      const item = items[index]
      return item === undefined || getItemKey === undefined ? index : getItemKey(item, index)
    }
  })

  if (items.length === 0 && emptyState !== undefined) return <>{emptyState}</>

  return (
    <div ref={scrollRef} className={cn('relative h-full overflow-y-auto', className)}>
      <div className="relative w-full" style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const item = items[virtualItem.index]
          if (item === undefined) return null
          return (
            <div
              key={virtualItem.key}
              className="absolute left-0 top-0 w-full"
              style={{ height: `${virtualItem.size}px`, transform: `translateY(${virtualItem.start}px)` }}
            >
              {renderItem(item, virtualItem.index)}
            </div>
          )
        })}
      </div>
    </div>
  )
}
