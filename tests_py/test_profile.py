"""头像文件处理测试：居中裁剪、尺寸上限、删除与异常。"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from PyQt5.QtGui import QColor, QImage  # noqa: E402

from melody_app.config import avatar_file  # noqa: E402
from melody_app.core.profile import (  # noqa: E402
    MAX_AVATAR_SIZE,
    AvatarError,
    has_avatar,
    load_avatar_image,
    remove_avatar,
    save_avatar,
)


def make_temp_dir(prefix: str = "avatar") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


class AvatarFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self._old_data_dir = os.environ.get("MELODY_DATA_DIR")
        os.environ["MELODY_DATA_DIR"] = os.path.join(self.temp, "data")

    def tearDown(self) -> None:
        if self._old_data_dir is None:
            os.environ.pop("MELODY_DATA_DIR", None)
        else:
            os.environ["MELODY_DATA_DIR"] = self._old_data_dir
        shutil.rmtree(self.temp, ignore_errors=True)

    def _make_image(self, width: int, height: int) -> str:
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(QColor("#7C6CF6"))
        path = os.path.join(self.temp, "source.png")
        self.assertTrue(image.save(path, "PNG"))
        return path

    def test_save_crops_square_and_limits_size(self) -> None:
        source = self._make_image(1200, 800)
        target = save_avatar(source)
        self.assertEqual(target, avatar_file())
        self.assertTrue(os.path.isfile(target))
        self.assertTrue(has_avatar())

        saved = QImage(target)
        self.assertEqual(saved.width(), MAX_AVATAR_SIZE)
        self.assertEqual(saved.height(), MAX_AVATAR_SIZE)

    def test_small_image_is_not_upscaled(self) -> None:
        source = self._make_image(120, 90)
        target = save_avatar(source)
        saved = QImage(target)
        self.assertEqual(saved.width(), 90)
        self.assertEqual(saved.height(), 90)

    def test_load_avatar_image(self) -> None:
        self.assertIsNone(load_avatar_image())
        save_avatar(self._make_image(300, 300))
        loaded = load_avatar_image()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.width(), 300)

    def test_remove_avatar(self) -> None:
        save_avatar(self._make_image(200, 200))
        self.assertTrue(remove_avatar())
        self.assertFalse(has_avatar())
        self.assertFalse(remove_avatar())

    def test_invalid_file_raises(self) -> None:
        bad = os.path.join(self.temp, "bad.txt")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("not an image")
        with self.assertRaises(AvatarError):
            save_avatar(bad)
        with self.assertRaises(AvatarError):
            save_avatar(os.path.join(self.temp, "missing.png"))

    def test_replacing_avatar_overwrites_single_file(self) -> None:
        save_avatar(self._make_image(300, 300))
        first = os.path.getmtime(avatar_file())
        save_avatar(self._make_image(400, 200))
        self.assertTrue(os.path.isfile(avatar_file()))
        self.assertGreaterEqual(os.path.getmtime(avatar_file()), first)


if __name__ == "__main__":
    unittest.main()
