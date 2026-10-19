"""WebDAV 客户端与来源连接测试（本地假 WebDAV 服务，不依赖外网）。"""

from __future__ import annotations

import base64
import os
import shutil
import sys
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from melody_app.core.credentials import CredentialStore  # noqa: E402
from melody_app.core.db import Database  # noqa: E402
from melody_app.core.repositories import SongsRepo, SourcesRepo  # noqa: E402
from melody_app.core.sources import create_source_adapter  # noqa: E402
from melody_app.core.sources.webdav_client import (  # noqa: E402
    WebDavClient,
    WebDavConfig,
    WebDavError,
    parse_multistatus,
)

USERNAME = "melody"
PASSWORD = "secret"

ROOT_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/dav/music/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop>
      <d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
</d:multistatus>"""

LIST_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/dav/music/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat>
  </d:response>
  <d:response>
    <d:href>/dav/music/A%20Song.flac</d:href>
    <d:propstat><d:prop><d:resourcetype/>
      <d:getcontentlength>1234</d:getcontentlength>
      <d:getlastmodified>Tue, 01 Jan 2024 00:00:00 GMT</d:getlastmodified>
    </d:prop></d:propstat>
  </d:response>
  <d:response>
    <d:href>/dav/music/sub/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat>
  </d:response>
</d:multistatus>"""


class FakeWebDavHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def _authorized(self) -> bool:
        expected = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
        return self.headers.get("Authorization") == expected

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PROPFIND(self) -> None:  # noqa: N802
        if not self._authorized():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="melody-test"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.headers.get("Depth") == "0":
            self._send(207, ROOT_XML)
        else:
            self._send(207, LIST_XML)

    def log_message(self, *_args) -> None:  # 静默
        return


class FakeWebDavServer:
    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), FakeWebDavHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "FakeWebDavServer":
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/dav/music"


def make_temp_dir(prefix: str = "webdav") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


class WebDavClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = FakeWebDavServer().__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.__exit__(None, None, None)

    def _config(self, **overrides) -> WebDavConfig:
        data = {
            "base_url": self.server.base_url,
            "username": USERNAME,
            "password": PASSWORD,
            "verify_tls": True,
            "timeout": 5,
        }
        data.update(overrides)
        return WebDavConfig(**data)

    def test_connection_ok(self) -> None:
        ok, message = WebDavClient(self._config()).test_connection()
        self.assertTrue(ok, message)
        self.assertEqual(message, "连接成功")

    def test_connection_bad_password(self) -> None:
        ok, message = WebDavClient(self._config(password="wrong")).test_connection()
        self.assertFalse(ok)
        self.assertIn("401", message)

    def test_connection_refused(self) -> None:
        ok, message = WebDavClient(
            WebDavConfig(base_url="http://127.0.0.1:1/dav", timeout=2)
        ).test_connection()
        self.assertFalse(ok)
        self.assertTrue("无法连接" in message or "连接失败" in message, message)

    def test_connection_rejects_bad_scheme(self) -> None:
        ok, message = WebDavClient(WebDavConfig(base_url="ftp://example.com")).test_connection()
        self.assertFalse(ok)
        self.assertIn("http", message)

    def test_list_dir_parses_entries(self) -> None:
        entries = WebDavClient(self._config()).list_dir()
        by_path = {entry.path: entry for entry in entries}
        self.assertIn("", by_path)
        self.assertTrue(by_path[""].is_dir)

        song = by_path["A Song.flac"]
        self.assertEqual(song.size, 1234)
        self.assertTrue(song.is_audio)
        self.assertFalse(song.is_dir)

        self.assertTrue(by_path["sub"].is_dir)
        self.assertFalse(by_path["sub"].is_audio)

    def test_parse_multistatus_handles_broken_xml(self) -> None:
        with self.assertRaises(WebDavError):
            parse_multistatus(b"<not-xml", "http://example.com")


class WebDavSourceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = FakeWebDavServer().__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.__exit__(None, None, None)

    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.db = Database(os.path.join(self.temp, "test.db"))
        self.songs = SongsRepo(self.db)
        self.sources = SourcesRepo(self.db)
        self.credentials = CredentialStore(os.path.join(self.temp, "credentials"))

    def tearDown(self) -> None:
        self.db.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def _source(self):
        source = self.sources.add_remote(
            "测试 NAS",
            self.server.base_url,
            config={"username": USERNAME, "verify_tls": True},
        )
        self.credentials.save(source.id, PASSWORD)
        return source

    def test_source_connection_with_saved_password(self) -> None:
        source = self._source()
        adapter = create_source_adapter(source, self.songs, self.credentials)
        self.assertFalse(adapter.available())
        ok, message = adapter.test_connection()
        self.assertTrue(ok, message)
        self.assertTrue(adapter.available())
        self.assertEqual(adapter.last_message, "连接成功")
        self.assertIn("WebDAV", adapter.describe())

    def test_source_connection_with_wrong_password(self) -> None:
        source = self._source()
        self.credentials.save(source.id, "wrong")
        adapter = create_source_adapter(source, self.songs, self.credentials)
        ok, message = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("401", message)
        self.assertFalse(adapter.available())


if __name__ == "__main__":
    unittest.main()
