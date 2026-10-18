import type { JSX } from 'react'
import { Command } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { useUiStore } from '../../stores/ui-store'

const SHORTCUTS: readonly { label: string; keys: string }[] = [
  { label: zhCN.shortcuts.space, keys: 'Space' },
  { label: zhCN.shortcuts.seek, keys: '← / →' },
  { label: zhCN.shortcuts.search, keys: 'Ctrl F' },
  { label: zhCN.shortcuts.palette, keys: 'Ctrl K' },
  { label: zhCN.shortcuts.escape, keys: 'Esc' }
]

/**
 * Ctrl+K 命令面板（占位实现）。
 * 阶段 2 将在此接入全局搜索与命令执行；当前只展示快捷键说明。
 */
export function CommandPalette(): JSX.Element | null {
  const open = useUiStore((state) => state.commandOpen)
  const toggleCommand = useUiStore((state) => state.toggleCommand)

  if (!open) return null

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-[90] flex items-start justify-center bg-black/50 px-4 pt-[16vh]"
      onClick={() => toggleCommand(false)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={zhCN.command.title}
        className="melody-fade-in w-full max-w-lg overflow-hidden rounded-[var(--radius-lg)] border border-border bg-bg-elevated shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Command size={15} className="text-accent" aria-hidden="true" />
          <h2 className="text-sm font-medium text-fg">{zhCN.command.title}</h2>
          <kbd className="ml-auto rounded border border-border px-1.5 py-0.5 text-[10px] text-fg-muted">
            Esc
          </kbd>
        </div>

        <input
          autoFocus
          type="text"
          placeholder={zhCN.command.placeholder}
          aria-label={zhCN.command.title}
          className="w-full bg-transparent px-4 py-3 text-sm text-fg placeholder:text-fg-muted/70 focus:outline-none"
        />

        <div className="border-t border-border px-4 py-3">
          <p className="mb-3 text-[11px] leading-5 text-fg-muted">{zhCN.command.hint}</p>
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-fg-muted">
            {zhCN.command.shortcutsTitle}
          </p>
          <ul className="space-y-1">
            {SHORTCUTS.map((shortcut) => (
              <li key={shortcut.keys} className="flex items-center justify-between gap-4 text-xs">
                <span className="text-fg">{shortcut.label}</span>
                <kbd className="rounded border border-border bg-bg px-1.5 py-0.5 text-[10px] text-fg-muted">
                  {shortcut.keys}
                </kbd>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
