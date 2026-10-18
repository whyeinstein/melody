import type {
  IpcChannel,
  IpcEventChannel,
  IpcEventMap,
  IpcRequest,
  IpcResponse,
  IpcResult
} from './contracts'

/** preload 通过 contextBridge 暴露给渲染进程的唯一入口。 */
export interface MelodyBridge {
  invoke<C extends IpcChannel>(channel: C, payload?: IpcRequest<C>): Promise<IpcResult<IpcResponse<C>>>
  /** 订阅主进程推送；返回取消订阅函数。 */
  on<C extends IpcEventChannel>(channel: C, listener: (payload: IpcEventMap[C]) => void): () => void
  readonly platform: string
}
