import type { JSX } from 'react'
import type { AppInfo } from '@shared/ipc/contracts'
import {
  AudioLines,
  CircleAlert,
  Clock,
  Disc3,
  FolderOpen,
  FolderPlus,
  Heart,
  Library,
  ListMusic,
  Play,
  Tags,
  Users
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { useLibraryStore } from '../../stores/library-store'
import { Button } from '../ui/Button'
import { useUiStore, type NavView } from '../../stores/ui-store'

interface NavItem {
  view: NavView
  label: string
  icon: LucideIcon
}

const NAV_ITEMS: readonly NavItem[] = [
  { view: 'songs', label: zhCN.nav.songs, icon: ListMusic },
  { view: 'albums', label: zhCN.nav.albums, icon: Disc3 },
  { view: 'artists', label: zhCN.nav.artists, icon: Users },
  { view: 'genres', label: zhCN.nav.genres, icon: Tags },
  { view: 'folders', label: zhCN.nav.folders, icon: FolderOpen },
  { view: 'recent', label: zhCN.nav.recent, icon: Clock },
  { view: 'favorites', label: zhCN.nav.favorites, icon: Heart },
  { view: 'playlists', label: zhCN.nav.playlists, icon: Library }
]

interface SidebarProps {
  info: AppInfo | null
  infoError: string | null
  configError: string | null
}

function ScanCard(): JSX.Element {
  const scan = useLibraryStore((state) => state.scan)
  const scanError = useLibraryStore((state) => state.scanError)
  const folders = useLibraryStore((state) => state.folders)
  const addFolders = useLibraryStore((state) => state.addFolders)
  const startScan = useLibraryStore((state) => state.startScan)
  const cancelScan = useLibraryStore((state) => state.cancelScan)

  const scanning = scan.state === 'scanning'
  const hasFolders = folders.length > 0

  return (
    <div className="space-y-2 rounded-[var(--radius-md)] border border-border bg-bg-elevated p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-fg">{zhCN.library.foldersTitle}</span>
        {scanning ? (
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" onClick={() => void cancelScan()}>
            {zhCN.library.cancelScan}
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[11px]"
            disabled={!hasFolders}
            leadingIcon={<Play size={12} aria-hidden="true" />}
            onClick={() => void startScan()}
          >
            {zhCN.library.startScan}
          </Button>
        )}
      </div>

      {scanning ? (
        <>
          <div className="h-1 overflow-hidden rounded-full bg-bg-active">
            <div className="melody-indeterminate h-full w-1/3 rounded-full bg-accent" />
          </div>
          <p className="truncate text-[11px] text-fg-muted">
            {scan.currentPath ?? zhCN.library.scanScanning}
          </p>
          <p className="text-[11px] text-fg-muted">
            {zhCN.library.scanSummary(scan.added, scan.updated)}
          </p>
        </>
      ) : (
        <button
          type="button"
          className="flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-sm)] border border-dashed border-border py-1.5 text-[11px] text-fg-muted transition-colors hover:border-accent hover:text-accent"
          onClick={() => void addFolders()}
        >
          <FolderPlus size={13} aria-hidden="true" />
          {zhCN.library.addFolder}
        </button>
      )}

      {scanError !== null && !scanning ? (
        <p className="line-clamp-2 text-[11px] leading-4 text-danger">{scanError}</p>
      ) : null}
    </div>
  )
}

function StatusLine({ info }: { info: AppInfo | null }): JSX.Element {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-fg-muted">
      <span className="flex items-center gap-1.5">
        <span
          className={cn('h-1.5 w-1.5 rounded-full', info?.storage.ok === true ? 'bg-success' : 'bg-danger')}
        />
        {info === null
          ? zhCN.common.loading
          : info.storage.ok
            ? zhCN.status.storageOk(info.storage.engine)
            : zhCN.status.storageUnavailable}
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className={cn('h-1.5 w-1.5 rounded-full', info?.ffmpeg.found === true ? 'bg-success' : 'bg-warning')}
        />
        {info?.ffmpeg.found === true ? zhCN.status.ffmpegFound : zhCN.status.ffmpegMissing}
      </span>
    </div>
  )
}

/** 左侧导航栏：音乐库分类 + 扫描状态 + 运行环境状态。 */
export function Sidebar({ info, infoError, configError }: SidebarProps): JSX.Element {
  const activeView = useUiStore((state) => state.activeView)
  const setActiveView = useUiStore((state) => state.setActiveView)
  const scan = useLibraryStore((state) => state.scan)

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-bg-elevated">
      <div className="flex h-16 shrink-0 items-center gap-3 px-4">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] text-accent"
          style={{ background: 'var(--color-accent-soft)' }}
        >
          <AudioLines size={19} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-wide text-fg">{zhCN.app.name}</p>
          <p className="truncate text-[11px] text-fg-muted">{zhCN.app.tagline}</p>
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-2" aria-label={zhCN.nav.libraryGroup}>
        <p className="px-2 pb-1.5 pt-3 text-[11px] font-medium uppercase tracking-wider text-fg-muted">
          {zhCN.nav.libraryGroup}
        </p>
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = activeView === item.view
            const Icon = item.icon
            return (
              <li key={item.view}>
                <button
                  type="button"
                  aria-current={active ? 'page' : undefined}
                  onClick={() => setActiveView(item.view)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-[var(--radius-sm)] px-2.5 py-2 text-sm transition-colors',
                    active
                      ? 'bg-accent-soft font-medium text-accent'
                      : 'text-fg-muted hover:bg-bg-hover hover:text-fg'
                  )}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span className="truncate">{item.label}</span>
                  {item.view === 'folders' && scan.state === 'scanning' ? (
                    <span className="ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  ) : null}
                </button>
              </li>
            )
          })}
        </ul>

        <div className="mt-3 px-2">
          <ScanCard />
        </div>
      </nav>

      <div className="shrink-0 space-y-2 border-t border-border p-3">
        <StatusLine info={info} />
        {infoError !== null ? (
          <p className="flex items-start gap-1.5 text-[11px] leading-4 text-warning">
            <CircleAlert size={12} className="mt-0.5 shrink-0" aria-hidden="true" />
            {infoError}
          </p>
        ) : null}
        {configError !== null ? (
          <p className="flex items-start gap-1.5 text-[11px] leading-4 text-fg-muted">
            <CircleAlert size={12} className="mt-0.5 shrink-0" aria-hidden="true" />
            {zhCN.errors.configUnavailable}
          </p>
        ) : null}
        {info !== null ? (
          <p className="truncate text-[11px] text-fg-muted" title={info.userDataPath}>
            {zhCN.app.version(info.version)} · {zhCN.app.stage}
          </p>
        ) : null}
      </div>
    </aside>
  )
}
