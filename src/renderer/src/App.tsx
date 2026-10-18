import type { JSX } from 'react'
import { CommandPalette } from './components/layout/CommandPalette'
import { MainView } from './components/layout/MainView'
import { PlayerBar } from './components/layout/PlayerBar'
import { QueueDrawer } from './components/layout/QueueDrawer'
import { Sidebar } from './components/layout/Sidebar'
import { ToastViewport } from './components/ui/Toast'
import { useAppBootstrap } from './hooks/useAppBootstrap'
import { useAudioEngine } from './hooks/useAudioEngine'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { useTheme } from './hooks/useTheme'

/**
 * 应用外壳：
 * ┌──────────┬──────────────────────┬──────────┐
 * │ 侧边导航  │ 主内容区              │ 队列抽屉  │
 * ├──────────┴──────────────────────┴──────────┤
 * │ 播放条                                     │
 * └────────────────────────────────────────────┘
 */
export function App(): JSX.Element {
  useTheme()
  const bootstrap = useAppBootstrap()
  useAudioEngine()
  useKeyboardShortcuts()

  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg text-fg">
      <div className="flex min-h-0 flex-1">
        <Sidebar
          info={bootstrap.info}
          infoError={bootstrap.infoError}
          configError={bootstrap.configError}
        />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <MainView />
        </main>
        <QueueDrawer />
      </div>
      <PlayerBar />
      <ToastViewport />
      <CommandPalette />
    </div>
  )
}
