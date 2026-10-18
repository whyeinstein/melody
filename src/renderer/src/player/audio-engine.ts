import { zhCN } from '../i18n/zh-CN'
import { clamp } from '../lib/format'
import { errorMessage } from '../lib/ipc'

/**
 * 音频引擎：HTMLAudioElement → MediaElementAudioSourceNode → GainNode → AnalyserNode → destination。
 *
 * - 音量由 GainNode 控制（图建立失败时退化为直接设置 audio.volume）；
 * - AnalyserNode 留给频谱可视化使用；
 * - EQ 插槽：阶段 2 会在 source 与 gain 之间插入 BiquadFilterNode 链，
 *   见 `setEqualizer` 与 `ensureGraph` 中的 TODO。
 *
 * 注意：媒体流由主进程的本地 HTTP 服务提供，必须带 CORS 响应头，
 * 否则 Chromium 会让 MediaElementAudioSourceNode 输出静音。
 */
export interface AudioEngineCallbacks {
  onProgress?: (currentTimeMs: number, durationMs: number) => void
  onEnded?: () => void
  onError?: (message: string) => void
  onWaiting?: () => void
  onPlayable?: () => void
}

const DEFAULT_VOLUME = 0.8

function describeMediaError(error: MediaError | null): string {
  if (error === null) return zhCN.errors.trackLoadFailed
  switch (error.code) {
    case MediaError.MEDIA_ERR_ABORTED:
      return zhCN.errors.mediaAborted
    case MediaError.MEDIA_ERR_NETWORK:
      return zhCN.errors.mediaNetwork
    case MediaError.MEDIA_ERR_DECODE:
      return zhCN.errors.mediaDecode
    case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
      return zhCN.errors.loadAudioFailed
    default:
      return zhCN.errors.trackLoadFailed
  }
}

export class AudioEngine {
  private audio: HTMLAudioElement | null = null
  private context: AudioContext | null = null
  private source: MediaElementAudioSourceNode | null = null
  private gain: GainNode | null = null
  private analyser: AnalyserNode | null = null
  private callbacks: AudioEngineCallbacks = {}
  private volume = DEFAULT_VOLUME
  private muted = false
  private graphReady = false
  /** 建图失败后不再重试（同一 Audio 元素只能创建一次 MediaElementSource）。 */
  private graphFailed = false
  /** 是否确认媒体服务支持 CORS（决定 WebAudio 图能否建立）。 */
  private corsAllowed = false

  /** 注册事件回调（整体替换，传空对象即清空）。 */
  configure(callbacks: AudioEngineCallbacks): void {
    this.callbacks = callbacks
  }

  private ensureAudio(): HTMLAudioElement | null {
    if (typeof Audio === 'undefined') return null
    if (this.audio !== null) return this.audio

    const audio = new Audio()
    audio.preload = 'metadata'

    audio.addEventListener('timeupdate', () => this.emitProgress())
    audio.addEventListener('durationchange', () => this.emitProgress())
    audio.addEventListener('loadedmetadata', () => this.emitProgress())
    audio.addEventListener('ended', () => this.callbacks.onEnded?.())
    audio.addEventListener('error', () => this.callbacks.onError?.(describeMediaError(audio.error)))
    audio.addEventListener('waiting', () => this.callbacks.onWaiting?.())
    audio.addEventListener('playing', () => this.callbacks.onPlayable?.())

    this.audio = audio
    return audio
  }

  private emitProgress(): void {
    const audio = this.audio
    if (audio === null) return
    const durationMs = Number.isFinite(audio.duration) ? Math.round(audio.duration * 1000) : 0
    const currentTimeMs = Number.isFinite(audio.currentTime) ? Math.round(audio.currentTime * 1000) : 0
    this.callbacks.onProgress?.(currentTimeMs, durationMs)
  }

  /**
   * 建立 WebAudio 图。创建失败（不支持 WebAudio 等）时静默退化，
   * 音频仍然能通过 <audio> 元素直接播放，只是没有分析器与 EQ。
   */
  private ensureGraph(): void {
    if (this.graphReady || this.graphFailed) return
    const audio = this.ensureAudio()
    if (audio === null || typeof AudioContext === 'undefined') return

    try {
      const context = new AudioContext()
      const source = context.createMediaElementSource(audio)
      const gain = context.createGain()
      const analyser = context.createAnalyser()
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.8

      // TODO(阶段 2): 在此插入 EQ 链：source → [BiquadFilterNode...] → gain → analyser → destination
      source.connect(gain)
      gain.connect(analyser)
      analyser.connect(context.destination)

      this.context = context
      this.source = source
      this.gain = gain
      this.analyser = analyser
      this.graphReady = true
      this.applyVolume()
    } catch {
      this.graphReady = false
      this.graphFailed = true
    }
  }

  private applyVolume(): void {
    const level = this.muted ? 0 : this.volume
    if (this.graphReady && this.gain !== null) {
      this.gain.gain.value = level
      if (this.audio !== null) this.audio.volume = 1
      return
    }
    if (this.audio !== null) this.audio.volume = level
  }

  /**
   * 探测媒体服务是否允许跨域。
   * 允许 → 设置 crossOrigin 并建立 WebAudio 图；
   * 不允许 → 退化为 <audio> 直接播放（可正常出声，但没有 analyser/EQ）。
   */
  private async prepareWebAudio(url: string): Promise<void> {
    if (this.graphReady || this.corsAllowed) return
    if (typeof fetch === 'undefined') return
    try {
      // HEAD 请求足够读取 CORS 响应头；跨域响应缺少 Access-Control-Allow-Origin 时 fetch 会 reject。
      const response = await fetch(url, { method: 'HEAD', cache: 'no-store' })
      if (!response.ok && response.status !== 206 && response.status !== 416) return
    } catch {
      return
    }
    this.corsAllowed = true
    const audio = this.ensureAudio()
    if (audio !== null) audio.crossOrigin = 'anonymous'
    this.ensureGraph()
  }

  /** 加载音频地址（不会自动播放）。会先确认跨域能力再决定是否建立 WebAudio 图。 */
  async load(url: string): Promise<void> {
    const audio = this.ensureAudio()
    if (audio === null) return
    await this.prepareWebAudio(url)
    audio.src = url
    audio.load()
  }

  /** 停止并清空当前音源（队列清空时调用）。 */
  stop(): void {
    const audio = this.audio
    if (audio === null) return
    audio.pause()
    audio.removeAttribute('src')
    audio.load()
    this.callbacks.onProgress?.(0, 0)
  }

  async play(): Promise<void> {
    const audio = this.ensureAudio()
    if (audio === null) return
    if (audio.src === '') return
    try {
      if (this.context !== null && this.context.state === 'suspended') {
        await this.context.resume()
      }
      await audio.play()
    } catch (reason) {
      // 切换曲目时浏览器会以 AbortError 拒绝旧的 play()，这属于正常现象，不提示用户。
      if (reason instanceof DOMException && reason.name === 'AbortError') return
      this.callbacks.onError?.(errorMessage(reason))
    }
  }

  pause(): void {
    this.audio?.pause()
  }

  /** 跳转到指定位置（毫秒）。 */
  seek(positionMs: number): void {
    const audio = this.audio
    if (audio === null) return
    const durationMs = Number.isFinite(audio.duration) ? audio.duration * 1000 : positionMs
    const target = clamp(positionMs, 0, durationMs)
    audio.currentTime = target / 1000
    this.emitProgress()
  }

  setVolume(volume: number): void {
    this.volume = clamp(volume, 0, 1)
    this.applyVolume()
  }

  setMuted(muted: boolean): void {
    this.muted = muted
    this.applyVolume()
  }

  /** 频谱分析器（可视化预留）。 */
  getAnalyser(): AnalyserNode | null {
    return this.analyser
  }

  /**
   * EQ 插槽（占位）。
   * 阶段 2 将根据频段增益创建 BiquadFilterNode 链并重新连接 source → eq → gain。
   */
  setEqualizer(_gainsDb: readonly number[]): void {
    // TODO(阶段 2): 创建并连接 BiquadFilterNode 链，实现均衡器。
  }

  /** 释放资源（正常使用中不会调用，单例引擎贯穿应用生命周期）。 */
  dispose(): void {
    this.stop()
    this.source?.disconnect()
    this.gain?.disconnect()
    this.analyser?.disconnect()
    void this.context?.close()
    this.audio = null
    this.context = null
    this.source = null
    this.gain = null
    this.analyser = null
    this.graphReady = false
  }
}

let engine: AudioEngine | null = null

/** 全局单例：避免 React StrictMode 双挂载时创建多个 Audio 元素/上下文。 */
export function getAudioEngine(): AudioEngine {
  engine ??= new AudioEngine()
  return engine
}
