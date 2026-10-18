/**
 * HTTP Range 请求头解析（只处理 `bytes` 单位的单区间）。
 *
 * Chromium 的 `<audio>` 在播放本地媒体时会发 `Range: bytes=start-` 之类的请求，
 * 主进程的本地媒体服务需要把它翻译成 `fs.createReadStream` 的 `{ start, end }`。
 *
 * 语义遵循 RFC 9110：
 * - 头不存在 / 空 / 单位不是 `bytes` / 语法非法 / 多区间：忽略 Range，按 200 返回完整内容；
 * - 单区间且可满足：按 206 返回该闭区间；
 * - 语法合法但无法满足（起点 ≥ 文件大小、后缀长度为 0、文件为空）：按 416 返回。
 *
 * 这里只做纯计算，不接触文件系统，方便单元测试。
 */

/** 闭区间 `[start, end]`，单位字节，两端都包含（与 `fs.createReadStream` 的语义一致）。 */
export interface ByteRange {
  start: number
  end: number
}

/** `parseRangeHeader` 的判定结果。 */
export type RangeDecision =
  /** 忽略 Range（或没有 Range），返回 200 + 完整内容。 */
  | { kind: 'full' }
  /** 可满足的单区间，返回 206 + `Content-Range`。 */
  | { kind: 'partial'; range: ByteRange }
  /** 无法满足的区间，返回 416 + `Content-Range: bytes *\/size`。 */
  | { kind: 'unsatisfiable' }

const RANGE_PREFIX = /^bytes\s*=\s*/i
const SINGLE_RANGE = /^(\d*)\s*-\s*(\d*)$/

/** 把纯数字串解析成安全整数；越界或非法返回 null。 */
function parseIndex(text: string): number | null {
  if (!/^\d+$/.test(text)) return null
  const value = Number(text)
  return Number.isSafeInteger(value) ? value : null
}

/**
 * 解析 Range 头。
 *
 * @param header 请求头原值，`undefined` / `null` / 空串都表示没有 Range。
 * @param size 资源总字节数（来自 `fs.stat`，非负整数）。
 */
export function parseRangeHeader(
  header: string | null | undefined,
  size: number
): RangeDecision {
  if (header == null) return { kind: 'full' }

  const trimmed = header.trim()
  if (!trimmed) return { kind: 'full' }
  if (!RANGE_PREFIX.test(trimmed)) return { kind: 'full' }

  const spec = trimmed.replace(RANGE_PREFIX, '').trim()
  // 多区间（`bytes=0-99,200-299`）：本服务只支持单区间，按 RFC 允许的方式忽略整个头。
  // Chromium 播放音频不会发多区间，所以退回完整响应即可，不必拆分 multipart/byteranges。
  if (spec.includes(',')) return { kind: 'full' }

  const match = SINGLE_RANGE.exec(spec)
  if (!match) return { kind: 'full' }

  const rawStart = match[1] ?? ''
  const rawEnd = match[2] ?? ''
  if (rawStart === '' && rawEnd === '') return { kind: 'full' }

  // 空文件（或非法大小）：任何区间都无法满足。
  const total = Number.isSafeInteger(size) && size > 0 ? size : 0

  // 后缀形式 `bytes=-N`：最后 N 个字节。
  if (rawStart === '') {
    const suffixLength = parseIndex(rawEnd)
    if (suffixLength === null) return { kind: 'full' }
    if (suffixLength === 0 || total === 0) return { kind: 'unsatisfiable' }
    return {
      kind: 'partial',
      range: { start: Math.max(0, total - suffixLength), end: total - 1 }
    }
  }

  const start = parseIndex(rawStart)
  if (start === null) return { kind: 'full' }
  if (start >= total) return { kind: 'unsatisfiable' }

  // 开区间 `bytes=start-`：从 start 到文件末尾。
  if (rawEnd === '') {
    return { kind: 'partial', range: { start, end: total - 1 } }
  }

  const end = parseIndex(rawEnd)
  if (end === null) return { kind: 'full' }
  // 起点大于终点属于非法语法，忽略 Range 返回完整内容。
  if (end < start) return { kind: 'full' }

  return { kind: 'partial', range: { start, end: Math.min(end, total - 1) } }
}
