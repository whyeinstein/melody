"""WebDAV 客户端：连接测试与目录列举（扫描/播放后续基于此实现）。

只用标准库（urllib + xml.etree），不引入新依赖。
"""

from __future__ import annotations

import base64
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

DAV_NS = "{DAV:}"
AUDIO_SUFFIXES = {
    ".mp3", ".flac", ".wav", ".ogg", ".oga", ".opus", ".m4a", ".aac",
    ".wma", ".ape", ".wv", ".aiff", ".aif", ".m4b", ".dsf", ".dff",
}


class WebDavError(RuntimeError):
    """WebDAV 请求/解析失败。"""


@dataclass(slots=True)
class WebDavConfig:
    base_url: str
    username: str = ""
    password: str = ""
    verify_tls: bool = True
    timeout: float = 10.0


@dataclass(slots=True)
class WebDavEntry:
    href: str
    path: str  # 相对 base_url 的路径，空字符串表示根目录
    is_dir: bool = False
    size: int = 0
    modified: str = ""

    @property
    def is_audio(self) -> bool:
        if self.is_dir:
            return False
        _, ext = _split_extension(self.path)
        return ext.lower() in AUDIO_SUFFIXES


def _split_extension(path: str) -> tuple[str, str]:
    dot = path.rfind(".")
    slash = max(path.rfind("/"), path.rfind("\\"))
    if dot <= slash:
        return path, ""
    return path[:dot], path[dot:]


def _relative_path(href: str, base_path: str) -> str:
    parsed = urllib.parse.urlsplit(href)
    path = urllib.parse.unquote(parsed.path)
    if base_path and path.startswith(base_path):
        path = path[len(base_path):]
    return path.strip("/")


def parse_multistatus(body: bytes, base_url: str) -> list[WebDavEntry]:
    """解析 PROPFIND 的 207 Multi-Status 响应。"""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise WebDavError(f"无法解析 WebDAV 响应：{error}") from error

    base_path = urllib.parse.urlsplit(base_url).path.rstrip("/")
    entries: list[WebDavEntry] = []
    for response in root.findall(f"{DAV_NS}response"):
        href = (response.findtext(f"{DAV_NS}href") or "").strip()
        if not href:
            continue
        prop = response.find(f"{DAV_NS}propstat/{DAV_NS}prop")
        is_dir = False
        size = 0
        modified = ""
        if prop is not None:
            is_dir = prop.find(f"{DAV_NS}resourcetype/{DAV_NS}collection") is not None
            try:
                size = int(prop.findtext(f"{DAV_NS}getcontentlength") or 0)
            except ValueError:
                size = 0
            modified = prop.findtext(f"{DAV_NS}getlastmodified") or ""
        entries.append(
            WebDavEntry(
                href=href,
                path=_relative_path(href, base_path),
                is_dir=is_dir,
                size=size,
                modified=modified,
            )
        )
    return entries


class WebDavClient:
    def __init__(self, config: WebDavConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    # ------------------------------------------------------------------ 请求
    def _url(self, path: str = "") -> str:
        clean = path.strip("/")
        if not clean:
            return self.base_url
        return f"{self.base_url}/{urllib.parse.quote(clean, safe='/')}"

    def _ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        if not self.config.verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _request(
        self,
        method: str,
        path: str = "",
        *,
        depth: int | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        headers = {"User-Agent": "Melody/0.2", "Accept": "*/*"}
        if depth is not None:
            headers["Depth"] = str(depth)
        if self.config.username:
            token = base64.b64encode(
                f"{self.config.username}:{self.config.password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        request = urllib.request.Request(
            self._url(path), headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout,
                context=self._ssl_context(),
            ) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers or {}), error.read()
        except urllib.error.URLError as error:
            raise WebDavError(f"无法连接：{error.reason}") from error
        except (OSError, ssl.SSLError) as error:
            raise WebDavError(f"连接失败：{error}") from error

    # ------------------------------------------------------------------ 接口
    def test_connection(self) -> tuple[bool, str]:
        """PROPFIND Depth:0 检查地址与认证。"""
        if not self.base_url:
            return False, "未填写 WebDAV 地址"
        if not self.base_url.lower().startswith(("http://", "https://")):
            return False, "地址需要以 http:// 或 https:// 开头"
        try:
            status, _headers, body = self._request("PROPFIND", depth=0)
        except WebDavError as error:
            return False, str(error)
        if status == 401:
            return False, "认证失败（401），请检查用户名和密码"
        if status == 403:
            return False, "没有访问权限（403）"
        if status == 404:
            return False, "路径不存在（404）"
        if 300 <= status < 400:
            return False, f"服务器重定向（{status}），请填写最终地址"
        if status in (200, 207):
            if b"multistatus" not in body.lower() and status == 207:
                return False, "返回内容不是 WebDAV 响应"
            return True, "连接成功"
        return False, f"服务器返回 {status}"

    def list_dir(self, path: str = "") -> list[WebDavEntry]:
        """列出某个目录下的条目（含目录自身）。"""
        status, _headers, body = self._request("PROPFIND", path, depth=1)
        if status == 401:
            raise WebDavError("认证失败（401）")
        if status not in (200, 207):
            raise WebDavError(f"列目录失败，服务器返回 {status}")
        return parse_multistatus(body, self.base_url)
