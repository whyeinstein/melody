import type { IpcChannel, IpcRequest, IpcResponse, IpcResult } from './contracts'

/** preload 通过 contextBridge 暴露给渲染进程的唯一入口。 */
export interface MelodyBridge {
  invoke<C extends IpcChannel>(channel: C, payload?: IpcRequest<C>): Promise<IpcResult<IpcResponse<C>>>
  readonly platform: string
}
