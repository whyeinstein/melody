import type { ButtonHTMLAttributes, JSX } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/cn'

export type IconButtonSize = 'sm' | 'md' | 'lg'

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icon: LucideIcon
  /** 无障碍标签，同时作为 title 提示。 */
  label: string
  size?: IconButtonSize
  /** 激活态（例如随机播放已开启）。 */
  active?: boolean
}

const SIZE_CLASSES: Record<IconButtonSize, string> = {
  sm: 'h-7 w-7',
  md: 'h-9 w-9',
  lg: 'h-11 w-11'
}

const ICON_SIZES: Record<IconButtonSize, number> = { sm: 15, md: 18, lg: 22 }

export function IconButton({
  icon: Icon,
  label,
  size = 'md',
  active = false,
  className,
  type = 'button',
  ...rest
}: IconButtonProps): JSX.Element {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      aria-pressed={active ? true : undefined}
      className={cn(
        'inline-flex items-center justify-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-40',
        SIZE_CLASSES[size],
        active ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-bg-hover hover:text-fg',
        className
      )}
      {...rest}
    >
      <Icon size={ICON_SIZES[size]} aria-hidden="true" />
    </button>
  )
}
