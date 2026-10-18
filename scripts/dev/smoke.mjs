/**
 * 冒烟启动器：以「继承 stdio」的方式拉起 Electron，避免在受限沙箱里
 * 使用带管道的 child_process（会 EPERM），同时把退出码透传给调用方。
 *
 * 注意：某些宿主环境（例如 DSH 自身）会设置 ELECTRON_RUN_AS_NODE=1，
 * 那会让 electron.exe 退化成普通 Node 进程，必须在这里显式移除。
 * 无桌面会话下 Chromium 无法建窗（0x80000003），此时用 --headless 只跑主进程逻辑。
 *
 * 用法：node scripts/dev/smoke.mjs [--headless] [额外 electron 参数]
 */
import { spawn } from 'node:child_process'
import { existsSync, readFileSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const electronBinary = resolve(projectRoot, 'node_modules/electron/dist/electron.exe')

const args = process.argv.slice(2)
const headlessIndex = args.indexOf('--headless')
if (headlessIndex !== -1) args.splice(headlessIndex, 1)

const resultPath = resolve(projectRoot, '.cache/smoke-appinfo.json')
rmSync(resultPath, { force: true })

const env = { ...process.env, MELODY_SMOKE: '1', ELECTRON_ENABLE_LOGGING: '1', MELODY_SMOKE_OUT: resultPath }
delete env.ELECTRON_RUN_AS_NODE
if (headlessIndex !== -1) env.MELODY_HEADLESS = '1'

const child = spawn(electronBinary, [projectRoot, ...args], {
  cwd: projectRoot,
  env,
  stdio: 'inherit'
})

const timer = setTimeout(() => {
  console.error('[smoke] 超过 60 秒仍未退出，强制结束')
  child.kill()
}, 60_000)

child.on('exit', (code) => {
  clearTimeout(timer)
  if (existsSync(resultPath)) {
    const info = JSON.parse(readFileSync(resultPath, 'utf8'))
    console.log('[smoke] app:info =', JSON.stringify(info, null, 2))
  } else {
    console.error('[smoke] 未生成 app:info 结果文件，主进程可能没有跑到退出前')
  }
  process.exit(code ?? 1)
})
