import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import {
  createMediaServer,
  type MediaServerHandle
} from '../../src/main/services/media/server'

/** 测试 fixture 放在工作区 .cache 下，避免依赖系统临时目录权限。 */
const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const cacheDir = join(projectRoot, '.cache')

const CONTENT = Buffer.from(Array.from({ length: 1000 }, (_, index) => index % 256))
/** 封面不需要是真实图片，只要扩展名能决定 Content-Type 即可。 */
const COVER_CONTENT = Buffer.from(Array.from({ length: 200 }, (_, index) => (index * 7) % 256))

async function readBody(response: Response): Promise<Buffer> {
  return Buffer.from(await response.arrayBuffer())
}

describe('createMediaServer', () => {
  let fixtureDir!: string
  let audioPath!: string
  let coverPath!: string
  let coverPngPath!: string
  let handle!: MediaServerHandle

  beforeAll(async () => {
    await mkdir(cacheDir, { recursive: true })
    fixtureDir = await mkdtemp(join(cacheDir, 'media-server-'))
    audioPath = join(fixtureDir, 'song one.mp3')
    coverPath = join(fixtureDir, 'cover.jpg')
    coverPngPath = join(fixtureDir, 'cover.png')
    await writeFile(audioPath, CONTENT)
    await writeFile(coverPath, COVER_CONTENT)
    await writeFile(coverPngPath, COVER_CONTENT)

    handle = await createMediaServer({
      getTrackPath: async (trackId: number): Promise<string | null> => {
        switch (trackId) {
          case 1:
            return audioPath
          case 2:
            return join(fixtureDir, 'missing.mp3')
          case 3:
            return null
          case 4:
            return fixtureDir
          case 5:
            throw new Error('boom')
          default:
            return null
        }
      },
      getCoverPath: async (coverId: number): Promise<string | null> => {
        switch (coverId) {
          case 1:
            return coverPath
          case 2:
            return join(fixtureDir, 'missing-cover.png')
          case 3:
            throw new Error('boom')
          case 4:
            return coverPngPath
          default:
            return null
        }
      }
    })
  })

  afterAll(async () => {
    await handle?.close()
    await rm(fixtureDir, { recursive: true, force: true })
  })

  it('暴露 baseUrl / port / token，并生成带 token 的音频与封面地址', () => {
    expect(handle.baseUrl).toBe(`http://127.0.0.1:${handle.port}`)
    expect(handle.port).toBeGreaterThan(0)
    expect(handle.token).toMatch(/^[0-9a-f]{48}$/)
    expect(handle.audioUrl(1)).toBe(`${handle.baseUrl}/audio/1?token=${handle.token}`)
    expect(handle.coverUrl(1)).toBe(`${handle.baseUrl}/covers/1?token=${handle.token}`)
    expect(() => handle.audioUrl(0)).toThrow(RangeError)
    expect(() => handle.coverUrl(-1)).toThrow(RangeError)
  })

  it('按扩展名返回封面图片 MIME（.jpg / .png）', async () => {
    expect((await fetch(handle.coverUrl(1))).headers.get('content-type')).toBe('image/jpeg')
    expect((await fetch(handle.coverUrl(4))).headers.get('content-type')).toBe('image/png')
  })

  it('封面路由返回 200 全量内容与图片 MIME', async () => {
    const response = await fetch(handle.coverUrl(1))
    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toBe('image/jpeg')
    expect(response.headers.get('content-length')).toBe('200')
    expect(response.headers.get('content-range')).toBeNull()
    expect(await readBody(response)).toEqual(COVER_CONTENT)
  })

  it('封面路由忽略 Range，始终返回 200 全量内容', async () => {
    const response = await fetch(handle.coverUrl(1), { headers: { Range: 'bytes=0-9' } })
    expect(response.status).toBe(200)
    expect(response.headers.get('content-range')).toBeNull()
    expect(response.headers.get('content-length')).toBe('200')
    expect(await readBody(response)).toEqual(COVER_CONTENT)
  })

  it('HEAD 封面返回 200 头但无 body', async () => {
    const response = await fetch(handle.coverUrl(1), { method: 'HEAD' })
    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toBe('image/jpeg')
    expect(response.headers.get('content-length')).toBe('200')
    expect(await readBody(response)).toHaveLength(0)
  })

  it('未知封面 id、缺失文件与回调抛错分别返回 404 / 404 / 500', async () => {
    expect((await fetch(handle.coverUrl(999))).status).toBe(404)
    expect((await fetch(handle.coverUrl(2))).status).toBe(404)
    expect((await fetch(handle.coverUrl(3))).status).toBe(500)
    // 音频路由不受封面回调影响。
    expect((await fetch(handle.audioUrl(1))).status).toBe(200)
  })

  it('无 Range 时返回 200、完整内容与正确响应头', async () => {
    const response = await fetch(handle.audioUrl(1))
    expect(response.status).toBe(200)
    expect(response.headers.get('accept-ranges')).toBe('bytes')
    expect(response.headers.get('content-type')).toBe('audio/mpeg')
    expect(response.headers.get('content-length')).toBe('1000')
    expect(response.headers.get('content-range')).toBeNull()
    expect(await readBody(response)).toEqual(CONTENT)
  })

  it('闭区间 Range 返回 206 与片段内容', async () => {
    const response = await fetch(handle.audioUrl(1), { headers: { Range: 'bytes=100-199' } })
    expect(response.status).toBe(206)
    expect(response.headers.get('accept-ranges')).toBe('bytes')
    expect(response.headers.get('content-range')).toBe('bytes 100-199/1000')
    expect(response.headers.get('content-length')).toBe('100')
    expect(await readBody(response)).toEqual(CONTENT.subarray(100, 200))
  })

  it('开区间 Range 返回文件末尾片段', async () => {
    const response = await fetch(handle.audioUrl(1), { headers: { Range: 'bytes=990-' } })
    expect(response.status).toBe(206)
    expect(response.headers.get('content-range')).toBe('bytes 990-999/1000')
    expect(await readBody(response)).toEqual(CONTENT.subarray(990))
  })

  it('后缀 Range 返回最后 N 字节', async () => {
    const response = await fetch(handle.audioUrl(1), { headers: { Range: 'bytes=-10' } })
    expect(response.status).toBe(206)
    expect(response.headers.get('content-range')).toBe('bytes 990-999/1000')
    expect(await readBody(response)).toEqual(CONTENT.subarray(990))
  })

  it('越界 Range 返回 416 与 Content-Range: bytes */size', async () => {
    const response = await fetch(handle.audioUrl(1), { headers: { Range: 'bytes=2000-' } })
    expect(response.status).toBe(416)
    expect(response.headers.get('content-range')).toBe('bytes */1000')
    expect(await readBody(response)).toHaveLength(0)
  })

  it('HEAD 返回与 GET 相同的头但不带 body', async () => {
    const response = await fetch(handle.audioUrl(1), { method: 'HEAD' })
    expect(response.status).toBe(200)
    expect(response.headers.get('accept-ranges')).toBe('bytes')
    expect(response.headers.get('content-type')).toBe('audio/mpeg')
    expect(response.headers.get('content-length')).toBe('1000')
    expect(await readBody(response)).toHaveLength(0)
  })

  it('HEAD + Range 返回 206 头但无 body', async () => {
    const response = await fetch(handle.audioUrl(1), {
      method: 'HEAD',
      headers: { Range: 'bytes=0-9' }
    })
    expect(response.status).toBe(206)
    expect(response.headers.get('content-range')).toBe('bytes 0-9/1000')
    expect(response.headers.get('content-length')).toBe('10')
    expect(await readBody(response)).toHaveLength(0)
  })

  it('getTrackPath 抛错时返回 500，服务仍可继续处理请求', async () => {
    const failed = await fetch(handle.audioUrl(5))
    expect(failed.status).toBe(500)

    const recovered = await fetch(handle.audioUrl(1))
    expect(recovered.status).toBe(200)
  })

  it('支持通过 options.token 指定固定 token', async () => {
    const custom = await createMediaServer({
      token: 'fixed-token-123',
      getTrackPath: async () => audioPath
    })
    try {
      expect(custom.token).toBe('fixed-token-123')
      expect(custom.audioUrl(7)).toBe(`${custom.baseUrl}/audio/7?token=fixed-token-123`)

      const ok = await fetch(custom.audioUrl(7))
      expect(ok.status).toBe(200)

      // 默认 token 的实例不接受这个 token。
      const crossToken = await fetch(`${handle.baseUrl}/audio/1?token=fixed-token-123`)
      expect(crossToken.status).toBe(403)
    } finally {
      await custom.close()
    }
  })

  it('未提供 getCoverPath 时 /covers 一律 404，音频不受影响', async () => {
    const audioOnly = await createMediaServer({
      getTrackPath: async () => audioPath
    })
    try {
      const response = await fetch(`${audioOnly.baseUrl}/covers/1?token=${audioOnly.token}`)
      expect(response.status).toBe(404)
      expect((await fetch(audioOnly.audioUrl(1))).status).toBe(200)
    } finally {
      await audioOnly.close()
    }
  })

  it('缺少或错误的 token 返回 403', async () => {
    const noToken = await fetch(`${handle.baseUrl}/audio/1`)
    expect(noToken.status).toBe(403)

    const wrongToken = await fetch(`${handle.baseUrl}/audio/1?token=deadbeef`)
    expect(wrongToken.status).toBe(403)

    // 不存在的路由也要先过 token 校验。
    const protectedRoute = await fetch(`${handle.baseUrl}/whatever`)
    expect(protectedRoute.status).toBe(403)
  })

  it('未知 id、null 路径、缺失文件与目录都返回 404', async () => {
    const unknownId = await fetch(handle.audioUrl(999))
    expect(unknownId.status).toBe(404)

    const nullPath = await fetch(handle.audioUrl(3))
    expect(nullPath.status).toBe(404)

    const missingFile = await fetch(handle.audioUrl(2))
    expect(missingFile.status).toBe(404)

    const directory = await fetch(handle.audioUrl(4))
    expect(directory.status).toBe(404)
  })

  it('非正整数 id 与未知路由返回 404', async () => {
    const token = `token=${handle.token}`
    const paths = [
      '/audio/0',
      '/audio/abc',
      '/audio/1/extra',
      '/audio/-1',
      '/covers/0',
      '/covers/abc',
      '/covers/1/extra'
    ]
    for (const path of paths) {
      const response = await fetch(`${handle.baseUrl}${path}?${token}`)
      expect(response.status, path).toBe(404)
    }
  })

  it('非 GET/HEAD 方法返回 405', async () => {
    const response = await fetch(handle.audioUrl(1), { method: 'POST' })
    expect(response.status).toBe(405)
    expect(response.headers.get('allow')).toBe('GET, HEAD, OPTIONS')
  })

  it('CORS：GET 暴露 Range 头，OPTIONS 预检直接 204', async () => {
    const audio = await fetch(handle.audioUrl(1))
    expect(audio.headers.get('access-control-allow-origin')).toBe('*')
    expect(audio.headers.get('access-control-expose-headers')).toContain('Content-Range')

    const preflight = await fetch(handle.audioUrl(1), { method: 'OPTIONS' })
    expect(preflight.status).toBe(204)
    expect(preflight.headers.get('access-control-allow-origin')).toBe('*')
    expect(preflight.headers.get('access-control-allow-headers')).toContain('Range')
  })

  it('close() 可重复调用，关闭后连接被拒绝', async () => {
    const url = handle.audioUrl(1)
    await handle.close()
    await handle.close()
    await expect(fetch(url)).rejects.toThrow()
  })
})
