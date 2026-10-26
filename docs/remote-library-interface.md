# WebDAV 远程音乐库

- 状态：**已实现**（来源登记、DPAPI 凭据、连接测试、递归扫描、封面、远程播放）
- 目标协议：WebDAV；后续可扩展 Navidrome / Jellyfin / SMB
- 相关代码：`core/sources/webdav.py`、`webdav_client.py`、`webdav_proxy.py`、
  `core/library/remote_scanner.py`、`core/credentials.py`、`core/repositories/sources.py`

## 1. 实现结构

```
WebDavSource (sources/webdav.py)
 ├─ client()            → WebDavClient（PROPFIND / 认证 / TLS 校验）
 ├─ test_connection()   → PROPFIND Depth:0，区分 401/403/404/重定向/网络错误
 ├─ stream_url(path)    → 本地 127.0.0.1 代理 URL（带 Range 与认证）
 └─ password()          → CredentialStore（Windows DPAPI）

RemoteScanWorker (library/remote_scanner.py)
 └─ list_tree() → 每个音频走本地代理交给 ffprobe 读标签 / ffmpeg 抽封面 → 写入 songs

WebDavProxy (sources/webdav_proxy.py)
 └─ http.server，仅监听 127.0.0.1，URL 带随机 token，透传 Range/认证
```

数据库：`sources(kind='webdav', name, path=基础 URL, config={username, verify_tls, protocol}, enabled)`；
远程曲目与本地共用 `songs` 表，`songs.path` 存**来源内相对路径**。
**密码不写数据库**，用 Windows DPAPI 加密存到 `<数据目录>/credentials/source-<id>.bin`。

## 2. 数据流

```
登记来源 → test_connection → 扫描（PROPFIND 递归 + ffprobe 读标签）
        → songs(source_id=来源, path=相对路径) → 列表/搜索/排序复用现有仓储

播放：PlaybackController 取 Song
     → LibraryService.stream_url_for()
     → WebDavSource.stream_url() → 本地代理 URL
     → mp3/wav：ffmpeg 下载到缓存（-c:a copy）后用 QMediaPlayer 播放
     → 其他格式：ffmpeg 转 WAV 缓存后播放
```

要点：

- 远程曲目与本地曲目共用同一套页面、搜索、排序、歌单、收藏；
- 是否显示远程曲目由来源 `enabled` 决定；
- 「音乐库 → 扫描全部来源」会按来源顺序扫描本地与远程；
- 扫描前一次性读取已有文件状态（size + `getlastmodified`）做增量，未变化不重复解析；
- 远程文件消失时清理对应曲目记录（与本地一致）。

## 3. 播放细节

`QMediaPlayer` / DirectShow 对 HTTP 源支持不稳定，因此远程播放统一走本地代理：

1. 每个来源一个代理实例，只监听 `127.0.0.1`，随机端口 + 随机 token；
2. 请求 `/media/<token>/<相对路径>` 转发到 WebDAV，透传 `Range` 与 Basic Auth；
3. 返回 200/206、`Content-Range`、`Accept-Ranges`，拖动进度正常；
4. mp3/wav 先 `ffmpeg -c:a copy` 下载到 `cache/` 再本地播放；其他格式转 WAV；
5. 进程退出时关闭所有代理（`MainWindow.closeEvent` → `shutdown_all()`）。

## 4. 接口现状

| 方法 | 现状 |
| ---- | ---- |
| `available()` | 最近一次连接测试结果；不主动联网 |
| `test_connection()` | PROPFIND Depth:0，返回可读错误 |
| `track_count()` | 按 `source_id` 统计 |
| `stream_url(path)` | 本地代理 URL（真正可用） |
| `connect()` / `list_entries()` / `probe()` / `fetch_cover()` / `scan()` | 仍显式 `NotImplementedError`；扫描/元数据/封面由 `RemoteScanWorker` 直接实现（保持接口占位供将来统一） |

`WebDavClient`：`test_connection`、`list_dir`、`list_tree`、`url_for`；
`WebDavEntry`：`path/size/modified_ms/is_dir/is_audio`。

## 5. 已知限制（后续可做）

- 远程转码/下载缓存以代理 URL 为键（端口/token 每次启动变化），**重启后会重新下载/转码**；
  缓存可在「音乐库 → 清理转码缓存」中清理；
- 未做离线标记：服务器不可达时列表不置灰，播放会给出错误提示；
- 远程标签编辑、按需只读缓存、断点续传尚未实现；
- 扫描为逐文件 ffprobe（4 并发），超大远程库首次扫描较慢；后续可考虑并发上限与进度细化；
- 目前只支持 WebDAV Basic Auth，其他协议需新增 `MusicSource` 子类。

## 6. 测试

- `tests_py/fake_webdav.py`：假 WebDAV 服务（PROPFIND 目录树 + GET/HEAD Range）；
- `test_webdav_client.py`：连接测试、401、目录解析、来源+DPAPI 集成；
- `test_webdav_proxy.py`：Range、完整 GET、HEAD、404；
- `test_webdav_scan.py`：递归列目录、扫描/增量/清理、远程播放地址（含 ffmpeg 真实转码链路）；
- `test_playback.py`：播放控制器会调用 URL 解析器（远程地址注入）。

## 7. 约束

- 纯本地：不引入账号体系、不收集遥测、不做 scrobble/在线歌词；
- 不新增第三方运行时依赖（标准库 + PyQt5 + 内置 ffmpeg）；
- 远程来源必须由用户显式添加并启用；
- 代理只监听回环地址，token 每次启动随机生成。
