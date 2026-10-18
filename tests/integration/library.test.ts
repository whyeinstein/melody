import { mkdtempSync, rmSync, unlinkSync, utimesSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { openDatabase, type DbHandle } from '../../src/main/services/db/connection'
import { migrate } from '../../src/main/services/db/migrations'
import {
  addFolder,
  listEnabledFolderPaths,
  listFolders,
  removeFolder
} from '../../src/main/services/db/repositories/folders'
import { listAlbums, listArtists, listGenres } from '../../src/main/services/db/repositories/aggregates'
import { getTrack, queryTracks, setFavorite } from '../../src/main/services/db/repositories/tracks'
import { LibraryScanner } from '../../src/main/services/library/scanner'
import { hasFfmpeg, writeFixtureTrack } from '../helpers/fixtures'

const describeIfFfmpeg = hasFfmpeg() ? describe : describe.skip

describeIfFfmpeg('音乐库：扫描 / 查询 / 增量', () => {
  let root: string
  let libraryDir: string
  let coversDir: string
  let db: DbHandle
  let scanner: LibraryScanner
  let folderId: number

  beforeAll(async () => {
    root = mkdtempSync(join(tmpdir(), 'melody-it-'))
    libraryDir = join(root, 'library')
    coversDir = join(root, 'covers')

    db = await openDatabase(join(root, 'library.db'))
    migrate(db)

    const folder = addFolder(db, libraryDir, Date.now())
    folderId = folder.id

    writeFixtureTrack(libraryDir, { format: 'mp3', title: '晨雾', artist: '林深', album: '雾气中的信号', trackNo: 1, genre: 'Ambient' })
    writeFixtureTrack(libraryDir, { format: 'flac', title: 'Orbit', artist: 'Nova Sound', album: 'Orbital Drift', trackNo: 2, genre: 'Electronic' })
    writeFixtureTrack(libraryDir, { format: 'ogg', title: '夜航船', artist: '夜航', album: '夜航船', trackNo: 3, genre: 'Folk' })
    writeFixtureTrack(libraryDir, { format: 'wav', title: 'Longitude', artist: 'The Meridian', album: 'Longitudes', trackNo: 4, genre: 'Rock' })
    writeFixtureTrack(join(libraryDir, 'nested'), { format: 'mp3', title: '深层曲目', artist: '林深', album: '雾气中的信号', trackNo: 5, genre: 'Ambient' })

    scanner = new LibraryScanner({ db, coversDir, concurrency: 2 })
  }, 60_000)

  afterAll(() => {
    db?.close()
    rmSync(root, { recursive: true, force: true })
  })

  it('首次扫描把标签、时长与文件夹统计写入数据库', async () => {
    const progress = await scanner.scan()
    expect(progress.state).toBe('done')
    expect(progress.added).toBe(5)
    expect(progress.failed).toBe(0)

    const folders = listFolders(db)
    expect(folders).toHaveLength(1)
    expect(folders[0]?.trackCount).toBe(5)

    const page = queryTracks(db, { sort: 'title' })
    expect(page.total).toBe(5)

    const first = page.items.find((track) => track.title === '晨雾')
    expect(first).toBeDefined()
    expect(first?.artist).toBe('林深')
    expect(first?.album).toBe('雾气中的信号')
    expect(first?.durationMs).toBeGreaterThan(500)
    expect(first?.format).toBe('mp3')
  })

  it('再次扫描不重复解析未变化文件', async () => {
    const progress = await scanner.scan()
    expect(progress.state).toBe('done')
    expect(progress.added).toBe(0)
    expect(progress.updated).toBe(0)
    expect(queryTracks(db, {}).total).toBe(5)
  })

  it('文件修改后增量更新，删除后标记缺失', async () => {
    const target = queryTracks(db, { search: '深层曲目' }).items[0]
    expect(target).toBeDefined()
    if (!target) return

    const future = new Date(Date.now() + 5000)
    utimesSync(target.path, future, future)

    const touched = await scanner.scan()
    expect(touched.updated).toBeGreaterThanOrEqual(1)

    unlinkSync(target.path)
    const removed = await scanner.scan()
    expect(removed.removed).toBeGreaterThanOrEqual(1)
    expect(queryTracks(db, {}).total).toBe(4)

    const stillThere = getTrack(db, target.id)
    expect(stillThere?.missing).toBe(true)
  })

  it('搜索、收藏与聚合视图', async () => {
    const search = queryTracks(db, { search: '晨雾' })
    expect(search.total).toBe(1)

    const favoriteTarget = search.items[0]
    expect(favoriteTarget).toBeDefined()
    if (!favoriteTarget) return

    setFavorite(db, favoriteTarget.id, true)
    expect(queryTracks(db, { favorite: true }).total).toBe(1)
    expect(getTrack(db, favoriteTarget.id)?.favorite).toBe(true)

    expect(listAlbums(db).length).toBeGreaterThanOrEqual(3)
    expect(listArtists(db).length).toBeGreaterThanOrEqual(3)
    expect(listGenres(db).some((genre) => genre.name === 'Ambient')).toBe(true)
  })

  it('按文件夹过滤、分页与排序生效', async () => {
    const byFolder = queryTracks(db, { folderId })
    expect(byFolder.total).toBe(4)

    const page = queryTracks(db, { limit: 2, offset: 0, sort: 'title', direction: 'asc' })
    expect(page.items).toHaveLength(2)
    const second = queryTracks(db, { limit: 2, offset: 2, sort: 'title', direction: 'asc' })
    expect(second.items[0]?.id).not.toBe(page.items[0]?.id)
  })

  it('移除文件夹会级联删除曲目', () => {
    removeFolder(db, folderId)
    expect(listFolders(db)).toHaveLength(0)
    expect(listEnabledFolderPaths(db)).toHaveLength(0)
    expect(queryTracks(db, {}).total).toBe(0)
  })
})
