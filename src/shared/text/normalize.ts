/**
 * 搜索与排序用的归一化：去重音、统一小写、压缩空白。
 * 中文不做分词，直接用子串匹配（配合 SQLite LIKE）。
 */
export function normalizeText(input: string | null | undefined): string {
  if (!input) return ''
  return input
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

/** 把用户输入转成 `%like%` 模式，转义 SQL LIKE 的通配符。 */
export function toLikePattern(input: string): string {
  const escaped = normalizeText(input).replace(/[\\%_]/g, (char) => `\\${char}`)
  return `%${escaped}%`
}
