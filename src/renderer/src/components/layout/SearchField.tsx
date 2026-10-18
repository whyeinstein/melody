import type { JSX } from 'react'
import { Search, X } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { SEARCH_INPUT_ID } from '../../lib/dom'
import { useLibraryStore } from '../../stores/library-store'

/** 顶栏搜索框（Ctrl+F 会聚焦到这里）。 */
export function SearchField({ className }: { className?: string }): JSX.Element {
  const search = useLibraryStore((state) => state.search)
  const setSearch = useLibraryStore((state) => state.setSearch)

  return (
    <div className={cn('relative flex w-full max-w-md items-center', className)}>
      <Search
        size={15}
        className="pointer-events-none absolute left-3 text-fg-muted"
        aria-hidden="true"
      />
      <input
        id={SEARCH_INPUT_ID}
        type="text"
        value={search}
        placeholder={zhCN.search.placeholder}
        aria-label={zhCN.search.label}
        spellCheck={false}
        onChange={(event) => setSearch(event.target.value)}
        className="h-9 w-full rounded-full border border-border bg-bg-elevated pl-9 pr-9 text-sm text-fg placeholder:text-fg-muted/70 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
      />
      {search.length > 0 ? (
        <button
          type="button"
          aria-label={zhCN.search.clear}
          title={zhCN.search.clear}
          onClick={() => setSearch('')}
          className="absolute right-2.5 rounded-full p-1 text-fg-muted transition-colors hover:bg-bg-hover hover:text-fg"
        >
          <X size={13} aria-hidden="true" />
        </button>
      ) : (
        <kbd className="pointer-events-none absolute right-3 hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-fg-muted sm:inline">
          Ctrl F
        </kbd>
      )}
    </div>
  )
}
