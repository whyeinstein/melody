import { useEffect, useState } from 'react'
import type { AppInfo } from '@shared/ipc/contracts'
import { describeIpcError, invoke, subscribe } from '../lib/ipc'
import { useLibraryStore } from '../stores/library-store'
import { usePlayerStore } from '../stores/player-store'
import { useUiStore } from '../stores/ui-store'

export interface BootstrapState {
  ready: boolean
  info: AppInfo | null
  infoError: string | null
  configError: string | null
}

/**
 * 应用启动引导：
 * 1. 读取运行环境信息与用户配置（失败时使用默认值，不阻塞界面）；
 * 2. 把主题 / 播放偏好写入 store；
 * 3. 拉取音乐库数据（频道未实现时各视图显示空状态）。
 */
export function useAppBootstrap(): BootstrapState {
  const [state, setState] = useState<BootstrapState>({
    ready: false,
    info: null,
    infoError: null,
    configError: null
  })

  useEffect(() => {
    let cancelled = false

    // 扫描进度以主进程推送为准；轮询仅作为兜底。
    const unsubscribeScan = subscribe('scan:progress', (progress) => {
      useLibraryStore.getState().applyScanProgress(progress)
    })

    void (async () => {
      const [infoResult, configResult] = await Promise.all([invoke('app:info'), invoke('config:get')])
      if (cancelled) return

      let configError: string | null = null
      if (configResult.ok) {
        const config = configResult.data
        useUiStore.getState().setTheme(config.theme)
        usePlayerStore.getState().hydrate({
          volume: config.volume,
          shuffle: config.shuffle,
          repeat: config.repeat
        })
      } else {
        configError = describeIpcError(configResult.error)
      }

      setState({
        ready: true,
        info: infoResult.ok ? infoResult.data : null,
        infoError: infoResult.ok ? null : describeIpcError(infoResult.error),
        configError
      })

      // 配置加载完成后再拉取音乐库，避免随机播放偏好与队列初始化竞争。
      void useLibraryStore.getState().refreshAll()
    })()

    return () => {
      cancelled = true
      unsubscribeScan()
      useLibraryStore.getState().stopScanPolling()
    }
  }, [])

  return state
}
