import { Fragment, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { JSX } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/cn'

export interface ContextMenuItem {
  id: string
  label: string
  icon?: LucideIcon
  danger?: boolean
  disabled?: boolean
  separatorBefore?: boolean
  onSelect: () => void
}

export interface ContextMenuProps {
  /** 触发位置（视口坐标）。 */
  x: number
  y: number
  items: ContextMenuItem[]
  onClose: () => void
}

const VIEWPORT_MARGIN = 8

/** 轻量右键菜单：点击外部或按 Esc 关闭，自动避免超出窗口边界。 */
export function ContextMenu({ x, y, items, onClose }: ContextMenuProps): JSX.Element {
  const ref = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ left: x, top: y })

  useLayoutEffect(() => {
    const element = ref.current
    if (element === null) return
    const rect = element.getBoundingClientRect()
    setPosition({
      left: Math.max(VIEWPORT_MARGIN, Math.min(x, window.innerWidth - rect.width - VIEWPORT_MARGIN)),
      top: Math.max(VIEWPORT_MARGIN, Math.min(y, window.innerHeight - rect.height - VIEWPORT_MARGIN))
    })
  }, [x, y])

  useEffect(() => {
    const onPointerDown = (event: globalThis.PointerEvent): void => {
      const target = event.target
      if (target instanceof Node && ref.current?.contains(target) === true) return
      onClose()
    }
    const onKeyDown = (event: globalThis.KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      onClose()
    }
    window.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown, true)
    return () => {
      window.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown, true)
    }
  }, [onClose])

  return (
    <div
      ref={ref}
      role="menu"
      className="fixed z-[70] min-w-44 rounded-[var(--radius-md)] border border-border bg-bg-elevated py-1 shadow-2xl"
      style={{ left: position.left, top: position.top }}
      onContextMenu={(event) => event.preventDefault()}
    >
      {items.map((item) => {
        const ItemIcon = item.icon
        return (
          <Fragment key={item.id}>
            {item.separatorBefore === true ? <div className="my-1 h-px bg-border" /> : null}
            <button
              type="button"
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                item.onSelect()
                onClose()
              }}
              className={cn(
                'flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors disabled:pointer-events-none disabled:opacity-40',
                item.danger === true
                  ? 'text-danger hover:bg-danger/10'
                  : 'text-fg hover:bg-bg-hover'
              )}
            >
              {ItemIcon !== undefined ? <ItemIcon size={15} aria-hidden="true" /> : null}
              {item.label}
            </button>
          </Fragment>
        )
      })}
    </div>
  )
}
