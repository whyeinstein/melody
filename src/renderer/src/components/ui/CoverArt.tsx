import { useEffect, useState } from 'react'
import type { JSX } from 'react'
import { AudioLines } from 'lucide-react'
import { cn } from '../../lib/cn'
import { buildCoverUrl, ensureMediaSession } from '../../lib/media'

export interface CoverArtProps {
  coverId: number | null
  size: number
  className?: string
}

/**
 * 专辑封面。
 * 通过主进程媒体服务（`/covers/{id}?token=...`）加载，没有封面时显示音符占位图。
 */
export function CoverArt({ coverId, size, className }: CoverArtProps): JSX.Element {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (coverId === null) {
      setUrl(null)
      return
    }
    let cancelled = false
    void ensureMediaSession().then((session) => {
      if (cancelled) return
      setUrl(session === null ? null : buildCoverUrl(session, coverId))
    })
    return () => {
      cancelled = true
    }
  }, [coverId])

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-[var(--radius-sm)] bg-bg-active text-fg-muted',
        className
      )}
      style={{ width: size, height: size }}
    >
      {url === null ? (
        <AudioLines size={Math.max(14, Math.round(size * 0.4))} aria-hidden="true" />
      ) : (
        <img
          src={url}
          alt=""
          width={size}
          height={size}
          loading="lazy"
          draggable={false}
          className="h-full w-full select-none object-cover"
        />
      )}
    </div>
  )
}
