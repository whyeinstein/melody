"""WebDAV 本地代理测试：Range 透传与错误状态。"""

from __future__ import annotations

import os
import sys
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_webdav import FakeWebDavServer  # noqa: E402
from melody_app.core.sources.webdav_client import WebDavClient, WebDavConfig  # noqa: E402
from melody_app.core.sources.webdav_proxy import WebDavProxy  # noqa: E402

PAYLOAD = bytes(range(256)) * 8  # 2048 字节


class WebDavProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = FakeWebDavServer().__enter__()
        cls.server.add_file("song.mp3", PAYLOAD)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.__exit__(None, None, None)

    def setUp(self) -> None:
        self.client = WebDavClient(WebDavConfig(base_url=self.server.base_url))
        self.proxy = WebDavProxy(self.client)
        self.proxy.start()
        self.url = self.proxy.url_for("song.mp3")

    def tearDown(self) -> None:
        self.proxy.stop()

    def test_url_is_loopback_with_token(self) -> None:
        self.assertTrue(self.url.startswith("http://127.0.0.1:"), self.url)
        self.assertIn("/media/", self.url)
        self.assertTrue(self.url.endswith("song.mp3"))

    def test_range_request(self) -> None:
        request = urllib.request.Request(self.url, headers={"Range": "bytes=10-19"})
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 206)
            body = response.read()
            self.assertEqual(len(body), 10)
            self.assertEqual(body, PAYLOAD[10:20])
            self.assertIn("bytes 10-19/2048", response.headers.get("Content-Range", ""))

    def test_full_get(self) -> None:
        with urllib.request.urlopen(self.url, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), PAYLOAD)

    def test_head(self) -> None:
        request = urllib.request.Request(self.url, method="HEAD")
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(int(response.headers["Content-Length"]), len(PAYLOAD))

    def test_missing_file_returns_404(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(self.proxy.url_for("missing.mp3"), timeout=10)
        self.assertEqual(context.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
