import { ipcMain } from 'electron'
import type { IpcChannel, IpcError, IpcRequest, IpcResponse, IpcResult } from '@shared/ipc/contracts'
import { IPC_CHANNELS, ipcRequestSchemas } from '@shared/ipc/contracts'
import { ZodError } from 'zod'
import { errorMessage } from '../services/logging'

export type IpcHandler<C extends IpcChannel> = (
  payload: IpcRequest<C>
) => Promise<IpcResponse<C>> | IpcResponse<C>

export type IpcHandlerMap = { [C in IpcChannel]?: IpcHandler<C> }

function toIpcError(error: unknown): IpcError {
  if (error instanceof ZodError) {
    const detail = error.issues
      .map((issue) => `${issue.path.join('.') || '<payload>'}: ${issue.message}`)
      .join('; ')
    return { code: 'E_INVALID_ARGUMENT', message: detail }
  }
  return { code: 'E_INTERNAL', message: errorMessage(error) }
}

/**
 * 统一注册 IPC：请求先用 zod 校验，再交给具体处理器，
 * 所有异常都转成 `{ ok:false, error }` 信封，渲染进程不会收到未捕获的 rejection。
 */
export function registerIpcRouter(handlers: IpcHandlerMap): void {
  for (const channel of IPC_CHANNELS) {
    const handler = handlers[channel]
    if (!handler) continue

    ipcMain.handle(channel, async (_event, rawPayload: unknown): Promise<IpcResult<unknown>> => {
      try {
        const schema = ipcRequestSchemas[channel]
        const payload = schema ? schema.parse(rawPayload) : rawPayload
        const data = await (handler as IpcHandler<IpcChannel>)(payload as IpcRequest<IpcChannel>)
        return { ok: true, data }
      } catch (error) {
        return { ok: false, error: toIpcError(error) }
      }
    })
  }
}
