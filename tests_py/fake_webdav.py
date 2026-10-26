"""测试用假 WebDAV 服务：PROPFIND 目录树 + 支持 Range 的 GET/HEAD。

只用于 tests_py，不进入应用。
"""

from __future__ import annotations

import email.utils
import mimetypes
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/dav/music"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args) -> None:
        return

    @property
    def fake(self) -> "FakeWebDavServer":
        return self.server.fake  # type: ignore[attr-defined]

    def _authorized(self) -> bool:
        if not self.fake.username:
            return True
        import base64

        expected = "Basic " + base64.b64encode(
            f"{self.fake.username}:{self.fake.password}".encode()
        ).decode()
        return self.headers.get("Authorization") == expected

    def _send(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    # ------------------------------------------------------------------ PROPFIND
    def do_PROPFIND(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send(401, b"", {"WWW-Authenticate": 'Basic realm="melody-test"'})
            return
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith(ROOT):
            self._send(404, b"")
            return
        relative = urllib.parse.unquote(path[len(ROOT):]).strip("/")
        depth = self.headers.get("Depth", "0")
        entries: list[tuple[str, bool, int, int]] = [(relative, True, 0, 0)]
        if depth != "0":
            for name in self.fake.children(relative):
                full = f"{relative}/{name}" if relative else name
                if full in self.fake.files:
                    data, mtime = self.fake.files[full]
                    entries.append((full, False, len(data), mtime))
                else:
                    entries.append((full, True, 0, 0))
        body = self.fake.multistatus(entries)
        self._send(207, body, {"Content-Type": "application/xml; charset=utf-8"})

    # ------------------------------------------------------------------ GET/HEAD
    def do_HEAD(self) -> None:  # noqa: N802
        self._serve_file(head_only=True)

    def do_GET(self) -> None:  # noqa: N802
        self._serve_file(head_only=False)

    def _serve_file(self, head_only: bool) -> None:
        if not self._authorized():
            self._send(401, b"", {"WWW-Authenticate": 'Basic realm="melody-test"'})
            return
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith(ROOT):
            self._send(404, b"")
            return
        relative = urllib.parse.unquote(path[len(ROOT):]).strip("/")
        if relative not in self.fake.files:
            self._send(404, b"")
            return
        data, mtime = self.fake.files[relative]
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        start, end = 0, len(data) - 1
        status = 200
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            spec = range_header[len("bytes="):]
            left, _, right = spec.partition("-")
            try:
                if left:
                    start = int(left)
                    end = int(right) if right else len(data) - 1
                else:
                    start = max(0, len(data) - int(right))
            except ValueError:
                start, end = 0, len(data) - 1
            if start >= len(data):
                self._send(416, b"")
                return
            end = min(end, len(data) - 1)
            status = 206
        chunk = data[start:end + 1]
        headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Last-Modified": email.utils.formatdate(mtime, usegmt=True),
        }
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{len(data)}"
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        if not head_only:
            self.wfile.write(chunk)


class FakeWebDavServer:
    def __init__(self, username: str = "", password: str = "") -> None:
        self.files: dict[str, tuple[bytes, int]] = {}
        self.username = username
        self.password = password
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.fake = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="fake-webdav", daemon=True
        )

    # ------------------------------------------------------------------ 生命周期
    def __enter__(self) -> "FakeWebDavServer":
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}{ROOT}"

    # ------------------------------------------------------------------ 内容
    def add_file(self, path: str, data: bytes, mtime: int = 1700000000) -> None:
        self.files[path.lstrip("/")] = (bytes(data), int(mtime))

    def remove_file(self, path: str) -> None:
        self.files.pop(path.lstrip("/"), None)

    def children(self, directory: str) -> list[str]:
        prefix = f"{directory}/" if directory else ""
        names: set[str] = set()
        for path in self.files:
            if not path.startswith(prefix):
                continue
            remainder = path[len(prefix):]
            if not remainder:
                continue
            names.add(remainder.split("/")[0])
        return sorted(names)

    def multistatus(self, entries: list[tuple[str, bool, int, int]]) -> bytes:
        parts = ['<?xml version="1.0" encoding="utf-8"?>', '<d:multistatus xmlns:d="DAV:">']
        for path, is_dir, size, mtime in entries:
            href = ROOT + ("/" + path if path else "/")
            if is_dir and not href.endswith("/"):
                href += "/"
            parts.append("<d:response>")
            parts.append(f"<d:href>{urllib.parse.quote(href)}</d:href>")
            parts.append("<d:propstat><d:prop>")
            if is_dir:
                parts.append("<d:resourcetype><d:collection/></d:resourcetype>")
            else:
                parts.append("<d:resourcetype/>")
                parts.append(f"<d:getcontentlength>{size}</d:getcontentlength>")
                parts.append(
                    f"<d:getlastmodified>{email.utils.formatdate(mtime, usegmt=True)}"
                    "</d:getlastmodified>"
                )
            parts.append("</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>")
            parts.append("</d:response>")
        parts.append("</d:multistatus>")
        return "".join(parts).encode("utf-8")
