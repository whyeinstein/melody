import { BrowserWindow } from 'electron'
import type { IpcEventChannel, IpcEventMap } from '@shared/ipc/contracts'

/** 向所有仍存活的窗口广播主进程事件。 */
export function broadcast<C extends IpcEventChannel>(channel: C, payload: IpcEventMap[C]): void {
  for (const window of BrowserWindow.getAllWindows()) {
    if (window.isDestroyed()) continue
    window.webContents.send(channel, payload)
  }
}
