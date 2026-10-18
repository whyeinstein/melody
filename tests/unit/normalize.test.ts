import { describe, expect, it } from 'vitest'
import { normalizeText, toLikePattern } from '@shared/text/normalize'

describe('搜索文本归一化', () => {
  it('小写、去重音、压缩空白', () => {
    expect(normalizeText('  Björk   —  Jóga ')).toBe('bjork — joga')
  })

  it('空值返回空串', () => {
    expect(normalizeText(null)).toBe('')
    expect(normalizeText(undefined)).toBe('')
  })

  it('中文保持原样', () => {
    expect(normalizeText('晨雾中的信号')).toBe('晨雾中的信号')
  })

  it('转义 SQL LIKE 通配符', () => {
    expect(toLikePattern('100%_mix')).toBe('%100\\%\\_mix%')
  })
})
