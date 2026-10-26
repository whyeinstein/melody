"""头像更换/移除的共用动作（侧边栏与设置页共用）。"""

from __future__ import annotations

import os

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from ..core.profile import AvatarError, remove_avatar, save_avatar
from .app_context import AppContext

IMAGE_FILTER = (
    "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;所有文件 (*)"
)


def choose_avatar(parent, ctx: AppContext) -> bool:
    path, _selected = QFileDialog.getOpenFileName(
        parent,
        "选择头像图片",
        os.path.expanduser("~"),
        IMAGE_FILTER,
    )
    if not path:
        return False
    try:
        save_avatar(path)
    except AvatarError as error:
        QMessageBox.warning(parent, "更换头像", str(error))
        return False
    ctx.avatar_changed.emit()
    ctx.toast("头像已更新")
    return True


def clear_avatar(parent, ctx: AppContext) -> bool:
    try:
        removed = remove_avatar()
    except AvatarError as error:
        QMessageBox.warning(parent, "移除头像", str(error))
        return False
    if not removed:
        return False
    ctx.avatar_changed.emit()
    ctx.toast("已移除头像")
    return True
