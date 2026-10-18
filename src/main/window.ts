import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { BrowserWindow } from 'electron'

const currentDir = fileURLToPath(new URL('.', import.meta.url))

export function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    show: false,
    backgroundColor: '#0b0c10',
    title: 'Melody',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(currentDir, '../preload/index.cjs'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webviewTag: false,
      spellcheck: false
    }
  })

  window.once('ready-to-show', () => window.show())

  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event, url) => {
    if (url !== window.webContents.getURL()) event.preventDefault()
  })

  const rendererUrl = process.env['ELECTRON_RENDERER_URL']
  if (rendererUrl) {
    void window.loadURL(rendererUrl)
  } else {
    void window.loadFile(join(currentDir, '../renderer/index.html'))
  }

  return window
}
