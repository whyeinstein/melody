import { useEffect, useState } from 'react'
import type { JSX } from 'react'
import type { AppInfo } from '@shared/ipc/contracts'

function StatusPill({ ok, label, detail }: { ok: boolean; label: string; detail?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2">
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: ok ? 'var(--color-success)' : 'var(--color-danger)' }}
      />
      <span className="text-sm">{label}</span>
      {detail ? <span className="text-xs text-[var(--color-fg-muted)]">{detail}</span> : null}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-[var(--color-border)] py-2 last:border-b-0">
      <span className="text-sm text-[var(--color-fg-muted)]">{label}</span>
      <span className="text-sm break-all text-right">{value}</span>
    </div>
  )
}

export function App(): JSX.Element {
  const [info, setInfo] = useState<AppInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    window.melody
      .invoke('app:info')
      .then((result) => {
        if (cancelled) return
        if (result.ok) setInfo(result.data)
        else setError(result.error.message)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : String(reason))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex min-h-full items-center justify-center p-10">
      <div className="w-full max-w-3xl">
        <div className="mb-8 flex items-center gap-4">
          <div
            className="flex h-14 w-14 items-center justify-center rounded-[var(--radius-lg)] text-2xl"
            style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}
          >
            ♪
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-wide">Melody</h1>
            <p className="text-sm text-[var(--color-fg-muted)]">本地音乐播放器 · 工程骨架（阶段 0）</p>
          </div>
        </div>

        <div
          className="rounded-[var(--radius-lg)] border border-[var(--color-border)] p-6"
          style={{ background: 'var(--color-bg-elevated)' }}
        >
          {error ? (
            <p className="text-sm" style={{ color: 'var(--color-danger)' }}>
              读取应用信息失败：{error}
            </p>
          ) : !info ? (
            <p className="text-sm text-[var(--color-fg-muted)]">正在读取运行环境…</p>
          ) : (
            <>
              <div className="mb-5 flex flex-wrap gap-2">
                <StatusPill
                  ok={info.storage.ok}
                  label={info.storage.ok ? `存储引擎 ${info.storage.engine}` : '存储引擎不可用'}
                  detail={info.storage.ok ? undefined : info.storage.detail}
                />
                <StatusPill
                  ok={info.ffmpeg.found}
                  label={info.ffmpeg.found ? 'ffmpeg 已就绪' : 'ffmpeg 未找到'}
                  detail={info.ffmpeg.found ? info.ffmpeg.version : '阶段 2 转码需要'}
                />
              </div>
              <div>
                <Row label="版本" value={info.version} />
                <Row label="Electron" value={info.electron} />
                <Row label="Chromium" value={info.chrome} />
                <Row label="Node" value={info.node} />
                <Row label="平台" value={`${info.platform} / ${info.arch}`} />
                <Row label="数据目录" value={info.userDataPath} />
                <Row label="ffmpeg 路径" value={info.ffmpeg.path ?? '—'} />
              </div>
            </>
          )}
        </div>

        <p className="mt-6 text-xs text-[var(--color-fg-muted)]">
          阶段 0 验收：真实窗口 + 类型化 IPC 往返 + 存储选型实测。下一步进入音乐库扫描与播放核心。
        </p>
      </div>
    </div>
  )
}
