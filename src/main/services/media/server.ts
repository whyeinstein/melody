import { randomBytes, timingSafeEqual } from 'node:crypto'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import {
  createServer,
  type IncomingMessage,
  type OutgoingHttpHeaders,
  type ServerResponse
} from 'node:http'
import type { Socket } from 'node:net'
import { extname } from 'node:path'
import { mimeForExtension } from '@shared/constants/audio'
import { errorMessage, logWarn } from '../logging'
import { parseRangeHeader, type RangeDecision } from '../../util/range'

/** 启动媒体服务所需的回调。路径只能来自这些回调，服务本身不接受客户端传入的路径。 */
export interface MediaServerOptions {
  /** 把曲目 id 解析成绝对路径；返回 null 表示曲目不存在。 */
  getTrackPath(trackId: number): Promise<string | null>
  /** 把封面 id 解析成绝对路径；不提供时 `/covers` 路由一律 404。 */
  getCoverPath?(coverId: number): Promise<string | null>
  /** 固定 token（测试用）；不传时每次启动随机生成。 */
  token?: string
}

export interface MediaServerHandle {
  /** 形如 `http://127.0.0.1:<port>`。 */
  baseUrl: string
  token: string
  /** 生成带 token 的音频地址，可直接给 `<audio src>` 使用。 */
  audioUrl(trackId: number): string
  /** 生成带 token 的封面地址，可直接给 `<img src>` 使用。 */
  coverUrl(coverId: number): string
  /** 关闭监听并销毁所有连接；可重复调用。 */
  close(): Promise<void>
  port: number
}

const AUDIO_ROUTE = /^\/audio\/(\d+)$/
const COVER_ROUTE = /^\/covers\/(\d+)$/
const TOKEN_BYTES = 24
const CACHE_CONTROL = 'no-store'

/**
 * `mimeForExtension` 只覆盖音频扩展名，封面用的图片类型在这里补齐。
 * （本文件不能改 src/shared，所以图片 MIME 表先放本地；命中不到再回退到共享实现。）
 */
const IMAGE_MIME_BY_EXTENSION: Readonly<Record<string, string>> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.avif': 'image/avif',
  '.bmp': 'image/bmp'
}

function mimeForPath(path: string): string {
  const extension = extname(path).toLowerCase()
  return IMAGE_MIME_BY_EXTENSION[extension] ?? mimeForExtension(extension)
}

type ResourceKind = 'audio' | 'cover'
type PathResolver = (id: number) => Promise<string | null>

function generateToken(): string {
  return randomBytes(TOKEN_BYTES).toString('hex')
}

/** 定长时间安全比较，避免 token 泄露给计时攻击。 */
function tokenEquals(expected: string, received: string | null): boolean {
  if (received === null) return false
  const a = Buffer.from(expected, 'utf8')
  const b = Buffer.from(received, 'utf8')
  return a.length === b.length && timingSafeEqual(a, b)
}

/** 发送一个简短的文本错误响应（HEAD 不带 body）。 */
function sendText(res: ServerResponse, statusCode: number, message: string): void {
  const body = Buffer.from(message, 'utf8')
  res.writeHead(statusCode, {
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Length': body.length,
    'Cache-Control': CACHE_CONTROL
  })
  if (res.req?.method === 'HEAD') {
    res.end()
    return
  }
  res.end(body)
}

/** 路由里的 id 必须是正的安全整数（`/audio/0`、超大数字都不算）。 */
function parsePositiveId(text: string): number | null {
  if (!/^\d+$/.test(text)) return null
  const value = Number(text)
  return Number.isSafeInteger(value) && value > 0 ? value : null
}

async function handleRequest(
  req: IncomingMessage,
  res: ServerResponse,
  getTrackPath: PathResolver,
  getCoverPath: PathResolver | undefined,
  token: string
): Promise<void> {
  // 渲染层用 WebAudio 的 MediaElementAudioSourceNode 读取跨域媒体时必须走 CORS，
  // 否则音频图输出静音；Range 相关响应头也要显式暴露给页面。
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader(
    'Access-Control-Expose-Headers',
    'Content-Range, Accept-Ranges, Content-Length, Content-Type, Last-Modified'
  )
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Range')

  // 预检不携带 token，且不返回任何资源数据，直接放行。
  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  // 只支持 GET / HEAD；其它方法明确拒绝。
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD, OPTIONS')
    sendText(res, 405, 'Method Not Allowed')
    return
  }

  let url: URL
  try {
    url = new URL(req.url ?? '/', 'http://127.0.0.1')
  } catch {
    sendText(res, 400, 'Bad Request')
    return
  }

  // 所有请求（包括不存在的路由）都必须带正确 token。
  if (!tokenEquals(token, url.searchParams.get('token'))) {
    sendText(res, 403, 'Forbidden')
    return
  }

  const audioMatch = AUDIO_ROUTE.exec(url.pathname)
  const coverMatch = audioMatch ? null : COVER_ROUTE.exec(url.pathname)
  const kind: ResourceKind = audioMatch ? 'audio' : 'cover'
  const id = parsePositiveId((audioMatch ?? coverMatch)?.[1] ?? '')
  if (id === null) {
    sendText(res, 404, 'Not Found')
    return
  }

  const resolvePath = kind === 'audio' ? getTrackPath : getCoverPath
  // 未提供封面回调时 /covers 一律 404，音频路由不受影响。
  if (!resolvePath) {
    sendText(res, 404, 'Not Found')
    return
  }

  let path: string | null
  try {
    path = await resolvePath(id)
  } catch (error) {
    logWarn(`媒体服务查询${kind === 'audio' ? '曲目' : '封面'} id=${id} 路径失败:`, errorMessage(error))
    sendText(res, 500, 'Internal Server Error')
    return
  }
  if (path === null || path === '') {
    sendText(res, 404, 'Not Found')
    return
  }

  let size: number
  let mtime: Date
  try {
    const info = await stat(path)
    if (!info.isFile()) {
      sendText(res, 404, 'Not Found')
      return
    }
    size = info.size
    mtime = info.mtime
  } catch {
    // 文件在扫描后已被删除/移动：按不存在处理。
    sendText(res, 404, 'Not Found')
    return
  }

  const mime = mimeForPath(path)

  // 音频需要 Range（Chromium 要边下边播）；封面是小文件，直接 200 全量返回，
  // 即使客户端带了 Range 也忽略。
  let decision: RangeDecision = { kind: 'full' }
  if (kind === 'audio') decision = parseRangeHeader(req.headers.range, size)

  if (decision.kind === 'unsatisfiable') {
    res.writeHead(416, {
      'Accept-Ranges': 'bytes',
      'Content-Range': `bytes */${size}`,
      'Content-Type': mime,
      'Content-Length': 0,
      'Cache-Control': CACHE_CONTROL
    })
    res.end()
    return
  }

  let start = 0
  let end = size - 1
  let partial = false
  if (decision.kind === 'partial') {
    partial = true
    start = decision.range.start
    end = decision.range.end
  }
  const length = size === 0 ? 0 : end - start + 1

  const headers: OutgoingHttpHeaders = {
    'Content-Type': mime,
    'Content-Length': length,
    'Cache-Control': CACHE_CONTROL,
    'Last-Modified': mtime.toUTCString()
  }
  if (kind === 'audio') headers['Accept-Ranges'] = 'bytes'
  if (partial) headers['Content-Range'] = `bytes ${start}-${end}/${size}`

  res.writeHead(partial ? 206 : 200, headers)

  if (res.req?.method === 'HEAD' || length === 0) {
    res.end()
    return
  }

  const stream = createReadStream(path, { start, end })

  // 客户端提前断开或服务关闭销毁 socket 时停止读文件，避免 fd 泄漏。
  res.on('close', () => {
    if (!res.writableFinished) stream.destroy()
  })
  stream.on('error', (error) => {
    logWarn(`媒体服务读取文件失败 path=${path}:`, errorMessage(error))
    res.destroy()
  })
  stream.pipe(res)
}

function assertPositiveId(value: number, label: string): void {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new RangeError(`${label}: 非法的 id ${String(value)}`)
  }
}

/**
 * 创建仅监听 127.0.0.1 的本地媒体 HTTP 服务，供渲染进程播放本地音频、显示封面。
 * 端口随机、token 鉴权；音频路由实现 Range（200/206/416），封面路由全量 200。
 */
export async function createMediaServer(options: MediaServerOptions): Promise<MediaServerHandle> {
  const getTrackPath = options.getTrackPath
  if (typeof getTrackPath !== 'function') {
    throw new TypeError('createMediaServer: getTrackPath 必须是函数')
  }
  const getCoverPath = options.getCoverPath
  if (getCoverPath !== undefined && typeof getCoverPath !== 'function') {
    throw new TypeError('createMediaServer: getCoverPath 必须是函数')
  }
  const token =
    typeof options.token === 'string' && options.token.length > 0 ? options.token : generateToken()

  const sockets = new Set<Socket>()
  const server = createServer((req, res) => {
    void handleRequest(req, res, getTrackPath, getCoverPath, token).catch((error: unknown) => {
      logWarn('媒体服务请求处理异常:', errorMessage(error))
      if (!res.headersSent) sendText(res, 500, 'Internal Server Error')
      else res.destroy()
    })
  })

  // 记录活动连接，close() 时逐个销毁（否则 keep-alive 连接会让 close 挂起）。
  server.on('connection', (socket) => {
    sockets.add(socket)
    socket.on('close', () => {
      sockets.delete(socket)
    })
  })

  await new Promise<void>((resolve, reject) => {
    const onError = (error: Error): void => {
      server.off('listening', onListening)
      reject(error)
    }
    const onListening = (): void => {
      server.off('error', onError)
      resolve()
    }
    server.once('error', onError)
    server.once('listening', onListening)
    server.listen(0, '127.0.0.1')
  })

  // 监听成功后的意外错误只记录，不让主进程崩溃。
  server.on('error', (error: Error) => {
    logWarn('媒体服务异常:', errorMessage(error))
  })

  const address = server.address()
  if (address === null || typeof address === 'string') {
    await new Promise<void>((resolve) => {
      server.close(() => resolve())
    })
    throw new Error('媒体服务未能获取监听端口')
  }

  const port = address.port
  const baseUrl = `http://127.0.0.1:${port}`

  let closePromise: Promise<void> | null = null
  const close = (): Promise<void> => {
    if (closePromise) return closePromise
    closePromise = new Promise<void>((resolve, reject) => {
      server.close((error) => {
        if (error) reject(error)
        else resolve()
      })
      for (const socket of sockets) socket.destroy()
      sockets.clear()
    })
    return closePromise
  }

  const buildUrl = (segment: 'audio' | 'covers', id: number): string =>
    `${baseUrl}/${segment}/${id}?token=${encodeURIComponent(token)}`

  const audioUrl = (trackId: number): string => {
    assertPositiveId(trackId, 'audioUrl')
    return buildUrl('audio', trackId)
  }

  const coverUrl = (coverId: number): string => {
    assertPositiveId(coverId, 'coverUrl')
    return buildUrl('covers', coverId)
  }

  return { baseUrl, token, audioUrl, coverUrl, close, port }
}
