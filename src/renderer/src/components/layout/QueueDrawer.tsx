import { useMemo, useState } from 'react'
import type { JSX } from 'react'
import { AudioLines, GripVertical, ListMusic, Trash, X } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { formatDuration } from '../../lib/format'
import { clearQueue, playQueueItem, removeQueueItem } from '../../lib/playback'
import { usePlayerStore } from '../../stores/player-store'
import { orderedTracks, useQueueStore } from '../../stores/queue-store'
import { useUiStore } from '../../stores/ui-store'
import { EmptyState } from '../ui/EmptyState'
import { IconButton } from '../ui/IconButton'

/**
 * 右侧可展开的播放队列抽屉。
 * 支持：点击切歌、拖拽调整展示顺序、移除单曲、清空队列。
 */
export function QueueDrawer(): JSX.Element {
  const open = useUiStore((state) => state.queueOpen)
  const toggleQueue = useUiStore((state) => state.toggleQueue)
  const items = useQueueStore((state) => state.items)
  const order = useQueueStore((state) => state.order)
  const currentId = useQueueStore((state) => state.currentId)
  const playing = usePlayerStore((state) => state.status === 'playing')
  const move = useQueueStore((state) => state.move)

  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dropIndex, setDropIndex] = useState<number | null>(null)

  // 展示顺序 = items；播放顺序由 order 决定（随机播放时两者不同）。
  const playbackOrder = useMemo(() => orderedTracks({ items, order }), [items, order])

  return (
    <aside
      className={cn(
        'relative flex h-full shrink-0 flex-col overflow-hidden border-border bg-bg-elevated transition-[width,border-width] duration-200',
        open ? 'w-80 border-l' : 'w-0 border-l-0'
      )}
      aria-hidden={!open}
      inert={!open}
      aria-label={zhCN.queue.title}
    >
      <div className="flex h-full w-80 flex-col">
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2">
            <ListMusic size={16} className="text-accent" aria-hidden="true" />
            <h2 className="text-sm font-medium text-fg">{zhCN.queue.title}</h2>
            <span className="text-xs text-fg-muted">{zhCN.queue.count(items.length)}</span>
          </div>
          <div className="flex items-center gap-1">
            <IconButton
              icon={Trash}
              label={zhCN.queue.clear}
              size="sm"
              disabled={items.length === 0}
              onClick={clearQueue}
            />
            <IconButton
              icon={X}
              label={zhCN.queue.close}
              size="sm"
              onClick={() => toggleQueue(false)}
            />
          </div>
        </div>

        {items.length === 0 ? (
          <EmptyState icon={ListMusic} title={zhCN.queue.empty} description={zhCN.queue.emptyHint} />
        ) : (
          <>
            <p className="px-4 py-2 text-[11px] text-fg-muted">{zhCN.queue.dragHint}</p>
            <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
              {items.map((track, index) => {
                const current = track.id === currentId
                return (
                  <li
                    key={track.id}
                    draggable
                    onDragStart={(event) => {
                      setDragIndex(index)
                      event.dataTransfer.effectAllowed = 'move'
                    }}
                    onDragOver={(event) => {
                      event.preventDefault()
                      if (dropIndex !== index) setDropIndex(index)
                    }}
                    onDragLeave={() => {
                      if (dropIndex === index) setDropIndex(null)
                    }}
                    onDrop={(event) => {
                      event.preventDefault()
                      if (dragIndex !== null && dragIndex !== index) move(dragIndex, index)
                      setDragIndex(null)
                      setDropIndex(null)
                    }}
                    onDragEnd={() => {
                      setDragIndex(null)
                      setDropIndex(null)
                    }}
                    className={cn(
                      'group flex cursor-default items-center gap-2 rounded-[var(--radius-sm)] px-2 py-1.5 transition-colors',
                      current ? 'bg-accent-soft' : 'hover:bg-bg-hover',
                      dropIndex === index && dragIndex !== null ? 'ring-1 ring-accent' : ''
                    )}
                  >
                    <GripVertical
                      size={13}
                      className="shrink-0 cursor-grab text-fg-muted opacity-0 group-hover:opacity-100"
                      aria-hidden="true"
                    />
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      onClick={() => playQueueItem(track.id)}
                      title={track.title}
                    >
                      {current ? (
                        <AudioLines size={14} className="shrink-0 text-accent" aria-hidden="true" />
                      ) : null}
                      <span className="min-w-0 flex-1">
                        <span
                          className={cn(
                            'block truncate text-sm',
                            current ? 'font-medium text-accent' : 'text-fg'
                          )}
                        >
                          {track.title}
                        </span>
                        <span className="block truncate text-xs text-fg-muted">
                          {track.artist ?? zhCN.common.unknownArtist}
                        </span>
                      </span>
                      <span className="shrink-0 text-[11px] tabular-nums text-fg-muted">
                        {formatDuration(track.durationMs)}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label={zhCN.actions.removeFromQueue}
                      title={zhCN.actions.removeFromQueue}
                      onClick={() => removeQueueItem(track.id)}
                      className="shrink-0 rounded p-1 text-fg-muted opacity-0 transition-colors hover:bg-bg-active hover:text-fg group-hover:opacity-100"
                    >
                      <X size={13} aria-hidden="true" />
                    </button>
                  </li>
                )
              })}
            </ul>
            {playbackOrder.length > 0 ? (
              <p className="shrink-0 border-t border-border px-4 py-2 text-[11px] text-fg-muted">
                {zhCN.queue.position(
                  playbackOrder.findIndex((track) => track.id === currentId) + 1,
                  playbackOrder.length
                )}
                {playing ? ` · ${zhCN.player.nowPlaying}` : ''}
              </p>
            ) : null}
          </>
        )}
      </div>
    </aside>
  )
}
