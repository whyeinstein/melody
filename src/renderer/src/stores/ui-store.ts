import { create } from 'zustand'

/** 左侧导航对应的主视图。 */
export type NavView =
  | 'songs'
  | 'albums'
  | 'artists'
  | 'genres'
  | 'folders'
  | 'recent'
  | 'favorites'
  | 'playlists'

export type ThemeMode = 'dark' | 'light' | 'system'

export type ToastKind = 'info' | 'success' | 'error'

export interface ToastMessage {
  id: number
  kind: ToastKind
  title: string
  description?: string
}

export interface UiState {
  activeView: NavView
  theme: ThemeMode
  /** 右侧播放队列抽屉是否展开。 */
  queueOpen: boolean
  /** Ctrl+K 命令面板是否打开（占位实现）。 */
  commandOpen: boolean
  toasts: ToastMessage[]

  setActiveView: (view: NavView) => void
  setTheme: (theme: ThemeMode) => void
  toggleQueue: (open?: boolean) => void
  toggleCommand: (open?: boolean) => void
  pushToast: (toast: Omit<ToastMessage, 'id'>) => number
  dismissToast: (id: number) => void
}

let toastSeq = 0

export const useUiStore = create<UiState>()((set, get) => ({
  activeView: 'songs',
  theme: 'dark',
  queueOpen: false,
  commandOpen: false,
  toasts: [],

  setActiveView: (activeView) => set({ activeView }),

  setTheme: (theme) => set({ theme }),

  toggleQueue: (open) => set({ queueOpen: open ?? !get().queueOpen }),

  toggleCommand: (open) => set({ commandOpen: open ?? !get().commandOpen }),

  pushToast: (toast) => {
    toastSeq += 1
    const message: ToastMessage = { ...toast, id: toastSeq }
    set((state) => ({ toasts: [...state.toasts, message].slice(-4) }))
    return message.id
  },

  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }))
}))
