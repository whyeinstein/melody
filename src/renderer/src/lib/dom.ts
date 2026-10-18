/** 与 DOM 相关的小工具（只在渲染进程调用）。 */

/** 搜索框的固定 id，供快捷键与「聚焦搜索」命令使用。 */
export const SEARCH_INPUT_ID = 'library-search-input'

export function focusSearch(): void {
  const element = document.getElementById(SEARCH_INPUT_ID)
  if (element instanceof HTMLInputElement) {
    element.focus()
    element.select()
  }
}

/** 判断键盘事件是否发生在可编辑元素中（此时不应触发全局快捷键）。 */
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

/**
 * 判断目标是否是可交互控件（按钮/链接/角色按钮）。
 * 空格键在这些元素上应激活控件本身，而不是触发全局播放/暂停。
 */
export function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  const tag = target.tagName
  if (tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') {
    return true
  }
  return target.getAttribute('role') === 'button'
}
