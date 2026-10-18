/**
 * 开发启动器：包住 `electron-vite dev`，做环境清理并按需注入诊断参数。
 *
 * 1. 删除 ELECTRON_RUN_AS_NODE：某些宿主（IDE/DSH 派生的终端）会设置它，
 *    带着它启动 electron.exe 会退化成普通 Node 进程，界面永远不出现且不报明显错误。
 * 2. MELODY_DIAG=1 时打开 Chromium 自身日志（logs/chromium.log），
 *    用于排查 Electron 启动即退出的问题。
 * 3. MELODY_EXTRA_ARGS 里的参数会透传给 Electron，例如 "--disable-gpu"。
 * 4. NO_SANDBOX=1 由 electron-vite 原生支持，追加 --no-sandbox。
 *
 * 用法：npm run dev
 */
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const cli = resolve(projectRoot, 'node_modules/electron-vite/bin/electron-vite.js')

const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE

if (process.env['ELECTRON_RUN_AS_NODE'] !== undefined) {
  console.log(
    '[melody] 警告：当前终端带有 ELECTRON_RUN_AS_NODE，说明它很可能由代理/IDE 环境派生。' +
      '已移除该变量，但这类环境通常还禁止 Chromium 需要的命名管道，窗口仍可能起不来。' +
      '建议改用开始菜单里的普通终端，或在资源管理器里双击项目根目录的 dev.cmd。'
  )
}

const extraArgs = (process.env['MELODY_EXTRA_ARGS'] ?? '').split(/\s+/).filter(Boolean)

if (process.env['MELODY_DIAG'] === '1') {
  const logDir = resolve(projectRoot, 'logs')
  mkdirSync(logDir, { recursive: true })
  const chromiumLog = resolve(logDir, 'chromium.log')
  const cliArgs = ['--enable-logging', `--log-file=${chromiumLog}`, '--v=1', ...extraArgs]
  env.ELECTRON_CLI_ARGS = JSON.stringify(cliArgs)
  console.log(`[melody] 诊断模式：Electron 参数 = ${cliArgs.join(' ')}`)
} else if (extraArgs.length > 0) {
  env.ELECTRON_CLI_ARGS = JSON.stringify(extraArgs)
}

if (env['NO_SANDBOX'] === '1') {
  console.log('[melody] NO_SANDBOX=1：本次以 --no-sandbox 启动（仅用于受限环境排查）')
}

const child = spawn(process.execPath, [cli, 'dev', ...process.argv.slice(2)], {
  cwd: projectRoot,
  env,
  stdio: 'inherit'
})

child.on('exit', (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0))
})
