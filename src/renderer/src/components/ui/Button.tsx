import type { ButtonHTMLAttributes, JSX, ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** 可选的前置图标（传入 <Icon size={16} /> 即可）。 */
  leadingIcon?: ReactNode
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-white hover:brightness-110 active:brightness-95',
  secondary: 'border border-border bg-bg-elevated text-fg hover:bg-bg-hover',
  ghost: 'text-fg-muted hover:bg-bg-hover hover:text-fg',
  danger: 'border border-danger/40 text-danger hover:bg-danger/10'
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4 text-sm'
}

/** 基础按钮：深色界面下的统一视觉与交互状态。 */
export function Button({
  variant = 'secondary',
  size = 'md',
  leadingIcon,
  className,
  type = 'button',
  children,
  ...rest
}: ButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex select-none items-center justify-center gap-2 rounded-[var(--radius-md)] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className
      )}
      {...rest}
    >
      {leadingIcon}
      {children}
    </button>
  )
}
