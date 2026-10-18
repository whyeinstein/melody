import { describe, expect, it } from 'vitest'
import { parseRangeHeader } from '../../src/main/util/range'

describe('parseRangeHeader', () => {
  describe('没有 Range（200）', () => {
    it('header 为 undefined / null / 空串 / 纯空白时返回 full', () => {
      expect(parseRangeHeader(undefined, 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader(null, 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('   ', 1000)).toEqual({ kind: 'full' })
    })

    it('没有 Range 时文件大小不影响结果', () => {
      expect(parseRangeHeader(undefined, 0)).toEqual({ kind: 'full' })
      expect(parseRangeHeader(undefined, -1)).toEqual({ kind: 'full' })
    })
  })

  describe('单区间（206）', () => {
    it('解析普通闭区间 bytes=start-end', () => {
      expect(parseRangeHeader('bytes=0-99', 1000)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 99 }
      })
      expect(parseRangeHeader('bytes=2-5', 1000)).toEqual({
        kind: 'partial',
        range: { start: 2, end: 5 }
      })
      expect(parseRangeHeader('bytes=0-0', 1)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 0 }
      })
    })

    it('解析开区间 bytes=start-（到文件末尾）', () => {
      expect(parseRangeHeader('bytes=900-', 1000)).toEqual({
        kind: 'partial',
        range: { start: 900, end: 999 }
      })
      expect(parseRangeHeader('bytes=0-', 1000)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 999 }
      })
      expect(parseRangeHeader('bytes=999-', 1000)).toEqual({
        kind: 'partial',
        range: { start: 999, end: 999 }
      })
    })

    it('解析后缀区间 bytes=-suffix（最后 N 字节）', () => {
      expect(parseRangeHeader('bytes=-100', 1000)).toEqual({
        kind: 'partial',
        range: { start: 900, end: 999 }
      })
      expect(parseRangeHeader('bytes=-1', 1000)).toEqual({
        kind: 'partial',
        range: { start: 999, end: 999 }
      })
      // 后缀长度超过文件大小时取整个文件，而不是 416。
      expect(parseRangeHeader('bytes=-5000', 1000)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 999 }
      })
    })

    it('终点超过文件末尾时截断到末尾', () => {
      expect(parseRangeHeader('bytes=500-9999', 1000)).toEqual({
        kind: 'partial',
        range: { start: 500, end: 999 }
      })
    })

    it('容忍大小写、单位周围空白与前导零', () => {
      expect(parseRangeHeader('BYTES=0-9', 100)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 9 }
      })
      expect(parseRangeHeader('bytes = 0 - 9', 100)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 9 }
      })
      expect(parseRangeHeader('bytes=000-009', 100)).toEqual({
        kind: 'partial',
        range: { start: 0, end: 9 }
      })
      expect(parseRangeHeader('  bytes=10-19  ', 100)).toEqual({
        kind: 'partial',
        range: { start: 10, end: 19 }
      })
    })
  })

  describe('无法满足的区间（416）', () => {
    it('起点等于或超过文件大小时返回 unsatisfiable', () => {
      expect(parseRangeHeader('bytes=1000-', 1000)).toEqual({ kind: 'unsatisfiable' })
      expect(parseRangeHeader('bytes=1000-2000', 1000)).toEqual({ kind: 'unsatisfiable' })
      expect(parseRangeHeader('bytes=2000-3000', 1000)).toEqual({ kind: 'unsatisfiable' })
    })

    it('后缀长度为 0 时返回 unsatisfiable', () => {
      expect(parseRangeHeader('bytes=-0', 1000)).toEqual({ kind: 'unsatisfiable' })
    })

    it('空文件上的任何区间都返回 unsatisfiable', () => {
      expect(parseRangeHeader('bytes=0-', 0)).toEqual({ kind: 'unsatisfiable' })
      expect(parseRangeHeader('bytes=0-10', 0)).toEqual({ kind: 'unsatisfiable' })
      expect(parseRangeHeader('bytes=-1', 0)).toEqual({ kind: 'unsatisfiable' })
      // 非法大小按空资源处理。
      expect(parseRangeHeader('bytes=0-', -1)).toEqual({ kind: 'unsatisfiable' })
    })
  })

  describe('多区间：忽略整个 Range（回退 200）', () => {
    it('bytes=0-99,200-299 返回 full 而不是 206', () => {
      expect(parseRangeHeader('bytes=0-99,200-299', 1000)).toEqual({ kind: 'full' })
      // 语法错误的“多段”也按忽略处理。
      expect(parseRangeHeader('bytes=0-99,', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=,0-99', 1000)).toEqual({ kind: 'full' })
    })
  })

  describe('非法输入：忽略 Range（回退 200）', () => {
    it('非 bytes 单位或缺少单位时返回 full', () => {
      expect(parseRangeHeader('items=0-99', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('0-99', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes', 1000)).toEqual({ kind: 'full' })
    })

    it('语法不合法时返回 full', () => {
      expect(parseRangeHeader('bytes=', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=-', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=abc', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=1.5-2', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=1-2-3', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=--5', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=+5-10', 1000)).toEqual({ kind: 'full' })
    })

    it('起点大于终点属于非法区间，返回 full', () => {
      expect(parseRangeHeader('bytes=5-4', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=999-0', 1000)).toEqual({ kind: 'full' })
    })

    it('数字超出安全整数范围时返回 full', () => {
      expect(parseRangeHeader('bytes=999999999999999999999-', 1000)).toEqual({ kind: 'full' })
      expect(parseRangeHeader('bytes=-999999999999999999999', 1000)).toEqual({ kind: 'full' })
    })
  })
})
