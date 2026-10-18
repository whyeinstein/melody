import { describe, expect, it } from 'vitest'
import { inferFromFilename } from '../../src/main/services/library/filename'

describe('文件名兜底解析', () => {
  it('解析「序号 - 艺术家 - 标题」', () => {
    expect(inferFromFilename('01 - 林深 - 晨雾.mp3')).toEqual({ artist: '林深', title: '晨雾', trackNo: 1 })
  })

  it('解析「艺术家 - 标题」', () => {
    expect(inferFromFilename('Nova Sound - Orbit.flac')).toEqual({ artist: 'Nova Sound', title: 'Orbit' })
  })

  it('解析「序号. 标题」', () => {
    expect(inferFromFilename('07. Longitude.wav')).toEqual({ title: 'Longitude', trackNo: 7 })
  })

  it('去掉尾部括号备注（伴奏/版本）', () => {
    expect(inferFromFilename('夜航 - 灯塔 (伴奏).ogg')).toEqual({ artist: '夜航', title: '灯塔' })
  })

  it('没有分隔符时整体作为标题', () => {
    expect(inferFromFilename('纯音乐.mp3')).toEqual({ title: '纯音乐' })
  })

  it('标题里包含连字符时保留后半段', () => {
    expect(inferFromFilename('A - B - C.mp3')).toEqual({ artist: 'A', title: 'B - C' })
  })
})
