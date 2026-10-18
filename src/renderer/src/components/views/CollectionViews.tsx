import { Fragment, useEffect } from 'react'
import type { JSX } from 'react'
import type { AlbumSummary, ArtistSummary, GenreSummary, Playlist } from '@shared/domain/types'
import { CircleAlert, Disc3, Inbox, Library, LoaderCircle, Tags, Users, WifiOff } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { formatDate, formatTotalDuration } from '../../lib/format'
import { useLibraryStore, type LoadStatus } from '../../stores/library-store'
import { useUiStore } from '../../stores/ui-store'
import { Button } from '../ui/Button'
import { CoverArt } from '../ui/CoverArt'
import { EmptyState } from '../ui/EmptyState'

interface CollectionGridProps<T> {
  items: readonly T[]
  status: LoadStatus
  error: string | null
  unavailable: boolean
  emptyTitle: string
  emptyHint: string
  onRetry: () => void
  getKey: (item: T) => string
  renderCard: (item: T) => JSX.Element
}

function LoadingHint(): JSX.Element {
  return (
    <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-muted">
      <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
      {zhCN.common.loading}
    </div>
  )
}

function CollectionGrid<T>({
  items,
  status,
  error,
  unavailable,
  emptyTitle,
  emptyHint,
  onRetry,
  getKey,
  renderCard
}: CollectionGridProps<T>): JSX.Element {
  if (status === 'loading' && items.length === 0) return <LoadingHint />

  if (status === 'error') {
    return (
      <EmptyState
        icon={unavailable ? WifiOff : CircleAlert}
        tone={unavailable ? 'default' : 'error'}
        title={unavailable ? zhCN.library.channelNotReady : zhCN.library.loadFailed}
        description={
          unavailable ? zhCN.library.channelNotReadyHint : (error ?? zhCN.errors.generic)
        }
        action={<Button onClick={onRetry}>{zhCN.common.retry}</Button>}
      />
    )
  }

  if (items.length === 0) {
    return <EmptyState icon={Inbox} title={emptyTitle} description={emptyHint} />
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Fragment key={getKey(item)}>{renderCard(item)}</Fragment>
        ))}
      </div>
    </div>
  )
}

function CollectionCard({
  icon: Icon,
  title,
  subtitle,
  coverId,
  onOpen
}: {
  icon: LucideIcon
  title: string
  subtitle: string
  coverId?: number | null
  onOpen?: () => void
}): JSX.Element {
  const leading =
    coverId === undefined || coverId === null ? (
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-bg-active text-fg-muted transition-colors group-hover:text-accent">
        <Icon size={20} aria-hidden="true" />
      </div>
    ) : (
      <CoverArt coverId={coverId} size={48} />
    )

  const content = (
    <>
      {leading}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-fg">{title}</p>
        <p className="truncate text-xs text-fg-muted">{subtitle}</p>
      </div>
    </>
  )

  if (onOpen === undefined) {
    return (
      <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-bg-elevated p-3">
        {content}
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-bg-elevated p-3 text-left transition-colors hover:border-accent/40 hover:bg-bg-hover"
    >
      {content}
    </button>
  )
}

function useCollection(
  key: 'albums' | 'artists' | 'genres' | 'playlists',
  loader: () => Promise<void>
): {
  status: LoadStatus
  error: string | null
  unavailable: boolean
  retry: () => void
} {
  const status = useLibraryStore((state) => state.collectionStatus[key])
  const error = useLibraryStore((state) => state.collectionErrors[key])
  const unavailable = useLibraryStore((state) => state.collectionUnavailable[key])

  // 只在首次进入视图（空闲态）时自动加载，失败后由用户点击「重试」。
  useEffect(() => {
    if (status === 'idle') void loader()
  }, [loader, status])

  return { status, error: error ?? null, unavailable, retry: () => void loader() }
}

/** 专辑视图：点击专辑跳转到歌曲视图并按专辑筛选。 */
export function AlbumsView(): JSX.Element {
  const albums = useLibraryStore((state) => state.albums)
  const loadAlbums = useLibraryStore((state) => state.loadAlbums)
  const setPendingQuery = useLibraryStore((state) => state.setPendingQuery)
  const setActiveView = useUiStore((state) => state.setActiveView)
  const collection = useCollection('albums', loadAlbums)

  const openAlbum = (album: AlbumSummary): void => {
    const query = album.albumArtist === null
      ? { album: album.name }
      : { album: album.name, artist: album.albumArtist }
    setPendingQuery(query)
    setActiveView('songs')
  }

  return (
    <CollectionGrid
      items={albums}
      status={collection.status}
      error={collection.error}
      unavailable={collection.unavailable}
      emptyTitle={zhCN.library.emptyAlbums}
      emptyHint={zhCN.library.emptyAlbumsHint}
      onRetry={collection.retry}
      getKey={(album) => `${album.name}::${album.albumArtist ?? ''}`}
      renderCard={(album) => (
        <CollectionCard
          icon={Disc3}
          title={album.name}
          coverId={album.coverId}
          subtitle={`${album.albumArtist ?? zhCN.common.unknownArtist} · ${album.year ?? '—'} · ${zhCN.common.count(album.trackCount)} · ${formatTotalDuration(album.durationMs)}`}
          onOpen={() => openAlbum(album)}
        />
      )}
    />
  )
}

/** 艺术家视图：点击艺术家跳转到歌曲视图并按艺术家筛选。 */
export function ArtistsView(): JSX.Element {
  const artists = useLibraryStore((state) => state.artists)
  const loadArtists = useLibraryStore((state) => state.loadArtists)
  const setPendingQuery = useLibraryStore((state) => state.setPendingQuery)
  const setActiveView = useUiStore((state) => state.setActiveView)
  const collection = useCollection('artists', loadArtists)

  return (
    <CollectionGrid
      items={artists}
      status={collection.status}
      error={collection.error}
      unavailable={collection.unavailable}
      emptyTitle={zhCN.library.emptyArtists}
      emptyHint={zhCN.library.emptyArtistsHint}
      onRetry={collection.retry}
      getKey={(artist) => artist.name}
      renderCard={(artist: ArtistSummary) => (
        <CollectionCard
          icon={Users}
          title={artist.name}
          subtitle={`${zhCN.common.count(artist.trackCount)} · ${zhCN.common.albumCount(artist.albumCount)}`}
          onOpen={() => {
            setPendingQuery({ artist: artist.name })
            setActiveView('songs')
          }}
        />
      )}
    />
  )
}

/** 流派视图：点击流派跳转到歌曲视图并按流派筛选。 */
export function GenresView(): JSX.Element {
  const genres = useLibraryStore((state) => state.genres)
  const loadGenres = useLibraryStore((state) => state.loadGenres)
  const setPendingQuery = useLibraryStore((state) => state.setPendingQuery)
  const setActiveView = useUiStore((state) => state.setActiveView)
  const collection = useCollection('genres', loadGenres)

  return (
    <CollectionGrid
      items={genres}
      status={collection.status}
      error={collection.error}
      unavailable={collection.unavailable}
      emptyTitle={zhCN.library.emptyGenres}
      emptyHint={zhCN.library.emptyGenresHint}
      onRetry={collection.retry}
      getKey={(genre) => genre.name}
      renderCard={(genre: GenreSummary) => (
        <CollectionCard
          icon={Tags}
          title={genre.name}
          subtitle={zhCN.common.count(genre.trackCount)}
          onOpen={() => {
            setPendingQuery({ genre: genre.name })
            setActiveView('songs')
          }}
        />
      )}
    />
  )
}

/** 播放列表视图（阶段 1 仅展示，创建/编辑在阶段 2 提供）。 */
export function PlaylistsView(): JSX.Element {
  const playlists = useLibraryStore((state) => state.playlists)
  const loadPlaylists = useLibraryStore((state) => state.loadPlaylists)
  const collection = useCollection('playlists', loadPlaylists)

  return (
    <CollectionGrid
      items={playlists}
      status={collection.status}
      error={collection.error}
      unavailable={collection.unavailable}
      emptyTitle={zhCN.library.emptyPlaylists}
      emptyHint={zhCN.library.emptyPlaylistsHint}
      onRetry={collection.retry}
      getKey={(playlist) => String(playlist.id)}
      renderCard={(playlist: Playlist) => (
        <CollectionCard
          icon={Library}
          title={playlist.name}
          subtitle={`${zhCN.common.count(playlist.trackCount)} · ${formatDate(playlist.updatedAt)}`}
        />
      )}
    />
  )
}
