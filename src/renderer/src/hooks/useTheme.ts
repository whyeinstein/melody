import { useEffect } from 'react'
import { useUiStore } from '../stores/ui-store'

/** 把主题偏好写到 <html data-theme> 上；`system` 跟随系统并实时响应变化。 */
export function useTheme(): void {
  const theme = useUiStore((state) => state.theme)

  useEffect(() => {
    const root = document.documentElement
    const media = window.matchMedia('(prefers-color-scheme: light)')
    const apply = (): void => {
      const resolved = theme === 'system' ? (media.matches ? 'light' : 'dark') : theme
      root.setAttribute('data-theme', resolved)
    }
    apply()
    if (theme !== 'system') return
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [theme])
}
