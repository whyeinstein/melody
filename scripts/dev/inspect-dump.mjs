/**
 * 极简 minidump 解析：列出崩溃转储里记录的异常码与已加载模块，
 * 用来判断 electron.exe 启动崩溃是否由第三方 DLL 注入/冲突导致。
 *
 * 用法：node scripts/dev/inspect-dump.mjs <path-to-dmp>
 */
import { readFileSync } from 'node:fs'

const file = process.argv[2]
if (!file) {
  console.error('用法: node scripts/dev/inspect-dump.mjs <dump.dmp>')
  process.exit(2)
}

const buffer = readFileSync(file)

const SIGNATURE = 0x504d444d // 'MDMP'
if (buffer.readUInt32LE(0) !== SIGNATURE) {
  console.error('不是 minidump 文件')
  process.exit(2)
}

const numberOfStreams = buffer.readUInt32LE(8)
const directoryRva = buffer.readUInt32LE(12)

const streams = []
for (let i = 0; i < numberOfStreams; i += 1) {
  const offset = directoryRva + i * 12
  streams.push({
    type: buffer.readUInt32LE(offset),
    size: buffer.readUInt32LE(offset + 4),
    rva: buffer.readUInt32LE(offset + 8)
  })
}

function readMinidumpString(rva) {
  const length = buffer.readUInt32LE(rva)
  return buffer.toString('utf16le', rva + 4, rva + 4 + length)
}

// Stream 6 = ExceptionStream
const exceptionStream = streams.find((stream) => stream.type === 6)
if (exceptionStream) {
  const base = exceptionStream.rva
  const exceptionCode = buffer.readUInt32LE(base + 8)
  const exceptionAddress = Number(buffer.readBigUInt64LE(base + 24))
  console.log(`异常码: 0x${exceptionCode.toString(16)}`)
  console.log(`异常地址: 0x${exceptionAddress.toString(16)}`)
}

// Stream 4 = ModuleListStream
const moduleStream = streams.find((stream) => stream.type === 4)
if (!moduleStream) {
  console.error('没有模块列表')
  process.exit(1)
}

const count = buffer.readUInt32LE(moduleStream.rva)
const modules = []
for (let i = 0; i < count; i += 1) {
  const entry = moduleStream.rva + 4 + i * 108
  const base = Number(buffer.readBigUInt64LE(entry))
  const size = buffer.readUInt32LE(entry + 8)
  const nameRva = buffer.readUInt32LE(entry + 20)
  modules.push({ base, size, name: readMinidumpString(nameRva) })
}

console.log(`模块数量: ${modules.length}`)
console.log('--- 非系统目录模块 ---')
const suspicious = modules.filter((module) => {
  const lower = module.name.toLowerCase()
  return !lower.startsWith('c:\\windows\\') && !lower.includes('\\electron\\dist\\')
})
for (const module of suspicious) {
  const offset = module.size > 0 ? '' : ' (size=0)'
  console.log(`  ${module.name}${offset}`)
}

console.log('--- electron 目录下的模块（前 25 个）---')
for (const module of modules.filter((m) => m.name.toLowerCase().includes('\\electron\\dist\\')).slice(0, 25)) {
  console.log(`  ${module.name}`)
}
