import { app, BrowserWindow } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { AppInfo } from '@shared/ipc/contracts'
import { createMainWindow } from './window'
import { registerIpcHandlers } from './ipc'
import { createAppContext, type AppContext } from './services/context'
import { probeStorage } from './services/storage/probe'
import { probeFfmpeg } from './services/media/ffmpeg'
import {
  configureBootLog,
  errorMessage,
  logError,
  logInfo,
  writeBootLog
} from './services/logging'

let mainWindow: BrowserWindow | null = null
let appContext: AppContext | null = null
let appInfoPromise: Promise<AppInfo> | null = null

// Chromium 初始化失败时控制台可能一片空白，先建立落盘日志再继续。
try {
  const bootLogPath = join(app.getPath('userData'), 'logs', 'boot.log')
  mkdirSync(dirname(bootLogPath), { recursive: true })
  configureBootLog(bootLogPath)
  writeBootLog(
    'main',
    `module loaded pid=${process.pid} electron=${process.versions.electron ?? 'unknown'} node=${process.versions.node ?? 'unknown'}`
  )
} catch (error) {
  logError('初始化启动日志失败:', errorMessage(error))
}

process.on('uncaughtException', (error) => {
  writeBootLog('uncaughtException', errorMessage(error))
})
process.on('unhandledRejection', (reason) => {
  writeBootLog('unhandledRejection', errorMessage(reason))
})

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

async function bootstrap(): Promise<void> {
  const headless = process.env['MELODY_HEADLESS'] === '1'
  writeBootLog('main', `bootstrap start headless=${headless}`)

  appContext = await createAppContext()
  writeBootLog('main', `context ready media=${appContext.media.port}`)
  registerIpcHandlers(appContext, getAppInfo)

  if (!headless) {
    mainWindow = createMainWindow()
    writeBootLog('main', 'window created')
    mainWindow.webContents.on('did-finish-load', () => {
      writeBootLog('renderer', 'did-finish-load')
    })
    mainWindow.webContents.on('did-fail-load', (_event, code, description) => {
      writeBootLog('renderer', `did-fail-load ${code} ${description}`)
    })
    mainWindow.webContents.on('render-process-gone', (_event, details) => {
      writeBootLog('renderer', `render-process-gone ${details.reason} exitCode=${details.exitCode}`)
    })
    mainWindow.once('ready-to-show', () => {
      writeBootLog('main', 'ready-to-show')
    })
    mainWindow.on('closed', () => {
      mainWindow = null
    })
  }

  void getAppInfo()
    .then((info) => {
      logInfo(
        `启动完成 headless=${headless} electron=${info.electron} chrome=${info.chrome} node=${info.node} ` +
          `storage=${info.storage.engine}(${info.storage.ok ? 'ok' : 'unavailable'}) ` +
          `ffmpeg=${info.ffmpeg.found ? (info.ffmpeg.version ?? 'found') : 'missing'} ` +
          `mediaPort=${appContext?.media.port ?? '-'} db=${appContext?.paths.dbFile ?? '-'}`
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
  app.on('will-quit', () => {
    void appContext?.dispose()
    appContext = null
  })
}
