import type { MelodyBridge } from '../shared/ipc/api'

declare global {
  interface Window {
    melody: MelodyBridge
  }
}

export {}
