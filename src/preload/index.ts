import { contextBridge, ipcRenderer } from 'electron'
import type { MelodyBridge } from '@shared/ipc/api'
import type {
  IpcChannel,
  IpcEventChannel,
  IpcEventMap,
  IpcRequest,
  IpcResponse,
  IpcResult
} from '@shared/ipc/contracts'

/**
 * preload 在 sandbox 下运行，不能依赖任何第三方运行时模块，
 * 因此频道白名单在这里显式维护（与 shared/ipc/contracts.ts 保持同步）。
 */
const ALLOWED_CHANNELS: ReadonlySet<string> = new Set<IpcChannel>([
  'app:info',
  'config:get',
  'config:set',
  'library:chooseFolder',
  'library:addFolder',
  'library:removeFolder',
  'library:listFolders',
  'library:startScan',
  'library:cancelScan',
  'library:scanStatus',
  'tracks:query',
  'tracks:get',
  'tracks:setFavorite',
  'tracks:markPlayed',
  'albums:list',
  'artists:list',
  'genres:list',
  'playlists:list',
  'media:session'
])

const ALLOWED_EVENTS: ReadonlySet<string> = new Set<IpcEventChannel>(['scan:progress'])

const bridge: MelodyBridge = {
  invoke<C extends IpcChannel>(
    channel: C,
    payload?: IpcRequest<C>
  ): Promise<IpcResult<IpcResponse<C>>> {
    if (!ALLOWED_CHANNELS.has(channel)) {
      return Promise.resolve({
        ok: false,
        error: { code: 'E_UNKNOWN_CHANNEL', message: `未知的 IPC 频道: ${String(channel)}` }
      })
    }
    return ipcRenderer.invoke(channel, payload) as Promise<IpcResult<IpcResponse<C>>>
  },

  on<C extends IpcEventChannel>(channel: C, listener: (payload: IpcEventMap[C]) => void): () => void {
    if (!ALLOWED_EVENTS.has(channel)) return () => {}
    const wrapped = (_event: unknown, payload: IpcEventMap[C]): void => listener(payload)
    ipcRenderer.on(channel, wrapped as never)
    return () => {
      ipcRenderer.removeListener(channel, wrapped as never)
    }
  },

  platform: process.platform
}

contextBridge.exposeInMainWorld('melody', bridge)
