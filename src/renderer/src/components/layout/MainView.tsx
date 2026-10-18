import type { JSX } from 'react'
import { ListMusic } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { useLibraryStore } from '../../stores/library-store'
import { useUiStore, type NavView } from '../../stores/ui-store'
import { IconButton } from '../ui/IconButton'
import { LibraryView } from '../views/LibraryView'
import { SearchField } from './SearchField'

interface Counts {
  tracks: number
  albums: number
  artists: number
  genres: number
  folders: number
  playlists: number
}

function subtitleFor(view: NavView, counts: Counts): string {
  switch (view) {
    case 'songs':
    case 'favorites':
    case 'recent':
      return zhCN.library.totalTracks(counts.tracks)
    case 'albums':
      return zhCN.common.albumCount(counts.albums)
    case 'artists':
      return zhCN.common.artistCount(counts.artists)
    case 'genres':
      return zhCN.common.genreCount(counts.genres)
    case 'folders':
      return zhCN.common.folderCount(counts.folders)
    case 'playlists':
      return zhCN.common.playlistCount(counts.playlists)
  }
}

/** 主内容区：顶栏（标题/搜索/队列开关）+ 当前视图。 */
export function MainView(): JSX.Element {
  const activeView = useUiStore((state) => state.activeView)
  const queueOpen = useUiStore((state) => state.queueOpen)
  const toggleQueue = useUiStore((state) => state.toggleQueue)

  const tracks = useLibraryStore((state) => state.total)
  const albums = useLibraryStore((state) => state.albums.length)
  const artists = useLibraryStore((state) => state.artists.length)
  const genres = useLibraryStore((state) => state.genres.length)
  const folders = useLibraryStore((state) => state.folders.length)
  const playlists = useLibraryStore((state) => state.playlists.length)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border px-6">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold text-fg">{zhCN.views[activeView]}</h1>
          <p className="truncate text-xs text-fg-muted">
            {subtitleFor(activeView, { tracks, albums, artists, genres, folders, playlists })}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <SearchField />
          <IconButton
            icon={ListMusic}
            label={queueOpen ? zhCN.queue.close : zhCN.player.queue}
            active={queueOpen}
            onClick={() => toggleQueue()}
          />
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-hidden">
        <LibraryView />
      </div>
    </div>
  )
}
