import type { ErrorInfo, ReactNode } from 'react'
import { Component } from 'react'
import { CircleAlert } from 'lucide-react'
import { zhCN } from '../i18n/zh-CN'
import { Button } from '../components/ui/Button'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/** 渲染层兜底：任何组件异常都不应该让整个界面变成白屏。 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[Melody] 渲染层异常:', error, info.componentStack)
  }

  override render(): ReactNode {
    const { error } = this.state
    if (error === null) return this.props.children

    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 bg-bg p-10 text-center text-fg">
        <CircleAlert size={28} className="text-danger" aria-hidden="true" />
        <div className="space-y-1">
          <h1 className="text-base font-semibold">{zhCN.errors.generic}</h1>
          <p className="max-w-lg break-words text-sm text-fg-muted">{error.message}</p>
        </div>
        <Button variant="primary" onClick={() => this.setState({ error: null })}>
          {zhCN.common.retry}
        </Button>
      </div>
    )
  }
}
