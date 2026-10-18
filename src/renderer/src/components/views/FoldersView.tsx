import { useEffect } from 'react'
import type { JSX } from 'react'
import type { ScanProgress } from '@shared/domain/types'
import { CircleAlert, FolderPlus, Play, RefreshCw, Trash, WifiOff } from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { useLibraryStore } from '../../stores/library-store'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'
import { IconButton } from '../ui/IconButton'

function scanLabel(scan: ScanProgress): string {
  switch (scan.state) {
    case 'scanning':
      return zhCN.library.scanScanning
    case 'done':
      return zhCN.library.scanDone
    case 'cancelled':
      return zhCN.library.scanCancelled
    case 'error':
      return zhCN.library.scanError
    default:
      return zhCN.library.scanIdle
  }
}

function ScanSummary({ scan }: { scan: ScanProgress }): JSX.Element {
  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-bg-elevated p-3 text-xs text-fg-muted">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-fg">{scanLabel(scan)}</span>
        <span>{zhCN.library.scanSummary(scan.added, scan.updated)}</span>
      </div>
      {scan.state === 'scanning' ? (
        <>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-bg-active">
            <div className="melody-indeterminate h-full w-1/3 rounded-full bg-accent" />
          </div>
          {scan.currentPath !== undefined ? (
            <p className="mt-1 truncate" title={scan.currentPath}>
              {scan.currentPath}
            </p>
          ) : null}
        </>
      ) : null}
      <p className="mt-1.5">
        {zhCN.library.scanCounters(scan.visited, scan.parsed, scan.failed)}
      </p>
    </div>
  )
}

/** 音乐文件夹管理：添加/移除目录，启动/取消扫描，展示扫描进度。 */
export function FoldersView(): JSX.Element {
  const folders = useLibraryStore((state) => state.folders)
  const status = useLibraryStore((state) => state.collectionStatus.folders)
  const error = useLibraryStore((state) => state.collectionErrors.folders)
  const unavailable = useLibraryStore((state) => state.collectionUnavailable.folders)
  const scan = useLibraryStore((state) => state.scan)
  const scanError = useLibraryStore((state) => state.scanError)
  const loadFolders = useLibraryStore((state) => state.loadFolders)
  const addFolders = useLibraryStore((state) => state.addFolders)
  const removeFolder = useLibraryStore((state) => state.removeFolder)
  const startScan = useLibraryStore((state) => state.startScan)
  const cancelScan = useLibraryStore((state) => state.cancelScan)

  useEffect(() => {
    if (status === 'idle') void loadFolders()
  }, [loadFolders, status])

  if (status === 'error' && folders.length === 0) {
    return (
      <EmptyState
        icon={unavailable ? WifiOff : CircleAlert}
        tone={unavailable ? 'default' : 'error'}
        title={unavailable ? zhCN.library.channelNotReady : zhCN.library.loadFailed}
        description={unavailable ? zhCN.library.channelNotReadyHint : (error ?? zhCN.errors.generic)}
        action={
          <Button leadingIcon={<RefreshCw size={14} />} onClick={() => void loadFolders()}>
            {zhCN.common.retry}
          </Button>
        }
      />
    )
  }

  const scanning = scan.state === 'scanning'

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-fg">{zhCN.library.foldersTitle}</h2>
          <p className="mt-0.5 text-xs text-fg-muted">{zhCN.library.foldersHint}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button leadingIcon={<FolderPlus size={15} />} onClick={() => void addFolders()}>
            {zhCN.library.addFolder}
          </Button>
          {scanning ? (
            <Button variant="ghost" onClick={() => void cancelScan()}>
              {zhCN.library.cancelScan}
            </Button>
          ) : (
            <Button
              variant="primary"
              leadingIcon={<Play size={15} />}
              disabled={folders.length === 0}
              onClick={() => void startScan()}
            >
              {zhCN.library.startScan}
            </Button>
          )}
        </div>
      </div>

      {scan.state !== 'idle' || scanError !== null ? <ScanSummary scan={scan} /> : null}
      {scanError !== null && !scanning ? (
        <p className="text-xs text-danger">{scanError}</p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {folders.length === 0 ? (
          <EmptyState
            icon={FolderPlus}
            title={zhCN.library.foldersEmpty}
            description={zhCN.library.foldersEmptyHint}
            action={
              <Button variant="primary" onClick={() => void addFolders()}>
                {zhCN.library.addFolder}
              </Button>
            }
          />
        ) : (
          <ul className="space-y-2">
            {folders.map((folder) => (
              <li
                key={folder.id}
                className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-bg-elevated px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-fg" title={folder.path}>
                    {folder.path}
                  </p>
                  <p className="text-xs text-fg-muted">
                    {zhCN.library.totalTracks(folder.trackCount)}
                    {folder.enabled ? '' : ` · ${zhCN.library.folderDisabled}`}
                  </p>
                </div>
                <IconButton
                  icon={Trash}
                  label={zhCN.library.removeFolder}
                  size="sm"
                  onClick={() => void removeFolder(folder.id)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
