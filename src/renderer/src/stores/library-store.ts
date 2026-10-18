import type {
  AlbumSummary,
  ArtistSummary,
  GenreSummary,
  LibraryFolder,
  Playlist,
  ScanProgress,
  Track,
  TrackQuery
} from '@shared/domain/types'
import { EMPTY_SCAN_PROGRESS } from '@shared/domain/types'
import type { IpcResult } from '@shared/ipc/contracts'
import { create } from 'zustand'
import { zhCN } from '../i18n/zh-CN'
import { describeIpcError, invoke, isChannelUnavailable } from '../lib/ipc'
import { useQueueStore } from './queue-store'
import { useUiStore } from './ui-store'

export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error'

export type CollectionKey = 'folders' | 'albums' | 'artists' | 'genres' | 'playlists'

/** 默认查询：按标题升序，主进程可以据此返回全部歌曲。 */
const DEFAULT_QUERY: TrackQuery = { sort: 'title', direction: 'asc' }

/** 一次最多拉取的歌曲数量（虚拟列表负责渲染，不受此限制影响）。 */
const TRACK_PAGE_LIMIT = 2000

const emptyCollectionStatus: Record<CollectionKey, LoadStatus> = {
  folders: 'idle',
  albums: 'idle',
  artists: 'idle',
  genres: 'idle',
  playlists: 'idle'
}

const emptyCollectionUnavailable: Record<CollectionKey, boolean> = {
  folders: false,
  albums: false,
  artists: false,
  genres: false,
  playlists: false
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
let scanTimer: ReturnType<typeof setInterval> | null = null
let tracksRequestSeq = 0

export interface LibraryState {
  tracks: Track[]
  total: number
  tracksStatus: LoadStatus
  tracksError: string | null
  query: TrackQuery
  search: string
  /** 从专辑/艺术家视图跳转到歌曲视图时携带的筛选条件。 */
  pendingQuery: TrackQuery | null

  folders: LibraryFolder[]
  albums: AlbumSummary[]
  artists: ArtistSummary[]
  genres: GenreSummary[]
  playlists: Playlist[]
  collectionStatus: Record<CollectionKey, LoadStatus>
  collectionErrors: Partial<Record<CollectionKey, string>>
  collectionUnavailable: Record<CollectionKey, boolean>

  scan: ScanProgress
  scanError: string | null

  setSearch: (text: string) => void
  setQuery: (query: TrackQuery) => void
  setPendingQuery: (query: TrackQuery) => void
  consumePendingQuery: () => TrackQuery | null

  loadTracks: () => Promise<void>
  loadFolders: () => Promise<void>
  loadAlbums: () => Promise<void>
  loadArtists: () => Promise<void>
  loadGenres: () => Promise<void>
  loadPlaylists: () => Promise<void>
  refreshAll: () => Promise<void>
  refreshScanStatus: () => Promise<void>
  /** 接收主进程 scan:progress 推送（扫描进度实时更新）。 */
  applyScanProgress: (progress: ScanProgress) => void

  addFolders: () => Promise<void>
  removeFolder: (id: number) => Promise<void>
  startScan: () => Promise<void>
  cancelScan: () => Promise<void>
  stopScanPolling: () => void

  toggleFavorite: (track: Track) => Promise<void>
}

/** 把搜索词合并进查询条件（空搜索词时移除该字段，避免主进程收到空字符串）。 */
function withSearch(query: TrackQuery, search: string): TrackQuery {
  const keyword = search.trim()
  if (keyword.length === 0) {
    const { search: _removed, ...rest } = query
    return rest
  }
  return { ...query, search: keyword }
}

export const useLibraryStore = create<LibraryState>()((set, get) => {
  const stopScanPolling = (): void => {
    if (scanTimer !== null) {
      clearInterval(scanTimer)
      scanTimer = null
    }
  }

  const pollScanStatus = async (): Promise<void> => {
    const result = await invoke('library:scanStatus')
    if (!result.ok) {
      stopScanPolling()
      set({ scanError: describeIpcError(result.error) })
      return
    }
    set({ scan: result.data, scanError: null })
    if (result.data.state !== 'scanning') {
      stopScanPolling()
      if (result.data.state === 'done') void get().refreshAll()
    }
  }

  const startScanPolling = (): void => {
    stopScanPolling()
    scanTimer = setInterval(() => {
      void pollScanStatus()
    }, 800)
  }

  /** 加载一个聚合集合（专辑/艺术家/流派/文件夹/播放列表），失败时只标记该集合不可用。 */
  const loadCollection = async <T>(
    key: CollectionKey,
    loader: () => Promise<IpcResult<T>>,
    onData: (data: T) => void
  ): Promise<void> => {
    set((state) => ({
      collectionStatus: { ...state.collectionStatus, [key]: 'loading' },
      collectionErrors: { ...state.collectionErrors, [key]: undefined }
    }))
    const result = await loader()
    if (result.ok) {
      onData(result.data)
      set((state) => ({
        collectionStatus: { ...state.collectionStatus, [key]: 'ready' },
        collectionUnavailable: { ...state.collectionUnavailable, [key]: false }
      }))
      return
    }
    set((state) => ({
      collectionStatus: { ...state.collectionStatus, [key]: 'error' },
      collectionErrors: { ...state.collectionErrors, [key]: describeIpcError(result.error) },
      collectionUnavailable: { ...state.collectionUnavailable, [key]: isChannelUnavailable(result.error) }
    }))
  }

  return {
    tracks: [],
    total: 0,
    tracksStatus: 'idle',
    tracksError: null,
    query: { ...DEFAULT_QUERY },
    search: '',
    pendingQuery: null,

    folders: [],
    albums: [],
    artists: [],
    genres: [],
    playlists: [],
    collectionStatus: { ...emptyCollectionStatus },
    collectionErrors: {},
    collectionUnavailable: { ...emptyCollectionUnavailable },

    scan: { ...EMPTY_SCAN_PROGRESS },
    scanError: null,

    setSearch: (text) => {
      set({ search: text })
      if (searchTimer !== null) clearTimeout(searchTimer)
      // 输入防抖：避免每个按键都触发一次 IPC 查询。
      searchTimer = setTimeout(() => {
        searchTimer = null
        void get().loadTracks()
      }, 250)
    },

    setQuery: (query) => set({ query: { ...query }, pendingQuery: null }),

    setPendingQuery: (query) => set({ pendingQuery: { ...query } }),

    consumePendingQuery: () => {
      const pending = get().pendingQuery
      if (pending !== null) set({ pendingQuery: null })
      return pending
    },

    loadTracks: async () => {
      tracksRequestSeq += 1
      const requestSeq = tracksRequestSeq
      set({ tracksStatus: 'loading', tracksError: null })
      const result = await invoke('tracks:query', {
        ...withSearch(get().query, get().search),
        offset: 0,
        limit: TRACK_PAGE_LIMIT
      })
      // 只接受最后一次请求的结果，避免快速切换视图/输入时旧结果覆盖新结果。
      if (requestSeq !== tracksRequestSeq) return
      if (result.ok) {
        set({ tracks: result.data.items, total: result.data.total, tracksStatus: 'ready' })
      } else {
        set({
          tracks: [],
          total: 0,
          tracksStatus: 'error',
          tracksError: describeIpcError(result.error)
        })
      }
    },

    loadFolders: () =>
      loadCollection('folders', () => invoke('library:listFolders'), (data) => set({ folders: data })),

    loadAlbums: () => loadCollection('albums', () => invoke('albums:list'), (data) => set({ albums: data })),

    loadArtists: () =>
      loadCollection('artists', () => invoke('artists:list'), (data) => set({ artists: data })),

    loadGenres: () => loadCollection('genres', () => invoke('genres:list'), (data) => set({ genres: data })),

    loadPlaylists: () =>
      loadCollection('playlists', () => invoke('playlists:list'), (data) => set({ playlists: data })),

    refreshAll: async () => {
      await Promise.all([
        get().loadTracks(),
        get().loadFolders(),
        get().loadAlbums(),
        get().loadArtists(),
        get().loadGenres(),
        get().loadPlaylists(),
        get().refreshScanStatus()
      ])
    },

    refreshScanStatus: async () => {
      const result = await invoke('library:scanStatus')
      if (result.ok) set({ scan: result.data })
      else set({ scanError: describeIpcError(result.error) })
    },

    applyScanProgress: (progress) => {
      set({ scan: progress, scanError: null })
      if (progress.state === 'scanning') return
      // 扫描结束：停止轮询兜底，并在成功完成时刷新音乐库。
      stopScanPolling()
      if (progress.state === 'done') void get().refreshAll()
    },

    addFolders: async () => {
      const chosen = await invoke('library:chooseFolder')
      if (!chosen.ok) {
        useUiStore.getState().pushToast({
          kind: 'error',
          title: zhCN.errors.folderChooseFailed,
          description: describeIpcError(chosen.error)
        })
        return
      }
      if (chosen.data.length === 0) return
      let added = 0
      for (const folderPath of chosen.data) {
        const result = await invoke('library:addFolder', { path: folderPath })
        if (result.ok) added += 1
        else {
          useUiStore.getState().pushToast({
            kind: 'error',
            title: zhCN.errors.folderAddFailed,
            description: describeIpcError(result.error)
          })
        }
      }
      if (added > 0) {
        await get().loadFolders()
        useUiStore.getState().pushToast({ kind: 'success', title: zhCN.toasts.foldersAdded(added) })
      }
    },

    removeFolder: async (id) => {
      const result = await invoke('library:removeFolder', { id })
      if (!result.ok) {
        useUiStore.getState().pushToast({
          kind: 'error',
          title: zhCN.errors.folderRemoveFailed,
          description: describeIpcError(result.error)
        })
        return
      }
      await Promise.all([get().loadFolders(), get().loadTracks()])
    },

    startScan: async () => {
      const result = await invoke('library:startScan')
      if (!result.ok) {
        set({ scanError: describeIpcError(result.error) })
        useUiStore.getState().pushToast({
          kind: 'error',
          title: zhCN.errors.scanStartFailed,
          description: describeIpcError(result.error)
        })
        return
      }
      set({ scan: result.data, scanError: null })
      useUiStore.getState().pushToast({ kind: 'info', title: zhCN.toasts.scanStarted })
      if (result.data.state === 'scanning') startScanPolling()
    },

    cancelScan: async () => {
      const result = await invoke('library:cancelScan')
      if (!result.ok) {
        set({ scanError: describeIpcError(result.error) })
        return
      }
      stopScanPolling()
      await get().refreshScanStatus()
      useUiStore.getState().pushToast({ kind: 'info', title: zhCN.toasts.scanCancelled })
    },

    stopScanPolling,

    toggleFavorite: async (track) => {
      const favorite = !track.favorite
      // 乐观更新，失败时回滚（列表与播放队列同时同步）。
      set((state) => ({
        tracks: state.tracks.map((item) => (item.id === track.id ? { ...item, favorite } : item))
      }))
      useQueueStore.getState().setFavorite(track.id, favorite)
      const result = await invoke('tracks:setFavorite', { id: track.id, favorite })
      if (result.ok) {
        useUiStore.getState().pushToast({
          kind: 'success',
          title: favorite ? zhCN.toasts.favoriteAdded : zhCN.toasts.favoriteRemoved
        })
        return
      }
      set((state) => ({
        tracks: state.tracks.map((item) => (item.id === track.id ? { ...item, favorite: track.favorite } : item))
      }))
      useQueueStore.getState().setFavorite(track.id, track.favorite)
      useUiStore.getState().pushToast({
        kind: 'error',
        title: zhCN.errors.favoriteFailed,
        description: describeIpcError(result.error)
      })
    }
  }
})
