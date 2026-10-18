const PREFIX = '[melody]'

export function logInfo(...args: unknown[]): void {
  console.log(PREFIX, ...args)
}

export function logWarn(...args: unknown[]): void {
  console.warn(PREFIX, ...args)
}

export function logError(...args: unknown[]): void {
  console.error(PREFIX, ...args)
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}
