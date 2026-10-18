import { useEffect } from 'react'
import type { JSX } from 'react'
import { CircleAlert, CircleCheck, Info, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { useUiStore, type ToastKind, type ToastMessage } from '../../stores/ui-store'

/** 提示自动消失时间。 */
const TOAST_DURATION_MS = 4200

const ICONS: Record<ToastKind, LucideIcon> = {
  info: Info,
  success: CircleCheck,
  error: CircleAlert
}

const TONE_CLASSES: Record<ToastKind, string> = {
  info: 'text-accent',
  success: 'text-success',
  error: 'text-danger'
}

function ToastItem({ toast }: { toast: ToastMessage }): JSX.Element {
  const dismissToast = useUiStore((state) => state.dismissToast)

  useEffect(() => {
    const timer = window.setTimeout(() => dismissToast(toast.id), TOAST_DURATION_MS)
    return () => window.clearTimeout(timer)
  }, [dismissToast, toast.id])

  const Icon = ICONS[toast.kind]

  return (
    <div
      role="status"
      className="melody-toast-in pointer-events-auto flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-bg-elevated px-3.5 py-3 shadow-2xl"
    >
      <Icon size={17} className={cn('mt-0.5 shrink-0', TONE_CLASSES[toast.kind])} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-fg">{toast.title}</p>
        {toast.description !== undefined ? (
          <p className="mt-0.5 break-words text-xs leading-5 text-fg-muted">{toast.description}</p>
        ) : null}
      </div>
      <button
        type="button"
        aria-label={zhCN.common.close}
        className="rounded p-0.5 text-fg-muted transition-colors hover:bg-bg-hover hover:text-fg"
        onClick={() => dismissToast(toast.id)}
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  )
}

/** 右下角提示堆栈。 */
export function ToastViewport(): JSX.Element | null {
  const toasts = useUiStore((state) => state.toasts)
  if (toasts.length === 0) return null
  return (
    <div className="pointer-events-none fixed bottom-24 right-4 z-[80] flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  )
}
