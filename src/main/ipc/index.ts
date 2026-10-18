import type { AppInfo } from '@shared/ipc/contracts'
import type { AppContext } from '../services/context'
import { createHandlers } from './handlers'
import { registerIpcRouter } from './router'

export function registerIpcHandlers(context: AppContext, getAppInfo: () => Promise<AppInfo>): void {
  registerIpcRouter(createHandlers(context, getAppInfo))
}
