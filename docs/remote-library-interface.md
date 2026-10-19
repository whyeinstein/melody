# 远程音乐库接口（WebDAV）：预留设计

- 状态：**仅接口占位，尚未实现协议**
- 目标协议：WebDAV（先做）；后续可扩展 Navidrome / Jellyfin / SMB
- 相关代码：`core/sources/base.py`、`core/sources/remote.py`、`core/sources/webdav.py`、`core/repositories/sources.py`

## 1. 这次只做什么

1. 定义远程来源的运行时接口与注册机制（已完成）；
2. 数据库里可以登记 `kind = 'webdav'` 的来源（地址、账号、TLS 选项），
   `sources.enabled` 可启停（已完成）；
3. UI 显示「添加远程库」入口与说明，但按钮禁用（已完成）；
4. 所有未实现的方法显式抛 `NotImplementedError`，避免被误用（已完成）。

**不做**：连接、列目录、扫描、元数据、封面、播放、凭据存储、代理。这些是后续实现项。

## 2. 现有接口

```
MusicSource (ABC)                 core/sources/base.py
 ├─ LocalFolderSource             local.py   （已实现）
 └─ RemoteSource                  remote.py  （远程通用占位）
     └─ WebDavSource              webdav.py  （WebDAV 占位）
SOURCE_REGISTRY / register_source / create_source_adapter
```

| 方法 | 当前行为 | 实现远程协议时 |
| ---- | -------- | -------------- |
| `available() -> bool` | 恒为 `False` | 连接成功且来源启用时为 `True` |
| `test_connection() -> (bool, str)` | `(False, "尚未实现…")` | `PROPFIND Depth:0`，返回可读的错误说明 |
| `track_count() -> int` | 已实现（按 `source_id` 统计） | 不变 |
| `connect()` | `NotImplementedError` | 建立/复用会话，校验凭据 |
| `list_entries() -> list[RemoteEntry]` | `NotImplementedError` | 递归列目录，返回音频文件条目 |
| `probe(path) -> dict \| None` | `NotImplementedError` | 结构与 `library/ffprobe.probe()` 完全一致 |
| `fetch_cover(path, target) -> bool` | `NotImplementedError` | 导出内嵌封面到本地缓存 |
| `scan()` | `NotImplementedError` | 扫描并写入 `songs`（`source_id` 指向该来源） |
| `stream_url(path) -> str` | `NotImplementedError` | 返回本地代理 URL（见第 4 节） |

`RemoteEntry`（`remote.py`）：`path`（来源内相对路径）、`size`、`mtime_ms`、`is_dir`。

数据库：`sources(kind='webdav', name, path=基础 URL, config={username, verify_tls, protocol}, enabled)`；
**密码不进数据库**，后续用 Windows DPAPI 加密后单独存储（用户目录）。

## 3. 计划的数据流

```
登记来源 → test_connection → scan（PROPFIND 列目录 + ffprobe 读标签）
        → songs(source_id=来源, path=远程相对路径) → 列表/搜索/排序复用现有仓储
播放：controller 取 Song → WebDavSource.stream_url(path)
        → 本地 127.0.0.1 代理（带 Range 与认证）→ QMediaPlayer / 转码
```

要点：

- 远程曲目与本地曲目共用 `songs` 表，`path` 存来源内相对路径，展示/搜索无需特殊处理；
- 是否显示远程曲目由来源 `enabled` 决定（`songs` 查询按 `source_id` 过滤，已具备）；
- 远程来源不参与「重新扫描全部」的本地扫描循环，单独触发。

## 4. 播放代理（实现时）

`QMediaPlayer` 无法带自定义认证头，方案与 Electron 版一致：

1. 本地起 `http.server`，只监听 `127.0.0.1`，随机端口 + 一次性 token；
2. 请求 `/media/<token>/<path>` 时转发到 WebDAV，透传 `Range` 与认证头；
3. 返回 206/Content-Range，Qt 可正常 seek；
4. 非 mp3/wav 仍走现有 ffmpeg 转码（ffmpeg 直接读代理 URL 或先下载到缓存）；
5. 进程退出/停用来源时关闭监听。

## 5. 实现清单（后续按顺序）

- [ ] 凭据存储（DPAPI）：保存/读取、删除；UI 只显示用户名
- [ ] 连接对话框：地址、用户名、密码、`verify_tls`、测试连接、错误提示
- [ ] `PROPFIND` 客户端（`urllib` 或 `http.client`，不引入新依赖）
- [ ] 递归列目录 + 音频扩展名过滤 + 忽略隐藏目录
- [ ] 元数据：ffprobe 带 `Authorization` 头读远程 URL（失败时回退到文件名）
- [ ] 扫描写库（复用 `songs.upsert_scan` 的数据结构，`path` 用相对路径）
- [ ] 播放代理（Range + 认证 + token）
- [ ] 封面缓存与缓存清理（并入「曲库工具」）
- [ ] 离线处理：`available()` 假时列表标灰、播放给出提示
- [ ] 测试：本地假 WebDAV 服务（`http.server` 模拟 PROPFIND/GET Range）
- [ ] 文档与设置页文案更新

## 6. 约束

- 纯本地：不引入账号体系、不收集遥测、不做 scrobble/在线歌词；
- 不新增第三方运行时依赖（Windows 上仅 Python 标准库 + PyQt5 + 内置 ffmpeg）；
- 远程来源默认关闭，必须由用户显式添加并启用；
- 代理只监听回环地址，token 每次启动随机生成。
