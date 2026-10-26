"""本地头像：统一保存为数据目录下的 ``avatar.png``（居中裁剪、最大 512px）。

不做用户管理，头像只是本机的一份图片，随数据目录一起迁移/备份。
"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage

from ..config import avatar_file

MAX_AVATAR_SIZE = 512


class AvatarError(ValueError):
    """头像图片无法读取或保存。"""


def has_avatar() -> bool:
    return os.path.isfile(avatar_file())


def save_avatar(source: str) -> str:
    """读取用户选择的图片，居中裁剪成方形并保存为标准 PNG。"""
    if not source or not os.path.isfile(source):
        raise AvatarError("找不到该图片文件")
    image = QImage(source)
    if image.isNull():
        raise AvatarError("无法读取该图片（格式不支持或文件损坏）")

    side = min(image.width(), image.height())
    if side <= 0:
        raise AvatarError("图片尺寸无效")
    left = max(0, (image.width() - side) // 2)
    top = max(0, (image.height() - side) // 2)
    cropped = image.copy(left, top, side, side)
    if side > MAX_AVATAR_SIZE:
        cropped = cropped.scaled(
            MAX_AVATAR_SIZE,
            MAX_AVATAR_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    target = avatar_file()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if not cropped.save(target, "PNG"):
        raise AvatarError("保存头像失败，请检查数据目录权限")
    return target


def remove_avatar() -> bool:
    """删除头像文件；本身不存在时返回 False。"""
    try:
        os.remove(avatar_file())
        return True
    except FileNotFoundError:
        return False
    except OSError as error:
        raise AvatarError(f"删除头像失败：{error}") from error


def load_avatar_image() -> QImage | None:
    path = avatar_file()
    if not os.path.isfile(path):
        return None
    image = QImage(path)
    return None if image.isNull() else image
