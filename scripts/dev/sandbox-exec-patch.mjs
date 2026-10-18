/**
 * 开发沙箱补丁：受限制的沙箱环境禁止带管道的子进程（spawn/exec 会抛 EPERM），
 * 而 Vite 在 Windows 首次解析路径时会同步调用 `exec("net use")` 探测网络驱动器，
 * 导致 vitest / electron-vite 在受限沙箱下无法启动。
 *
 * 这里只拦截那一条探测命令（返回错误让 Vite 走默认分支），其余 exec 调用保持原样。
 * 在普通终端里运行同样安全：结果是退回 `fs.realpathSync` 的默认实现。
 *
 * 用法：node --import ./scripts/dev/sandbox-exec-patch.mjs <其它命令行>
 */
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const childProcess = require('node:child_process')
const originalExec = childProcess.exec

const NET_USE = /^\s*net\s+use\s*$/i

childProcess.exec = function sandboxSafeExec(command, options, callback) {
  if (typeof command === 'string' && NET_USE.test(command)) {
    const done = typeof options === 'function' ? options : callback
    const fake = { on: () => fake, kill: () => {}, removeListener: () => fake }
    if (typeof done === 'function') {
      queueMicrotask(() => done(new Error('net use probing skipped'), '', ''))
    }
    return fake
  }
  return originalExec.call(childProcess, command, options, callback)
}
