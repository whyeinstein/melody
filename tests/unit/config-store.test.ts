import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { ConfigStore } from '../../src/main/services/config/store'

const temporaryDirectories: string[] = []

function createDirectory(): string {
  const directory = mkdtempSync(join(tmpdir(), 'melody-config-'))
  temporaryDirectories.push(directory)
  return directory
}

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true })
  }
})

describe('配置存储', () => {
  it('首次加载写入默认配置', () => {
    const file = join(createDirectory(), 'config.json')
    const store = ConfigStore.load(file)
    expect(store.get().theme).toBe('dark')
    expect(store.get().volume).toBe(0.8)
    expect(JSON.parse(readFileSync(file, 'utf8')).version).toBe(1)
  })

  it('更新后持久化，并在重新加载时保留', () => {
    const file = join(createDirectory(), 'config.json')
    ConfigStore.load(file).update({ volume: 0.35, repeat: 'all', shuffle: true })
    const reloaded = ConfigStore.load(file)
    expect(reloaded.get().volume).toBe(0.35)
    expect(reloaded.get().repeat).toBe('all')
    expect(reloaded.get().shuffle).toBe(true)
  })

  it('损坏的 JSON 回退默认值', () => {
    const file = join(createDirectory(), 'config.json')
    writeFileSync(file, '{ not json', 'utf8')
    expect(ConfigStore.load(file).get().theme).toBe('dark')
  })

  it('非法字段回退默认值', () => {
    const file = join(createDirectory(), 'config.json')
    writeFileSync(file, JSON.stringify({ version: 1, volume: 42 }), 'utf8')
    expect(ConfigStore.load(file).get().volume).toBe(0.8)
  })
})
