#!/usr/bin/env node
/**
 * 通过 GitHub REST API 创建 Release 并上传资产（不依赖 gh CLI / curl）。
 *
 * 用法：
 *   $env:GH_TOKEN = '<token>'
 *   node scripts/dev/gh-release.mjs --tag v0.2.0 --name "Melody v0.2.0" --notes docs/release-v0.2.0.md --asset "release/SHA256.txt"
 */
import { readFileSync, statSync } from 'node:fs'
import { basename, resolve } from 'node:path'

const OWNER = 'whyeinstein'
const REPO = 'melody'

function parseArgs(argv) {
  const options = { tag: null, name: null, notes: null, assets: [], draft: false }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--tag') options.tag = argv[++i]
    else if (arg === '--name') options.name = argv[++i]
    else if (arg === '--notes') options.notes = argv[++i]
    else if (arg === '--asset') options.assets.push(argv[++i])
    else if (arg === '--draft') options.draft = true
  }
  if (!options.tag || !options.name) throw new Error('缺少 --tag 或 --name')
  return options
}

const token = process.env.GH_TOKEN
if (!token) {
  console.error('缺少 GH_TOKEN 环境变量')
  process.exit(2)
}

const API = 'https://api.github.com'
const HEADERS = {
  authorization: `Bearer ${token}`,
  accept: 'application/vnd.github+json',
  'user-agent': 'melody-release-script',
  'x-github-api-version': '2022-11-28'
}

async function apiJson(url, init = {}) {
  const response = await fetch(url, { ...init, headers: { ...HEADERS, ...(init.headers ?? {}) } })
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  return { status: response.status, data }
}

async function findRelease(tag) {
  const { data } = await apiJson(`${API}/repos/${OWNER}/${REPO}/releases/tags/${encodeURIComponent(tag)}`)
  return data && data.id ? data : null
}

async function ensureRelease(options) {
  const existing = await findRelease(options.tag)
  if (existing) {
    console.log(`Release 已存在：${existing.html_url}`)
    return existing
  }
  const notes = options.notes ? readFileSync(resolve(options.notes), 'utf8') : ''
  const result = await apiJson(`${API}/repos/${OWNER}/${REPO}/releases`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      tag_name: options.tag,
      name: options.name,
      body: notes,
      draft: options.draft,
      prerelease: false
    })
  })
  if (result.status >= 300) {
    throw new Error(`创建 Release 失败：${result.status} ${JSON.stringify(result.data)}`)
  }
  console.log(`Release 已创建：${result.data.html_url}`)
  return result.data
}

async function existingAssetNames(releaseId) {
  const { data } = await apiJson(`${API}/repos/${OWNER}/${REPO}/releases/${releaseId}/assets?per_page=100`)
  return new Set((Array.isArray(data) ? data : []).map((asset) => asset.name))
}

async function uploadAsset(releaseId, filePath, alreadyThere) {
  const name = basename(filePath)
  if (alreadyThere.has(name)) {
    console.log(`跳过已存在的资产：${name}`)
    return
  }
  const size = statSync(filePath).size
  console.log(`上传 ${name}（${(size / 1024 / 1024).toFixed(1)} MB）…`)
  // 用 Buffer 一次性读取：实现简单，避免流式上传在受限网络下的 TLS 抖动。
  const body = readFileSync(filePath)
  const endpoint = `https://uploads.github.com/repos/${OWNER}/${REPO}/releases/${releaseId}/assets?name=${encodeURIComponent(name)}`

  let response = null
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          ...HEADERS,
          'content-type': 'application/octet-stream',
          'content-length': String(size)
        },
        body
      })
      break
    } catch (error) {
      console.log(`  第 ${attempt} 次上传失败：${error.cause?.message ?? error.message}`)
      if (attempt === 3) throw error
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 2000))
    }
  }

  const text = await response.text()
  if (response.status >= 300) {
    throw new Error(`上传 ${name} 失败：${response.status} ${text.slice(0, 300)}`)
  }
  const asset = JSON.parse(text)
  console.log(`完成 ${asset.name} → ${asset.browser_download_url}`)
}

const options = parseArgs(process.argv.slice(2))
const release = await ensureRelease(options)
const uploaded = await existingAssetNames(release.id)
for (const asset of options.assets) {
  await uploadAsset(release.id, asset, uploaded)
}
console.log(`发布完成：${release.html_url}`)
