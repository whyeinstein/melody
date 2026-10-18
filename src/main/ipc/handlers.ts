import { dialog } from 'electron'
import type { AppInfo } from '@shared/ipc/contracts'
import { listAlbums, listArtists, listGenres } from '../services/db/repositories/aggregates'
import { addFolder, listFolders, removeFolder } from '../services/db/repositories/folders'
import { listPlaylists } from '../services/db/repositories/playlists'
import { getTrack, markPlayed, queryTracks, setFavorite } from '../services/db/repositories/tracks'
import type { AppContext } from '../services/context'
import type { IpcHandlerMap } from './router'

/** 把服务容器映射成 IPC 处理器表；未列出的频道由 router 跳过。 */
export function createHandlers(
  context: AppContext,
  getAppInfo: () => Promise<AppInfo>
): IpcHandlerMap {
  const { db, config, scanner, media } = context

  return {
    'app:info': () => getAppInfo(),

    'config:get': () => config.get(),
    'config:set': (patch) => config.update(patch),

    'library:chooseFolder': async () => {
      const result = await dialog.showOpenDialog({
        title: '选择音乐文件夹',
        properties: ['openDirectory', 'multiSelections']
      })
      return result.canceled ? [] : result.filePaths
    },
    'library:addFolder': ({ path }) => addFolder(db, path, Date.now()),
    'library:removeFolder': ({ id }) => {
      removeFolder(db, id)
    },
    'library:listFolders': () => listFolders(db),
    'library:startScan': () => {
      if (!scanner.isRunning()) void scanner.scan()
      return scanner.getProgress()
    },
    'library:cancelScan': () => {
      scanner.cancel()
    },
    'library:scanStatus': () => scanner.getProgress(),

    'tracks:query': (query) => queryTracks(db, query),
    'tracks:get': ({ id }) => getTrack(db, id),
    'tracks:setFavorite': ({ id, favorite }) => {
      setFavorite(db, id, favorite)
    },
    'tracks:markPlayed': ({ id }) => {
      markPlayed(db, id, Date.now())
    },

    'albums:list': () => listAlbums(db),
    'artists:list': () => listArtists(db),
    'genres:list': () => listGenres(db),
    'playlists:list': () => listPlaylists(db),

    'media:session': () => ({ baseUrl: media.baseUrl, token: media.token })
  }
}
