/**
 * 开发启动器：包住 `electron-vite dev`，做两件环境清理后再交给 electron-vite。
 *
 * 1. 删除 ELECTRON_RUN_AS_NODE：某些宿主（例如 IDE/DSH 派生的终端）会设置它，
 *    带着它启动 electron.exe 会退化成普通 Node 进程，界面永远不出现，且不报明显错误。
 * 2. 透传 NO_SANDBOX=1：受限环境里 Chromium 沙箱初始化失败时，可以用
 *    `set NO_SANDBOX=1 && npm run dev` 临时关闭沙箱启动（electron-vite 原生支持）。
 *
 * 用法：npm run dev   或   node scripts/dev/dev.mjs
 */
import { spawn } from 'node:child_process'
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
