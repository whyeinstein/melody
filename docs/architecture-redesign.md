# Melody 重构设计：六页面 PyQt5 架构

- 状态：已实施（2026-10-18）
- 范围：`desktop/`（PyQt5 原生版）。`src/`（Electron 版）保持不变，仅作交互与领域模型参考。

## 1. 目标与约束

**目标**

1. 界面从「单窗口 + 折叠工具栏」升级为**六个一级页面**：歌曲、歌单、音乐库、专辑、播放、设置，
   外加常驻底部播放条。
2. 把「扫到什么就放什么」的临时播放列表，升级为**独立播放队列**（随机 / 列表循环 / 单曲循环 / 播放历史）。
3. 数据层从两张表升级为 v2：**音乐来源（本地 + 远程占位）、收藏、播放次数、歌单、设置**，并带可回滚迁移。
4. 代码分层：`ui/pages` 只做界面，业务在 `core/`，页面之间通过 `AppContext` 通信，禁止页面直接互相 import。

**约束**

- 继续使用 PyQt5 + QMediaPlayer + ffmpeg/ffprobe，不引入新运行时依赖。
- 保留命令行开关（`--scan` / `--screenshot` / `--autoplay` / `--exit-after`），便于自动化验证。
- 旧版本地库（`%APPDATA%\Melody\melody.db`）必须能自动迁移，迁移前留 `.v1.bak` 备份。

## 2. 页面结构

底部播放条在所有页面常驻；「播放」页是完整的 Now Playing 视图。

| # | 页面 | 关键内容 |
| - | ---- | -------- |
| 1 | **歌曲** | 全部歌曲表；搜索（标题/艺术家/专辑）、筛选（全部/收藏/最近）、按来源过滤、点列头排序、右键菜单（播放/加入歌单/收藏/定位文件） |
| 2 | **歌单** | 左歌单列表（新建/重命名/删除）+ 右曲目表；播放全部、移除曲目、拖拽排序（P1 可简化为上下移动） |
| 3 | **音乐库** | ① 浏览方式：按来源浏览入口；② 音乐来源：本地文件夹增删、启停，远程库占位开关；③ 曲库工具：扫描/进度、统计、失效文件检查与清理、缓存清理、打开数据目录 |
| 4 | **专辑** | 封面墙（网格）+ 搜索；点击进入专辑详情（封面/艺术家/年份/曲目表/播放全部） |
| 5 | **播放** | 大封面、标题/艺术家/专辑、可拖动进度、传输控制、随机/循环/音量、收藏、当前队列列表 |
| 6 | **设置** | 播放（默认音量、恢复上次播放、默认循环/随机）、外观（强调色）、音乐库（ffmpeg 状态、扫描）、远程库（占位说明）、数据（路径/缓存/关于） |

导航顺序固定为：歌曲 → 歌单 → 音乐库 → 专辑 → 播放 → 设置。

## 3. 分层架构

```
┌──────────────────────────── ui/ ─────────────────────────────┐
│ main_window.py  外壳：导航 + QStackedWidget + PlayerBar        │
│ pages/          六个页面（只处理交互，不写 SQL）                 │
│ widgets/        SongTableView / CoverLabel / Card / PageHeader  │
└───────────────┬───────────────────────────────────────────────┘
                │ AppContext：repos + service + controller + 信号
┌───────────────▼───────────────────────────────────────────────┐
│ core/playback   Queue（顺序/随机/循环）→ PlaybackController     │
│                 → AudioEngine（QMediaPlayer + 转码缓存）        │
│ core/library    LibraryService（扫描/工具/统计）→ ScanWorker     │
│ core/sources    MusicSource 抽象（local / remote 占位）         │
│ core/repositories  SongsRepo / AlbumsRepo / PlaylistsRepo /     │
│                    SourcesRepo / SettingsRepo                  │
│ core/db.py      SQLite 连接 + schema v2 + v1→v2 迁移            │
└───────────────────────────────────────────────────────────────┘
```

页面通信只用 `AppContext` 上的信号：

| 信号 | 触发 | 订阅者 |
| ---- | ---- | ------ |
| `library_changed` | 扫描完成、来源增删/启停、失效文件清理 | 所有页面刷新 |
| `sources_changed` | 来源列表变化 | 歌曲页来源下拉、音乐库页 |
| `playlists_changed` | 歌单增删改 | 歌单页、歌曲页右键菜单 |
| `open_songs_requested(source_id)` | 音乐库页「浏览」按钮 | MainWindow：切到歌曲页并过滤来源 |
| `status_message(str)` | 任意操作反馈 | MainWindow 状态栏 |
| `theme_changed()` | 设置页改强调色 | MainWindow 重新应用 QSS |

## 4. 目录结构（重构后）

```
desktop/
  run.py
  melody_app/
    main.py                 入口：argparse / 崩溃日志 / QApplication
    app.py                  装配：Database → repos → services → MainWindow
    config.py               路径与音频扩展名
    core/
      models.py             Song / Album / Playlist / Source / LibraryStats
      db.py                 连接 + schema + 迁移
      repositories/
        songs.py  albums.py  playlists.py  sources.py  settings.py
      sources/
        base.py  local.py  remote.py（占位）
      library/
        ffprobe.py  scanner.py  service.py
      playback/
        engine.py  queue.py  controller.py
    ui/
      app_context.py
      navigation.py
      theme.py
      main_window.py
      player_bar.py
      widgets/  song_table.py  cover.py  common.py
      pages/    songs_page.py  playlists_page.py  library_page.py
                albums_page.py  player_page.py  settings_page.py
```

## 5. 数据模型（schema v2）

```sql
meta(key, value)                       -- schema_version = 2
sources(id, kind, name, path, config, enabled, added_at)   -- kind: local | remote
songs(id, path UNIQUE, source_id → sources ON DELETE CASCADE,
      title, artist, album, album_artist, genre, year, track_no, disc_no,
      duration_ms, bitrate, sample_rate, channels, format, size, mtime_ms,
      cover_path, favorite, play_count, last_played_at, missing, added_at, updated_at)
playlists(id, name UNIQUE, created_at, updated_at)
playlist_items(playlist_id → playlists, song_id → songs, position, added_at,
               PRIMARY KEY(playlist_id, song_id))
settings(key PRIMARY KEY, value TEXT)   -- JSON 值
play_history(id, song_id → songs, played_at)
```

索引：`songs(source_id)`、`songs(artist COLLATE NOCASE)`、`songs(album COLLATE NOCASE)`、
`songs(favorite)`、`songs(last_played_at)`、`playlist_items(song_id)`、`play_history(played_at)`。

**v1 → v2 迁移**（`Database._migrate_v1`）：

1. 备份数据库文件为 `melody.db.v1.bak`（已存在则跳过）；
2. `folders` → `sources`（kind='local'，name=目录名，path=folder.path）；
3. 重建 `songs` 表：`folder_id` → `source_id`（按路径匹配），补 `favorite=0 / play_count=0 / last_played_at=NULL / missing=0 / disc_no=NULL`；
4. 删除旧 `folders` 表，重建索引，写入 `meta.schema_version='2'`；
5. 全程单事务 + `PRAGMA foreign_keys=OFF`，失败回滚。

## 6. 音乐来源抽象

```python
class MusicSource(ABC):          # sources/base.py
    kind: str                    # 'local' | 'remote'
    def available(self) -> bool  # 当前是否可用（本地：目录存在；远程：已连接）
    def track_count(self) -> int

SOURCE_REGISTRY: dict[str, type[MusicSource]]
def create_source_adapter(row, songs_repo) -> MusicSource   # 按 kind 分发
```

- `LocalFolderSource`：目录存在即可用，曲目数由 SQL 统计。
- `RemoteSource`：远程通用占位，`available()` 恒为 False，扫描/播放抛 `NotImplementedError`。
- `WebDavSource`（`sources/webdav.py`）：WebDAV 远程库，已实现来源登记、DPAPI 密码存储与
  `PROPFIND` 连接测试（`webdav_client.py`）；扫描、封面、播放待实现。
  实现路线与接口契约见 [remote-library-interface.md](remote-library-interface.md)。
- 后续接入具体协议时只需实现 `RemoteSource` 的接口并注册，UI 无需改动。
- `sources.enabled` 决定该来源是否参与「扫描全部」与歌曲列表默认可见范围（远程库可一键开关）。

## 7. 播放子系统

- **Queue**：`items`（展示顺序）+ `order`（播放顺序，随机时是 items 的排列）+ `position`。
  模式：`sequential`（播完停）、`repeat-all`（列表循环）、`repeat-one`（单曲循环）；`shuffle` 独立开关。
- **AudioEngine**：`QMediaPlayer`；`.mp3/.wav` 直放，其余格式 ffmpeg 转 WAV 缓存后播放（沿用现有策略）。
- **PlaybackController**：唯一入口，负责
  - `play_songs(songs, start)` / `play_song(song)` / `toggle` / `next` / `previous` / `seek` / `set_volume` / `set_mute` / `set_shuffle` / `cycle_repeat`；
  - 曲目结束时按模式自动切歌；
  - 标记录放次数与历史（`songs.play_count`、`last_played_at`、`play_history`）；
  - 会话持久化：音量、随机/循环、上次曲目与位置（设置键 `playback.*`），启动时恢复。
- 信号：`track_changed(Song|None)`、`state_changed(str)`、`position_changed(int)`、`duration_changed(int)`、`queue_changed()`。

## 8. 页面规格

### 8.1 歌曲页（`pages/songs_page.py`）
- 顶栏：标题 + 「共 N 首 · 总时长 X」；搜索框（200ms 防抖，单一 QTimer 重启）；筛选下拉（全部/收藏/最近）；
  来源下拉（全部来源 + 已启用来源）。
- 表格列：`♥ / 标题 / 艺术家 / 专辑 / 时长 / 格式`；点击列头切换排序（字段：title/artist/album/duration/format/added）。
- 双击行 → 以当前列表为队列从该行播放；右键菜单：播放、加入歌单、收藏/取消收藏、在资源管理器中显示。
- 订阅 `library_changed/sources_changed/playlists_changed` 自动刷新。

### 8.2 歌单页（`pages/playlists_page.py`）
- 左：歌单列表（名称 + 曲目数），底部「新建 / 重命名 / 删除」。
- 右：歌单标题 + 「播放全部 / 移除所选」+ 曲目表；空歌单显示占位提示。
- 重命名/新建用 `QInputDialog`；删除需二次确认。

### 8.3 音乐库页（`pages/library_page.py`，QScrollArea + 卡片）
- **音乐来源**：每行来源显示 类型徽标、名称、路径、曲目数、启用开关、移除按钮；「添加本地文件夹」；
  远程库「添加」按钮为占位（禁用 + tooltip）。
- **浏览方式**：来源卡片，点击「浏览」→ `ctx.open_songs_requested.emit(source_id)`。
- **曲库工具**：统计（歌曲/专辑/艺术家/总时长/失效）、扫描按钮与进度条、检查并清理失效文件、
  清理转码缓存、打开数据目录。
- 订阅 `library_changed/sources_changed`。

### 8.4 专辑页（`pages/albums_page.py`）
- `QStackedWidget`：封面墙 ↔ 专辑详情。
- 封面墙：`QListWidget` IconMode（160px 封面 + 专辑名/艺术家/曲目数），顶部搜索。
- 详情：返回按钮、封面、「播放全部」、专辑信息、曲目表（复用 SongTableView），双击播放整张专辑。

### 8.5 播放页（`pages/player_page.py`）
- 左：大封面（≥280px）、标题/艺术家/专辑、收藏按钮、进度条 + 时间、传输控制、
  随机/循环切换、音量。
- 右：当前队列列表（当前曲目高亮，双击跳播，可清空）。
- 空队列时显示「从歌曲/专辑开始播放」占位。

### 8.6 设置页（`pages/settings_page.py`）
- 播放：默认音量、恢复上次播放（开关）、默认循环模式、默认随机（开关）——写入 `settings`。
- 外观：强调色下拉（紫/蓝/青/绿/橙），立即生效（`theme_changed`）。
- 音乐库：ffmpeg/ffprobe 路径与可用状态、扫描并发说明。
- 远程库：占位说明（协议待定，接口已预留）。
- 数据：数据目录（可打开）、转码/封面缓存大小与清理、版本与曲库统计。

## 9. 测试计划

- `tests_py/test_database.py`：v2 建表、仓库查询/排序/搜索/收藏/统计、歌单增删改、设置读写、v1→v2 迁移（构造 v1 schema 后断言数据保留、备份存在）。
- `tests_py/test_scanner.py`：沿用现有扫描测试，改用 `source` 概念（新增/增量/清理/多格式标签）。
- 界面冒烟：`python desktop/run.py --page songs --screenshot shot.png`、`--page player`、`--page albums` 等逐页截图人工验证。

## 10. 实施顺序

1. 数据层 v2（models / db / repositories）→ 2. 来源抽象与 LibraryService → 3. 播放子系统 →
4. 共享 UI 与外壳 → 5. 六个页面 → 6. 测试与截图验证。

## 11. 实施结果（2026-10-18）

**已落地**

- 数据层 v2 与迁移：`core/db.py`；真实旧库（`%APPDATA%\Melody\melody.db`）迁移验证通过
  （schema=2，songs 保留，生成 `melody.db.v1.bak`，`folders` 并入 `sources` 后删除）。
- 仓储：`songs / albums / playlists / sources / settings`，页面不写 SQL。
- 来源抽象：`core/sources/base.py` 的 `MusicSource` + 注册表；本地实现、远程占位。
- 音乐库服务：来源管理、顺序扫描、统计、失效检查/清理、转码与封面缓存清理。
- 播放子系统：`PlayQueue`（顺序/随机/列表循环/单曲循环）、`PlaybackController`
  （播放记录、历史、会话恢复、模式持久化）、`AudioEngine`（沿用转码策略）。
- 六个页面 + 常驻播放条 + 强调色主题，逐页截图见 `docs/screenshots/`。
- 测试：`tests_py` 24 个用例通过（数据库/迁移/歌单/设置/队列/控制器/扫描）。

**实施中对设计的两处修正**

1. **扫描线程使用独立 SQLite 连接**：原 v1 代码在 4 个 ffprobe 子线程里共用同一个连接查库，
   高并发下会出现 `sqlite3.InterfaceError`。现在扫描线程自己开连接，子线程只读内存字典，
   数据库写入全部串行在扫描线程内，并给连接加 `busy_timeout=5000`。
2. **迁移前备份改用 SQLite backup API**：WAL 模式下直接复制主文件可能漏掉未 checkpoint 的数据。

**验证方式**

| 项 | 命令 / 结果 |
| -- | ----------- |
| 单元测试 | `python -m unittest discover -s tests_py -v` → 24 passed |
| 离屏冒烟 | `.cache/smoke_ui.py` 逐页构造并切换六页面，无异常 |
| 真实旧库迁移 | 复制 `%APPDATA%\Melody\melody.db` 后启动 → schema 2、备份存在、曲目保留 |
| 界面 | `python desktop/run.py --page <songs/playlists/library/albums/player/settings> --screenshot ...` |
