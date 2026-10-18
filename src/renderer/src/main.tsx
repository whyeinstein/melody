import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { zhCN } from './i18n/zh-CN'
import './styles/global.css'

const container = document.getElementById('root')
if (!container) throw new Error(zhCN.errors.rootContainer)

createRoot(container).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
)
