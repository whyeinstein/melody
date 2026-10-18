import { ipcMain } from 'electron'
import type { AppInfo, IpcResult } from '@shared/ipc/contracts'
import { errorMessage } from '../services/logging'

export function registerIpcHandlers(getAppInfo: () => Promise<AppInfo>): void {
  ipcMain.handle('app:info', async (): Promise<IpcResult<AppInfo>> => {
    try {
      return { ok: true, data: await getAppInfo() }
    } catch (error) {
      return { ok: false, error: { code: 'E_APP_INFO', message: errorMessage(error) } }
    }
  })
}
