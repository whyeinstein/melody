import { appendFileSync } from 'node:fs'

const PREFIX = '[melody]'

let bootLogFile: string | null = null

/** 涓昏繘绋嬪穿婧冿紙渚嬪 Chromium 鍒濆鍖栧け璐ワ級鏃舵帶鍒跺彴鍙兘浠€涔堥兘鐪嬩笉鍒帮紝鍥犳棰濆钀界洏涓€浠藉惎鍔ㄦ棩蹇椼€?*/
export function configureBootLog(filePath: string): void {
  bootLogFile = filePath
}

export function writeBootLog(scope: string, message = ''): void {
  const line = `${new Date().toISOString()} [${scope}] ${message}`
  console.log(PREFIX, line)
  if (!bootLogFile) return
  try {
    appendFileSync(bootLogFile, `${line}\n`, 'utf8')
  } catch {
    // 鏃ュ織鍐欏叆澶辫触涓嶅簲褰卞搷鍚姩
  }
}

export function logInfo(...args: unknown[]): void {
  console.log(PREFIX, ...args)
}

export function logWarn(...args: unknown[]): void {
  console.warn(PREFIX, ...args)
}

export function logError(...args: unknown[]): void {
  console.error(PREFIX, ...args)
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}
