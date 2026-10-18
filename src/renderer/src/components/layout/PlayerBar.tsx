import { useEffect, useState } from 'react'
import type { JSX } from 'react'
import {
  Heart,
  ListMusic,
  Pause,
  Play,
  Repeat,
  Repeat1,
  Shuffle,
  SkipBack,
  SkipForward,
  Volume1,
  Volume2,
  VolumeX
} from 'lucide-react'
import { zhCN } from '../../i18n/zh-CN'
import { cn } from '../../lib/cn'
import { formatDuration } from '../../lib/format'
import {
  cycleRepeat,
  playNext,
  playPrevious,
  seekTo,
  setVolume,
  toggleMute,
  togglePlay,
  toggleShuffle
} from '../../lib/playback'
import { useLibraryStore } from '../../stores/library-store'
import { usePlayerStore } from '../../stores/player-store'
import { selectCurrentTrack, useQueueStore } from '../../stores/queue-store'
import { useUiStore } from '../../stores/ui-store'
import { CoverArt } from '../ui/CoverArt'
import { IconButton } from '../ui/IconButton'
import { Slider } from '../ui/Slider'

/** 底部播放条：当前曲目信息 + 传输控制 + 进度 + 音量 + 队列开关。 */
export function PlayerBar(): JSX.Element {
  const track = useQueueStore(selectCurrentTrack)
  const queueEmpty = useQueueStore((state) => state.items.length === 0)
  const status = usePlayerStore((state) => state.status)
  const currentTimeMs = usePlayerStore((state) => state.currentTimeMs)
  const playerDurationMs = usePlayerStore((state) => state.durationMs)
  const volume = usePlayerStore((state) => state.volume)
  const muted = usePlayerStore((state) => state.muted)
  const shuffle = usePlayerStore((state) => state.shuffle)
  const repeat = usePlayerStore((state) => state.repeat)
  const queueOpen = useUiStore((state) => state.queueOpen)
  const toggleQueue = useUiStore((state) => state.toggleQueue)
  const toggleFavorite = useLibraryStore((state) => state.toggleFavorite)

  // 拖动进度条时用本地预览值，避免音频时间回写导致滑块跳动。
  const [previewMs, setPreviewMs] = useState<number | null>(null)

  useEffect(() => {
    setPreviewMs(null)
  }, [track?.id])

  const durationMs = playerDurationMs > 0 ? playerDurationMs : (track?.durationMs ?? 0)
  const playedMs = previewMs ?? Math.min(currentTimeMs, durationMs > 0 ? durationMs : currentTimeMs)
  const playing = status === 'playing'
  const loading = status === 'loading'
  const repeatActive = repeat !== 'off'

  return (
    <footer className="flex h-20 shrink-0 items-center gap-4 border-t border-border bg-bg-elevated px-4">
      {/* 当前曲目 */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <CoverArt coverId={track?.coverId ?? null} size={48} />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-fg">
            {track?.title ?? zhCN.player.nothingPlaying}
          </p>
          <p className="truncate text-xs text-fg-muted">
            {track?.artist ?? zhCN.common.unknownArtist}
          </p>
        </div>
        {track !== null ? (
          <button
            type="button"
            aria-label={track.favorite ? zhCN.actions.removeFavorite : zhCN.actions.addFavorite}
            title={track.favorite ? zhCN.actions.removeFavorite : zhCN.actions.addFavorite}
            className="ml-1 rounded-full p-1.5 text-fg-muted transition-colors hover:bg-bg-hover hover:text-fg"
            onClick={() => void toggleFavorite(track)}
          >
            <Heart
              size={16}
              className={cn(track.favorite && 'text-accent')}
              fill={track.favorite ? 'currentColor' : 'none'}
              aria-hidden="true"
            />
          </button>
        ) : null}
      </div>

      {/* 传输控制 + 进度 */}
      <div className="flex min-w-0 flex-[1.8] flex-col items-center gap-1">
        <div className="flex items-center gap-1.5">
          <IconButton
            icon={Shuffle}
            label={zhCN.player.shuffleOn}
            size="sm"
            active={shuffle}
            disabled={queueEmpty}
            onClick={toggleShuffle}
          />
          <IconButton
            icon={SkipBack}
            label={zhCN.actions.previous}
            size="md"
            disabled={queueEmpty}
            onClick={playPrevious}
          />
          <button
            type="button"
            aria-label={playing ? zhCN.actions.pause : zhCN.actions.play}
            title={playing ? zhCN.actions.pause : zhCN.actions.play}
            disabled={queueEmpty}
            onClick={togglePlay}
            className="mx-1 flex h-10 w-10 items-center justify-center rounded-full bg-accent text-white shadow-lg transition hover:brightness-110 disabled:pointer-events-none disabled:opacity-40"
          >
            {playing ? (
              <Pause size={18} fill="currentColor" aria-hidden="true" />
            ) : (
              <Play size={18} fill="currentColor" className="ml-0.5" aria-hidden="true" />
            )}
          </button>
          <IconButton
            icon={SkipForward}
            label={zhCN.actions.next}
            size="md"
            disabled={queueEmpty}
            onClick={() => playNext(false)}
          />
          <IconButton
            icon={repeat === 'one' ? Repeat1 : Repeat}
            label={
              repeat === 'one'
                ? zhCN.player.repeatOne
                : repeat === 'all'
                  ? zhCN.player.repeatAll
                  : zhCN.player.repeatOff
            }
            size="sm"
            active={repeatActive}
            disabled={queueEmpty}
            onClick={cycleRepeat}
          />
        </div>

        <div className="flex w-full items-center gap-2">
          <span className="w-10 text-right text-[11px] tabular-nums text-fg-muted">
            {formatDuration(playedMs)}
          </span>
          <Slider
            className="flex-1"
            value={playedMs}
            max={durationMs}
            step={1000}
            disabled={track === null || durationMs <= 0}
            ariaLabel={zhCN.player.progress}
            valueText={`${formatDuration(playedMs)} / ${formatDuration(durationMs)}`}
            onChange={(value) => setPreviewMs(value)}
            onCommit={(value) => {
              seekTo(value)
              setPreviewMs(null)
            }}
          />
          <span className="w-10 text-[11px] tabular-nums text-fg-muted">
            {formatDuration(durationMs)}
          </span>
        </div>
      </div>

      {/* 音量 + 队列 */}
      <div className="flex min-w-0 flex-1 items-center justify-end gap-1">
        {loading ? (
          <span className="mr-1 text-[11px] text-fg-muted">{zhCN.common.loading}</span>
        ) : null}
        <IconButton
          icon={muted || volume === 0 ? VolumeX : volume < 0.5 ? Volume1 : Volume2}
          label={muted ? zhCN.player.unmute : zhCN.player.mute}
          size="sm"
          onClick={toggleMute}
        />
        <div className="w-24">
          <Slider
            value={muted ? 0 : volume}
            max={1}
            step={0.01}
            ariaLabel={zhCN.player.volume}
            valueText={`${Math.round((muted ? 0 : volume) * 100)}%`}
            onChange={setVolume}
            onCommit={setVolume}
          />
        </div>
        <IconButton
          icon={ListMusic}
          label={queueOpen ? zhCN.queue.close : zhCN.player.queue}
          size="md"
          active={queueOpen}
          className="ml-1"
          onClick={() => toggleQueue()}
        />
      </div>
    </footer>
  )
}
