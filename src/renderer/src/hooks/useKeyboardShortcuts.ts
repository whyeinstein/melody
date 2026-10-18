import { useEffect } from 'react'
import { focusSearch, isEditableTarget, isInteractiveTarget } from '../lib/dom'
import { seekBy, togglePlay } from '../lib/playback'
import { useUiStore } from '../stores/ui-store'

/**
 * 全局键盘快捷键：
 * - 空格：播放 / 暂停
 * - ← / →：后退 / 快进 5 秒
 * - Ctrl+F：聚焦搜索框
 * - Ctrl+K：命令面板（占位）
 * - Esc：关闭命令面板 / 队列抽屉
 */
export function useKeyboardShortcuts(): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const modifier = event.ctrlKey || event.metaKey
      const key = event.key.toLowerCase()

      if (modifier && key === 'k') {
        event.preventDefault()
        useUiStore.getState().toggleCommand()
        return
      }
      if (modifier && key === 'f') {
        event.preventDefault()
        focusSearch()
        return
      }
      if (event.key === 'Escape') {
        const ui = useUiStore.getState()
        if (ui.commandOpen) ui.toggleCommand(false)
        else if (ui.queueOpen) ui.toggleQueue(false)
        return
      }

      // 输入框 / 文本域中不响应全局播放快捷键。
      if (isEditableTarget(event.target) || event.altKey || modifier) return

      if (event.code === 'Space' || event.key === ' ') {
        // 让按钮/链接/角色按钮自己处理空格激活。
        if (isInteractiveTarget(event.target)) return
        event.preventDefault()
        togglePlay()
        return
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        seekBy(5000)
        return
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        seekBy(-5000)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}
