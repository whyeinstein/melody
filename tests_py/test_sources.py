"""音乐来源接口测试：注册表、适配器分发与 WebDAV 占位行为。"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from melody_app.core.db import Database  # noqa: E402
from melody_app.core.models import Source  # noqa: E402
from melody_app.core.repositories import SongsRepo, SourcesRepo  # noqa: E402
from melody_app.core.sources import (  # noqa: E402
    SOURCE_REGISTRY,
    LocalFolderSource,
    RemoteSource,
    WebDavSource,
    create_source_adapter,
)


def make_temp_dir(prefix: str = "source") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


class SourceInterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.db = Database(os.path.join(self.temp, "test.db"))
        self.songs = SongsRepo(self.db)
        self.sources = SourcesRepo(self.db)

    def tearDown(self) -> None:
        self.db.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_registry_contains_local_and_webdav(self) -> None:
        self.assertIs(SOURCE_REGISTRY["local"], LocalFolderSource)
        self.assertIs(SOURCE_REGISTRY["webdav"], WebDavSource)
        self.assertIs(SOURCE_REGISTRY["remote"], RemoteSource)

    def test_local_adapter(self) -> None:
        folder = make_temp_dir("music")
        source = self.sources.add_local(folder)
        adapter = create_source_adapter(source, self.songs)
        self.assertIsInstance(adapter, LocalFolderSource)
        self.assertTrue(adapter.available())
        self.assertEqual(adapter.track_count(), 0)
        self.assertEqual(adapter.stream_url("a.mp3"), "a.mp3")
        shutil.rmtree(folder, ignore_errors=True)

    def test_webdav_source_is_registered_placeholder(self) -> None:
        source = self.sources.add_remote(
            "家里的 NAS",
            "https://nas.example.com/dav/music",
            config={"username": "melody", "verify_tls": True},
        )
        self.assertEqual(source.kind, "webdav")
        self.assertEqual(source.kind_text, "WebDAV")
        self.assertEqual(source.config.get("protocol"), "webdav")
        self.assertEqual(source.config.get("username"), "melody")
        # 密码不应出现在数据库 config 里
        self.assertNotIn("password", source.config)

        adapter = create_source_adapter(source, self.songs)
        self.assertIsInstance(adapter, WebDavSource)
        self.assertFalse(adapter.available())
        self.assertEqual(adapter.track_count(), 0)

        ok, message = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("尚未实现", message)
        self.assertIn("nas.example.com", adapter.describe())

    def test_webdav_interface_methods_are_explicitly_unimplemented(self) -> None:
        source = self.sources.add_remote("NAS", "https://nas.example.com/dav")
        adapter = create_source_adapter(source, self.songs)
        self.assertIsInstance(adapter, WebDavSource)

        with self.assertRaises(NotImplementedError):
            adapter.connect()
        with self.assertRaises(NotImplementedError):
            adapter.list_entries()
        with self.assertRaises(NotImplementedError):
            adapter.probe("a.flac")
        with self.assertRaises(NotImplementedError):
            adapter.fetch_cover("a.flac", os.path.join(self.temp, "cover.jpg"))
        with self.assertRaises(NotImplementedError):
            adapter.scan()
        with self.assertRaises(NotImplementedError):
            adapter.stream_url("a.flac")

    def test_webdav_without_url_reports_missing_address(self) -> None:
        source = self.sources.add_remote("未配置", "")
        adapter = create_source_adapter(source, self.songs)
        ok, message = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("未填写", message)

    def test_unknown_kind_falls_back_to_remote_placeholder(self) -> None:
        row = Source(id=99, kind="smb", name="SMB", path="//nas/music")
        adapter = create_source_adapter(row, self.songs)
        self.assertIsInstance(adapter, RemoteSource)
        self.assertFalse(adapter.available())

    def test_remote_source_rows_are_listed_and_toggleable(self) -> None:
        source = self.sources.add_remote("NAS", "https://nas.example.com/dav")
        rows = self.sources.list()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, "webdav")

        self.sources.set_enabled(source.id, False)
        self.assertEqual(self.sources.list(include_disabled=False), [])
        self.assertEqual(len(self.sources.list()), 1)

        self.sources.remove(source.id)
        self.assertEqual(self.sources.list(), [])


if __name__ == "__main__":
    unittest.main()
