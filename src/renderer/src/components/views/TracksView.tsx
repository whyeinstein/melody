import { useEffect, useRef, useState } from 'react'
import type { JSX } from 'react'
import type { Track, TrackQuery } from '@shared/domain/types'
import { AudioLines, CircleAlert, Heart, ListEnd, ListPlus, Play, RefreshCw } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { formatDuration } from '../../lib/format'
import { enqueueTracks, playTrackNext, playTracks } from '../../lib/playback'
import { useLibraryStore } from '../../stores/library-store'
import { usePlayerStore } from '../../stores/player-store'
import { useQueueStore } from '../../stores/queue-store'
import { Button } from '../ui/Button'
import { ContextMenu, type ContextMenuItem } from '../ui/ContextMenu'
import { CoverArt } from '../ui/CoverArt'
import { EmptyState } from '../ui/EmptyState'
import { VirtualList } from '../ui/VirtualList'

/** 歌曲列表的行高与网格列宽（表头与数据行共用，保证对齐）。 */
const ROW_HEIGHT = 44
const GRID_COLUMNS =
  'grid grid-cols-[2.25rem_minmax(0,1fr)_minmax(0,0.9fr)_4rem_2.5rem] items-center gap-3 px-3'

interface TracksViewProps {
  preset: TrackQuery
  emptyTitle: string
  emptyHint: string
}

interface MenuState {
  x: number
  y: number
  track: Track
}

function TrackRow({
  track,
  index,
  current,
  playing,
  onPlay,
  onContextMenu
}: {
  track: Track
  index: number
  current: boolean
  playing: boolean
  onPlay: () => void
  onContextMenu: (x: number, y: number) => void
}): JSX.Element {
  const toggleFavorite = useLibraryStore((state) => state.toggleFavorite)

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${zhCN.actions.play} ${track.title}`}
      title={track.path}
      onClick={onPlay}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onPlay()
        }
      }}
      onContextMenu={(event) => {
        event.preventDefault()
        onContextMenu(event.clientX, event.clientY)
      }}
      className={cn(
        GRID_COLUMNS,
        'group h-11 cursor-default select-none rounded-[var(--radius-sm)] text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        current ? 'bg-accent-soft' : 'hover:bg-bg-hover'
      )}
    >
      <div className="flex items-center justify-center text-xs text-fg-muted">
        {current && playing ? (
          <AudioLines size={15} className="text-accent" aria-hidden="true" />
        ) : (
          <span className={cn('tabular-nums', current && 'text-accent')}>{index + 1}</span>
        )}
      </div>

      <div className="flex min-w-0 items-center gap-2.5">
        <CoverArt coverId={track.coverId} size={32} />
        <div className="min-w-0">
          <p className={cn('truncate', current ? 'font-medium text-accent' : 'text-fg')}>{track.title}</p>
          <p className="truncate text-xs text-fg-muted">{track.artist ?? zhCN.common.unknownArtist}</p>
        </div>
      </div>

      <p className="truncate text-sm text-fg-muted">{track.album ?? zhCN.common.unknownAlbum}</p>
      <p className="text-right text-xs tabular-nums text-fg-muted">{formatDuration(track.durationMs)}</p>

      <div className="flex justify-center">
        <button
          type="button"
          aria-label={track.favorite ? zhCN.actions.removeFavorite : zhCN.actions.addFavorite}
          title={track.favorite ? zhCN.actions.removeFavorite : zhCN.actions.addFavorite}
          onClick={(event) => {
            event.stopPropagation()
            void toggleFavorite(track)
          }}
          className="rounded-full p-1.5 transition-colors hover:bg-bg-active"
        >
          <Heart
            size={14}
            className={cn(
              track.favorite ? 'text-accent' : 'text-fg-muted opacity-0 group-hover:opacity-100'
            )}
            fill={track.favorite ? 'currentColor' : 'none'}
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  )
}

function ListHeader(): JSX.Element {
  return (
    <div
      className={cn(
        GRID_COLUMNS,
        'shrink-0 border-b border-border pb-2 pt-1 text-[11px] font-medium text-fg-muted'
      )}
    >
      <span className="text-center">{zhCN.columns.index}</span>
      <span>{zhCN.columns.title}</span>
      <span>{zhCN.columns.album}</span>
      <span className="text-right">{zhCN.columns.duration}</span>
      <span className="text-center">{zhCN.columns.favorite}</span>
    </div>
  )
}

function LoadingRows(): JSX.Element {
  return (
    <div className="space-y-1 px-3 pt-2" aria-hidden="true">
      {Array.from({ length: 10 }, (_, index) => (
        <div key={index} className="flex h-11 items-center gap-3">
          <div className="h-3 w-4 animate-pulse rounded bg-bg-active" />
          <div className="h-8 w-8 animate-pulse rounded-[var(--radius-sm)] bg-bg-active" />
          <div className="h-3 flex-1 animate-pulse rounded bg-bg-active" />
          <div className="h-3 w-24 animate-pulse rounded bg-bg-active" />
        </div>
      ))}
    </div>
  )
}

/**
 * 歌曲列表（虚拟滚动）：同时服务于「歌曲 / 最近添加 / 我喜欢」三个视图，
 * 通过 preset 指定查询条件。
 */
export function TracksView({ preset, emptyTitle, emptyHint }: TracksViewProps): JSX.Element {
  const tracks = useLibraryStore((state) => state.tracks)
  const total = useLibraryStore((state) => state.total)
  const status = useLibraryStore((state) => state.tracksStatus)
  const error = useLibraryStore((state) => state.tracksError)
  const search = useLibraryStore((state) => state.search)
  const setQuery = useLibraryStore((state) => state.setQuery)
  const consumePendingQuery = useLibraryStore((state) => state.consumePendingQuery)
  const loadTracks = useLibraryStore((state) => state.loadTracks)
  const currentId = useQueueStore((state) => state.currentId)
  const playing = usePlayerStore((state) => state.status === 'playing')
  const [menu, setMenu] = useState<MenuState | null>(null)
  // StrictMode 下 effect 会挂载两次，用 ref 避免二次执行覆盖掉待处理的筛选条件。
  const initializedRef = useRef(false)

  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    // 从专辑/艺术家视图跳转过来时，合并其筛选条件。
    const pending = consumePendingQuery()
    setQuery(pending === null ? preset : { ...preset, ...pending })
    void loadTracks()
  }, [consumePendingQuery, loadTracks, preset, setQuery])

  const keyword = search.trim()
  const showEmpty = tracks.length === 0 && status !== 'loading' && status !== 'error'

  const menuItems: ContextMenuItem[] =
    menu === null
      ? []
      : [
          {
            id: 'play',
            label: zhCN.actions.play,
            icon: Play,
            onSelect: () => {
              playTracks(
                tracks,
                tracks.findIndex((item) => item.id === menu.track.id)
              )
            }
          },
          {
            id: 'play-next',
            label: zhCN.actions.playNext,
            icon: ListPlus,
            onSelect: () => playTrackNext(menu.track)
          },
          {
            id: 'enqueue',
            label: zhCN.actions.addToQueue,
            icon: ListEnd,
            onSelect: () => enqueueTracks([menu.track])
          },
          {
            id: 'favorite',
            label: menu.track.favorite ? zhCN.actions.removeFavorite : zhCN.actions.addFavorite,
            icon: Heart,
            separatorBefore: true,
            onSelect: () => {
              void useLibraryStore.getState().toggleFavorite(menu.track)
            }
          }
        ]

  if (status === 'error') {
    return (
      <EmptyState
        icon={CircleAlert}
        tone="error"
        title={zhCN.library.loadFailed}
        description={error ?? zhCN.errors.generic}
        action={
          <Button leadingIcon={<RefreshCw size={14} />} onClick={() => void loadTracks()}>
            {zhCN.common.retry}
          </Button>
        }
      />
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center justify-between gap-3 px-6 pb-1 pt-4">
        <p className="truncate text-xs text-fg-muted">
          {keyword.length > 0
            ? `${zhCN.search.label}：「${keyword}」 · ${zhCN.library.shownTracks(tracks.length, total)}`
            : zhCN.library.shownTracks(tracks.length, total)}
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          leadingIcon={<RefreshCw size={13} />}
          onClick={() => void loadTracks()}
        >
          {zhCN.common.refresh}
        </Button>
      </div>

      <div className="shrink-0 px-3">
        <ListHeader />
      </div>

      <div className="min-h-0 flex-1 px-3 pb-3">
        {status === 'loading' && tracks.length === 0 ? (
          <LoadingRows />
        ) : (
          <VirtualList
            items={tracks}
            estimateSize={ROW_HEIGHT}
            getItemKey={(track) => track.id}
            renderItem={(track, index) => (
              <TrackRow
                track={track}
                index={index}
                current={track.id === currentId}
                playing={playing}
                onPlay={() => playTracks(tracks, index)}
                onContextMenu={(x, y) => setMenu({ x, y, track })}
              />
            )}
            emptyState={
              showEmpty ? (
                <EmptyState
                  icon={CircleAlert}
                  title={keyword.length > 0 ? zhCN.library.emptySearch : emptyTitle}
                  description={
                    keyword.length > 0 ? zhCN.library.emptySearchHint(keyword) : emptyHint
                  }
                />
              ) : (
                <div />
              )
            }
          />
        )}
      </div>

      {menu !== null ? (
        <ContextMenu x={menu.x} y={menu.y} items={menuItems} onClose={() => setMenu(null)} />
      ) : null}
    </div>
  )
}
