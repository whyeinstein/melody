"""WebDAV 远程来源——**接口占位，尚未实现协议**。

数据库里可以登记 ``kind = 'webdav'`` 的来源（地址、账号、密码放在 config 里），
但当前版本不会连接、不会扫描、不会播放。

后续实现顺序（详见 ``docs/remote-library-interface.md``）：

1. 连接探测：``PROPFIND`` Depth:0，可选 Basic Auth，保存/校验凭据；
2. 列目录：``PROPFIND`` Depth:1 逐层遍历，收集音频扩展名；
3. 元数据：用内置 ffprobe 带 ``Authorization`` 头读取远程 URL 的标签（或先下载头部字节解析）；
4. 播放：在本地 127.0.0.1 启动带 Range 透传的 HTTP 代理，解决 QMediaPlayer 无法带认证头；
5. 封面：``fetch_cover`` 复用 ffmpeg 导出到本地 covers 目录；
6. 离线：来源不可达时 ``available()`` 为 False，UI 标灰但仍保留已入库曲目。
"""

from __future__ import annotations

from ..models import Source
from .base import register_source
from .remote import RemoteSource


class WebDavSource(RemoteSource):
    kind = "webdav"
    protocol = "webdav"

    def __init__(self, row: Source, songs_repo) -> None:
        super().__init__(row, songs_repo)
        config = row.config or {}
        self.base_url = (row.path or "").rstrip("/")
        self.username = str(config.get("username", ""))
        self.verify_tls = bool(config.get("verify_tls", True))
        # 密码不在这里保存/读取，后续由凭据存储（Windows DPAPI）提供。

    def available(self) -> bool:
        return False

    def test_connection(self) -> tuple[bool, str]:
        if not self.base_url:
            return False, "未填写 WebDAV 地址"
        return False, "WebDAV 远程库尚未实现（接口已预留）"

    def describe(self) -> str:
        return f"WebDAV · {self.base_url or '未配置地址'}"


register_source("webdav", WebDavSource)
