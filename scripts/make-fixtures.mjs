#!/usr/bin/env node
/**
 * 生成测试音乐库：用系统 ffmpeg 合成多格式、带标签与封面的音频文件。
 *
 *   node scripts/make-fixtures.mjs --count=60 --out=tests/fixtures/library
 *
 * 输出目录默认被 .gitignore 忽略，可随时重建。
 */
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function parseArgs(argv) {
  const options = { count: 60, out: 'tests/fixtures/library', clean: true }
  for (const arg of argv) {
    if (arg.startsWith('--count=')) options.count = Math.max(1, Number.parseInt(arg.slice(8), 10) || 60)
    else if (arg.startsWith('--out=')) options.out = arg.slice(6)
    else if (arg === '--keep') options.clean = false
  }
  return options
}

const options = parseArgs(process.argv.slice(2))
const outputRoot = resolve(projectRoot, options.out)

const ffmpeg = findFfmpeg()
if (!ffmpeg) {
  console.error('未找到 ffmpeg，请先安装或将其加入 PATH')
  process.exit(1)
}

if (options.clean && existsSync(outputRoot)) rmSync(outputRoot, { recursive: true, force: true })
mkdirSync(outputRoot, { recursive: true })

const artists = [
  { name: '林深', album: '雾气中的信号' },
  { name: 'Nova Sound', album: 'Orbital Drift' },
  { name: '夜航', album: '夜航船' },
  { name: 'The Meridian', album: 'Longitudes' },
  { name: 'Ария', album: 'Северный свет' }
]
const genres = ['Ambient', 'Electronic', 'Folk', 'Rock', 'Classical']
const formats = ['mp3', 'flac', 'ogg', 'm4a', 'wav']
const tracksPerAlbum = 12

function pad(value) {
  return String(value).padStart(2, '0')
}

function findFfmpeg() {
  const fromPath = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' })
  return fromPath.status === 0 ? 'ffmpeg' : null
}

function run(args) {
  const result = spawnSync(ffmpeg, args, { stdio: 'ignore' })
  if (result.status !== 0) throw new Error(`ffmpeg 失败: ${args.join(' ')}`)
}

const COVER_COLORS = ['0x2b2d42', '0x5a3df0', '0x0f766e', '0x9a3412', '0x1d4ed8']

function ensureCover(directory, albumIndex) {
  const coverPath = join(directory, 'cover.png')
  if (existsSync(coverPath)) return coverPath
  const color = COVER_COLORS[albumIndex % COVER_COLORS.length]
  run(['-y', '-f', 'lavfi', '-i', `color=c=${color}:s=300x300`, '-frames:v', '1', coverPath])
  return coverPath
}

let created = 0
for (let index = 0; index < options.count; index += 1) {
  const artist = artists[index % artists.length]
  const format = formats[index % formats.length]
  const albumIndex = Math.floor(index / tracksPerAlbum)
  const trackNo = (index % tracksPerAlbum) + 1
  const title = `${artist.album} ${pad(trackNo)}`
  const duration = 2 + (index % 3)

  const albumDirectory = join(outputRoot, artist.name, `${artist.album}`)
  mkdirSync(albumDirectory, { recursive: true })

  const fileName = `${pad(trackNo)} - ${artist.name} - ${title}.${format}`
  const target = join(albumDirectory, fileName)

  const input = ['-y', '-f', 'lavfi', '-i', `sine=frequency=${220 + ((index * 37) % 500)}:duration=${duration}`]

  const metadata = [
    '-metadata',
    `title=${title}`,
    '-metadata',
    `artist=${artist.name}`,
    '-metadata',
    `album=${artist.album}`,
    '-metadata',
    `album_artist=${artist.name}`,
    '-metadata',
    `track=${trackNo}`,
    '-metadata',
    `date=${2015 + (albumIndex % 10)}`,
    '-metadata',
    `genre=${genres[albumIndex % genres.length]}`
  ]

  if (format === 'mp3') {
    const cover = ensureCover(albumDirectory, albumIndex)
    run([
      ...input,
      '-i',
      cover,
      '-map',
      '0:a',
      '-map',
      '1:v',
      '-c:a',
      'libmp3lame',
      '-q:a',
      '6',
      '-c:v',
      'mjpeg',
      '-disposition:v',
      'attached_pic',
      '-id3v2_version',
      '3',
      ...metadata,
      target
    ])
  } else if (format === 'flac') {
    run([...input, '-c:a', 'flac', '-compression_level', '5', ...metadata, target])
  } else if (format === 'ogg') {
    run([...input, '-c:a', 'libvorbis', '-q:a', '4', ...metadata, target])
  } else if (format === 'm4a') {
    run([...input, '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', ...metadata, target])
  } else {
    run([...input, '-c:a', 'pcm_s16le', ...metadata, target])
  }

  created += 1
}

// 一个损坏文件，用于验证扫描器的错误统计不会中断整次扫描
const brokenDirectory = join(outputRoot, 'broken')
mkdirSync(brokenDirectory, { recursive: true })
writeFileSync(join(brokenDirectory, 'corrupt.mp3'), Buffer.from('not really an mp3 file'))
writeFileSync(join(brokenDirectory, 'notes.txt'), '这不是音频文件，扫描器应忽略')

console.log(`已生成 ${created} 首测试曲目（含 1 个损坏文件）于 ${outputRoot}`)
