"""WebDAV 远程来源。

当前已实现：
- 来源登记（地址、用户名、TLS 选项）与启用/停用；
- 密码用 Windows DPAPI 加密保存在本地（不落数据库）；
- ``test_connection()``：PROPFIND Depth:0 校验地址与认证；
- 递归列目录 + 本地代理扫描写库（``remote_scanner``）；
- 播放：``stream_url()`` 返回本地 Range 代理 URL，QMediaPlayer / ffmpeg 可直接使用。

尚未实现：远程标签编辑、离线标记与更细的缓存策略。
接口契约与实现清单见 ``docs/remote-library-interface.md``。
"""

from __future__ import annotations

import hashlib

from ..models import Source
from .base import register_source
from .remote import RemoteSource
from .webdav_client import WebDavClient, WebDavConfig, WebDavError
from .webdav_proxy import get_proxy


class WebDavSource(RemoteSource):
    kind = "webdav"
    protocol = "webdav"

    def __init__(self, row: Source, songs_repo, credentials=None) -> None:
        super().__init__(row, songs_repo, credentials)
        config = row.config or {}
        self.base_url = (row.path or "").rstrip("/")
        self.username = str(config.get("username", ""))
        self.verify_tls = bool(config.get("verify_tls", True))
        self._available = False
        self._last_message = "尚未测试连接"

    # ------------------------------------------------------------------ 状态
    def available(self) -> bool:
        """最近一次连接测试是否成功；不会主动联网。"""
        return self._available

    @property
    def last_message(self) -> str:
        return self._last_message

    def password(self) -> str:
        if self._credentials is None:
            return ""
        try:
            return self._credentials.load(self.id) or ""
        except (OSError, RuntimeError):
            return ""

    def client(self) -> WebDavClient:
        return WebDavClient(
            WebDavConfig(
                base_url=self.base_url,
                username=self.username,
                password=self.password(),
                verify_tls=self.verify_tls,
            )
        )

    def test_connection(self) -> tuple[bool, str]:
        if not self.base_url:
            self._available = False
            self._last_message = "未填写 WebDAV 地址"
            return False, self._last_message
        try:
            ok, message = self.client().test_connection()
        except WebDavError as error:
            ok, message = False, str(error)
        except Exception as error:  # noqa: BLE001 - 任何异常都转成可读提示
            ok, message = False, f"连接失败：{error}"
        self._available = ok
        self._last_message = message
        return ok, message

    def describe(self) -> str:
        return f"WebDAV · {self.base_url or '未配置地址'}"

    def _signature(self) -> str:
        raw = f"{self.base_url}|{self.username}|{self.password()}|{int(self.verify_tls)}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def stream_url(self, path: str) -> str:
        """返回本地代理 URL（带 Range 透传与认证），供 QMediaPlayer / ffmpeg 使用。"""
        if not self.base_url:
            raise WebDavError("未配置 WebDAV 地址")
        proxy = get_proxy(self.id, self.client(), self._signature())
        return proxy.url_for(path)

    # ----------------------------------------------------- 仍是占位的后续能力
    # connect / list_entries / probe / fetch_cover / scan 继承自 RemoteSource，
    # 当前显式抛 NotImplementedError（扫描与播放走独立实现，见 remote_scanner / 本地代理）。


register_source("webdav", WebDavSource)
