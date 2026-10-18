import type { JSX } from 'react'
import type { TrackQuery } from '@shared/domain/types'
import { zhCN } from '../../i18n/zh-CN'
import { useUiStore } from '../../stores/ui-store'
import { AlbumsView, ArtistsView, GenresView, PlaylistsView } from './CollectionViews'
import { FoldersView } from './FoldersView'
import { TracksView } from './TracksView'

/** 预置查询条件使用模块级常量，保证引用稳定，避免视图重复加载。 */
const SONGS_PRESET: TrackQuery = { sort: 'title', direction: 'asc' }
const FAVORITES_PRESET: TrackQuery = { favorite: true, sort: 'title', direction: 'asc' }
const RECENT_PRESET: TrackQuery = { sort: 'addedAt', direction: 'desc' }

/** 主内容区的视图路由。 */
export function LibraryView(): JSX.Element {
  const activeView = useUiStore((state) => state.activeView)

  switch (activeView) {
    case 'songs':
      return (
        <TracksView
          preset={SONGS_PRESET}
          emptyTitle={zhCN.library.emptyTitle}
          emptyHint={zhCN.library.emptyHint}
        />
      )
    case 'favorites':
      return (
        <TracksView
          preset={FAVORITES_PRESET}
          emptyTitle={zhCN.library.emptyFavorites}
          emptyHint={zhCN.library.emptyFavoritesHint}
        />
      )
    case 'recent':
      return (
        <TracksView
          preset={RECENT_PRESET}
          emptyTitle={zhCN.library.emptyRecent}
          emptyHint={zhCN.library.emptyRecentHint}
        />
      )
    case 'albums':
      return <AlbumsView />
    case 'artists':
      return <ArtistsView />
    case 'genres':
      return <GenresView />
    case 'folders':
      return <FoldersView />
    case 'playlists':
      return <PlaylistsView />
    default:
      return <div />
  }
}
