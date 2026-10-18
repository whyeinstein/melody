import { app, BrowserWindow } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { AppInfo } from '@shared/ipc/contracts'
import { createMainWindow } from './window'
import { registerIpcHandlers } from './ipc'
import { probeStorage } from './services/storage/probe'
import { probeFfmpeg } from './services/media/ffmpeg'
import { errorMessage, logError, logInfo } from './services/logging'

let mainWindow: BrowserWindow | null = null
let appInfoPromise: Promise<AppInfo> | null = null

function getAppInfo(): Promise<AppInfo> {
  appInfoPromise ??= (async () => {
    const [storage, ffmpeg] = await Promise.all([probeStorage(), probeFfmpeg()])
    return {
      name: 'Melody',
      version: app.getVersion(),
      electron: process.versions.electron ?? 'unknown',
      chrome: process.versions.chrome ?? 'unknown',
      node: process.versions.node ?? 'unknown',
      platform: process.platform,
      arch: process.arch,
      isPackaged: app.isPackaged,
      userDataPath: app.getPath('userData'),
      storage,
      ffmpeg
    }
  })()
  return appInfoPromise
}

function focusMainWindow(): void {
  if (!mainWindow) {
    mainWindow = createMainWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.focus()
}

function bootstrap(): void {
  registerIpcHandlers(getAppInfo)

  const headless = process.env['MELODY_HEADLESS'] === '1'

  if (!headless) {
    mainWindow = createMainWindow()
    mainWindow.on('closed', () => {
      mainWindow = null
    })
  }

  void getAppInfo()
    .then((info) => {
      logInfo(
        `启动完成 headless=${headless} electron=${info.electron} chrome=${info.chrome} node=${info.node} ` +
          `storage=${info.storage.engine}(${info.storage.ok ? 'ok' : 'unavailable'}) ` +
          `ffmpeg=${info.ffmpeg.found ? (info.ffmpeg.version ?? 'found') : 'missing'}`
      )
      if (headless || process.env['MELODY_SMOKE'] === '1') {
        setTimeout(() => app.quit(), 1500)
      }
      if (process.env['MELODY_SMOKE'] === '1') {
        const outPath = process.env['MELODY_SMOKE_OUT'] ?? join(app.getPath('userData'), 'smoke-appinfo.json')
        try {
          mkdirSync(dirname(outPath), { recursive: true })
          writeFileSync(outPath, JSON.stringify(info, null, 2), 'utf8')
        } catch (error) {
          logError('写入冒烟结果失败:', errorMessage(error))
        }
      }
    })
    .catch((error: unknown) => logError('读取应用信息失败:', errorMessage(error)))
}

const hasSingleInstanceLock = app.requestSingleInstanceLock()
if (!hasSingleInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', focusMainWindow)
  app.whenReady().then(bootstrap).catch((error: unknown) => {
    logError('应用启动失败:', errorMessage(error))
    app.quit()
  })
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) focusMainWindow()
  })
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
  })
}
