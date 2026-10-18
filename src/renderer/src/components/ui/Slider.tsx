import type { ChangeEvent, JSX } from 'react'
import { cn } from '../../lib/cn'
import { clamp, percentOf } from '../../lib/format'

export interface SliderProps {
  value: number
  max: number
  min?: number
  step?: number
  onChange: (value: number) => void
  /** 拖动结束（或键盘调整结束）时回调，用于真正提交 seek。 */
  onCommit?: (value: number) => void
  ariaLabel: string
  valueText?: string
  disabled?: boolean
  className?: string
}

/**
 * 滑块：进度条与音量条共用。
 * 使用原生 input[type=range] 保证键盘与无障碍支持，视觉上叠加自定义轨道。
 */
export function Slider({
  value,
  max,
  min = 0,
  step = 1,
  onChange,
  onCommit,
  ariaLabel,
  valueText,
  disabled = false,
  className
}: SliderProps): JSX.Element {
  const upperBound = Math.max(max, min)
  const safeValue = clamp(value, min, upperBound)
  const percent = percentOf(safeValue - min, upperBound - min)

  const handleChange = (event: ChangeEvent<HTMLInputElement>): void => {
    onChange(Number(event.target.value))
  }

  const commit = (input: HTMLInputElement): void => {
    onCommit?.(Number(input.value))
  }

  return (
    <div className={cn('group relative flex h-4 w-full items-center', disabled && 'opacity-40', className)}>
      <div className="pointer-events-none absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-bg-active" />
      <div
        className="pointer-events-none absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-accent"
        style={{ width: `${percent}%` }}
      />
      <input
        className="melody-range relative z-10 w-full"
        type="range"
        min={min}
        max={upperBound}
        step={step}
        value={safeValue}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-valuetext={valueText}
        onChange={handleChange}
        onPointerUp={(event) => commit(event.currentTarget)}
        onKeyUp={(event) => commit(event.currentTarget)}
        onBlur={(event) => commit(event.currentTarget)}
      />
    </div>
  )
}
