"""本地 HTTP 代理：把需要认证的 WebDAV 音频暴露为 127.0.0.1 的 URL，并透传 Range。

QMediaPlayer / ffmpeg 不能携带自定义认证头，所以扫描元数据与远程播放都走这个代理。
代理只监听回环地址，URL 中带每次启动随机生成的 token。
"""

from __future__ import annotations

import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .webdav_client import WebDavClient, WebDavError

_PASS_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Last-Modified",
    "ETag",
)


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args) -> None:  # 静默
        return

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(head_only=True)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(head_only=False)

    def _serve(self, head_only: bool) -> None:
        proxy: "WebDavProxy" = self.server.proxy  # type: ignore[attr-defined]
        raw_path = urllib.parse.urlsplit(self.path).path
        if not raw_path.startswith(proxy.path_prefix):
            self._send_error(404, "not found")
            return
        remote_path = urllib.parse.unquote(raw_path[len(proxy.path_prefix):])
        try:
            response = proxy.request(
                "HEAD" if head_only else "GET",
                remote_path,
                range_header=self.headers.get("Range"),
            )
        except WebDavError as error:
            self._send_error(502, str(error))
            return
        except OSError as error:
            self._send_error(502, f"代理请求失败：{error}")
            return

        try:
            status = getattr(response, "status", getattr(response, "code", 502))
            self.send_response(status)
            for name in _PASS_HEADERS:
                value = response.headers.get(name)
                if value:
                    self.send_header(name, value)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if head_only:
                return
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            response.close()

    def _send_error(self, status: int, message: str) -> None:
        body = message.encode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


class _ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, proxy: "WebDavProxy") -> None:
        self.proxy = proxy
        super().__init__(address, _ProxyHandler)


class WebDavProxy:
    """一个来源对应一个代理实例；懒启动，进程退出时自动结束。"""

    def __init__(self, client: WebDavClient) -> None:
        self._client = client
        self._token = secrets.token_urlsafe(18)
        self._server: _ProxyServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ 生命周期
    def start(self) -> None:
        if self._server is not None:
            return
        self._server = _ProxyServer(("127.0.0.1", 0), self)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="melody-webdav-proxy",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2)

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server is not None else 0

    @property
    def base_url(self) -> str:
        self.start()
        return f"http://127.0.0.1:{self.port}"

    @property
    def path_prefix(self) -> str:
        return f"/media/{self._token}/"

    # ------------------------------------------------------------------ 地址/请求
    def url_for(self, path: str) -> str:
        self.start()
        clean = path.strip("/")
        return f"{self.base_url}{self.path_prefix}{urllib.parse.quote(clean, safe='/')}"

    def request(self, method: str, remote_path: str, range_header: str | None = None):
        headers = {"User-Agent": "Melody/0.2"}
        if self._client.config.username:
            import base64

            token = base64.b64encode(
                f"{self._client.config.username}:{self._client.config.password}".encode(
                    "utf-8"
                )
            ).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        if range_header:
            headers["Range"] = range_header
        url = self._client.url_for(remote_path)
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            return urllib.request.urlopen(
                request, timeout=60, context=self._client.ssl_context()
            )
        except urllib.error.HTTPError as error:
            return error
        except urllib.error.URLError as error:
            raise WebDavError(f"无法连接远程库：{error.reason}") from error


# ---------------------------------------------------------------------- 注册表
_PROXIES: dict[int, tuple[str, WebDavProxy]] = {}
_LOCK = threading.Lock()


def get_proxy(source_id: int, client: WebDavClient, signature: str) -> WebDavProxy:
    """按来源复用代理；连接参数变化时重建。"""
    with _LOCK:
        existing = _PROXIES.get(source_id)
        if existing is not None and existing[0] == signature:
            return existing[1]
        if existing is not None:
            try:
                existing[1].stop()
            except Exception:  # noqa: BLE001 - 旧代理停止失败不影响新代理
                pass
        proxy = WebDavProxy(client)
        proxy.start()
        _PROXIES[source_id] = (signature, proxy)
        return proxy


def shutdown_all() -> None:
    with _LOCK:
        proxies = list(_PROXIES.values())
        _PROXIES.clear()
    for _signature, proxy in proxies:
        try:
            proxy.stop()
        except Exception:  # noqa: BLE001
            pass
