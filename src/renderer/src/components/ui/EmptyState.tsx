import type { JSX, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/cn'

export interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: ReactNode
  tone?: 'default' | 'error'
  className?: string
}

/** 空状态 / 错误状态（主进程频道未实现时也用它展示降级提示）。 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = 'default',
  className
}: EmptyStateProps): JSX.Element {
  return (
    <div className={cn('flex h-full flex-col items-center justify-center gap-4 px-8 py-16 text-center', className)}>
      {Icon !== undefined ? (
        <div
          className={cn(
            'flex h-14 w-14 items-center justify-center rounded-full border border-border',
            tone === 'error' ? 'text-danger' : 'text-fg-muted'
          )}
          style={{ background: 'var(--color-bg-elevated)' }}
        >
          <Icon size={24} aria-hidden="true" />
        </div>
      ) : null}
      <div className="space-y-1.5">
        <h2 className="text-base font-semibold text-fg">{title}</h2>
        {description !== undefined ? (
          <p className="mx-auto max-w-md text-sm leading-6 text-fg-muted">{description}</p>
        ) : null}
      </div>
      {action !== undefined ? <div className="flex items-center gap-2">{action}</div> : null}
    </div>
  )
}
