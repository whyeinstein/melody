import type {
  IpcChannel,
  IpcError,
  IpcEventChannel,
  IpcEventMap,
  IpcRequest,
  IpcResponse,
  IpcResult
} from '@shared/ipc/contracts'
import { zhCN } from '../i18n/zh-CN'

/**
 * 渲染层访问主进程的唯一入口。
 *
 * 所有 IPC 调用都必须经过这里：
 * - 桥（preload）不存在、频道未注册、调用被拒绝时都返回结构化的 IpcResult，
 *   绝不向调用方抛出异常，界面据此展示空状态/错误提示即可。
 */
export function errorMessage(reason: unknown): string {
  if (reason instanceof Error) return reason.message
  if (typeof reason === 'string') return reason
  try {
    return JSON.stringify(reason)
  } catch {
    return String(reason)
  }
}

export function hasBridge(): boolean {
  if (typeof window === 'undefined') return false
  const bridge = window.melody
  return typeof bridge === 'object' && bridge !== null && typeof bridge.invoke === 'function'
}

const NO_BRIDGE: IpcError = { code: 'E_NO_BRIDGE', message: zhCN.errors.bridgeMissing }

function normalizeError(reason: unknown): IpcError {
  const message = errorMessage(reason)
  // 主进程没有注册 handler 时，ipcRenderer.invoke 会 reject，这里归一化为可识别的错误码，
  // 便于界面区分「功能未实现」和真正的故障。
  if (message.includes('No handler registered')) {
    return { code: 'E_NO_HANDLER', message }
  }
  return { code: 'E_IPC_REJECTED', message }
}

export async function invoke<C extends IpcChannel>(
  channel: C,
  payload?: IpcRequest<C>
): Promise<IpcResult<IpcResponse<C>>> {
  if (!hasBridge()) return { ok: false, error: NO_BRIDGE }
  try {
    return await window.melody.invoke(channel, payload)
  } catch (reason) {
    return { ok: false, error: normalizeError(reason) }
  }
}

/** 频道/桥尚未就绪：属于可预期的降级场景，界面应显示「功能尚未就绪」而不是故障。 */
export function isChannelUnavailable(error: IpcError): boolean {
  return error.code === 'E_NO_BRIDGE' || error.code === 'E_UNKNOWN_CHANNEL' || error.code === 'E_NO_HANDLER'
}

/** 把 IPC 错误翻译成适合展示给用户的中文文案。 */
export function describeIpcError(error: IpcError): string {
  if (error.code === 'E_NO_BRIDGE') return zhCN.errors.bridgeMissing
  if (isChannelUnavailable(error)) return `${zhCN.errors.channelNotReady}（${error.code}）`
  return error.message.length > 0 ? error.message : zhCN.errors.generic
}

/**
 * 订阅主进程推送事件（例如 scan:progress）。
 * 桥或事件频道不可用时返回空取消函数，调用方无需做额外判断。
 */
export function subscribe<C extends IpcEventChannel>(
  channel: C,
  listener: (payload: IpcEventMap[C]) => void
): () => void {
  if (typeof window === 'undefined') return () => {}
  const bridge = window.melody
  if (typeof bridge !== 'object' || bridge === null || typeof bridge.on !== 'function') {
    return () => {}
  }
  try {
    return bridge.on(channel, listener)
  } catch {
    return () => {}
  }
}
