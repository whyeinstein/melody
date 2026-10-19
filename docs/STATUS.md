# Melody 项目状态

> 更新时间：2026-10-19 · 当前版本 v0.2.0（原生 Qt 版）

## 1. 一句话结论

原生 PyQt5 桌面播放器已经可用、可打包；原 Electron 路线因本机系统不兼容而弃用（代码保留）。

## 2. 路线变更记录

| 事项 | 结论 |
| --- | --- |
| 原计划 | Electron 44 + React + TypeScript，阶段 0～3 |
| 本机实测 | Windows 10 Enterprise 25H2（build 26200）：Electron 38/40/42/44 **全部启动即崩**（`0xc0000003` / `0xc0000005`），连 `electron --version` 都崩；关闭沙箱、GPU、崩溃上报均无效 |
| 对照 | 同机 Edge、VS Code、Qt（含 QtWebEngine）运行正常 |
| 决策 | Electron 版保留在 `src/`，主力改为 **PyQt5 原生桌面程序**（`desktop/`），不依赖浏览器、不联网 |

## 3. 已完成（v0.2.0）

### 3.1 应用与界面

- 左导航 + 六个一级页面：**歌曲 / 歌单 / 音乐库 / 专辑 / 播放 / 设置**
- 底部常驻播放条（封面、曲名、进度、上一首/播放暂停/下一首、随机/顺序、音量、队列）
- 深色主题 + 可切换强调色（`ui/theme.py`）

### 3.2 数据层（schema v2）

- `core/db.py`：sources / songs / albums 聚合 / playlists / playlist_items / settings / play_history
- **v1 → v2 自动迁移**（迁移前备份 `.v1.bak`）
- `core/repositories/`：songs / albums / playlists / sources / settings

### 3.3 音乐库

- 音乐来源抽象 `core/sources/`：`MusicSource` 接口 + `LocalSource`（已实现）+ `WebDavSource`
  （**已实现来源登记、DPAPI 密码加密与连接测试**；扫描/封面/播放待实现，见 `docs/remote-library-interface.md`）
- 增量扫描（size + mtime 未变则跳过），自动清理消失文件，扫描错误计数
- `ffprobe` 解析标签（mp3/flac/ogg/m4a/wav 等）、内嵌封面导出缓存
- 支持 mp3 / flac / wav / ogg / oga / opus / m4a / aac / wma / ape / wv / aiff / aif / m4b / dsf / dff
- 非 QtMultimedia 原生格式自动 `ffmpeg` 转码为 WAV 缓存后播放

### 3.4 播放子系统

- `core/playback/`：`AudioEngine`（QMediaPlayer + 转码）、`PlayQueue`（展示顺序 ≠ 播放顺序）、`PlaybackController`
- 随机 / 顺序 / 列表循环 / 单曲循环；播放结束自动切歌
- 播放次数、最近播放、收藏、播放历史写入 SQLite
- 会话恢复：记住上次曲目与进度（设置中可关闭）
- 持续播放状态、音量、静音持久化

### 3.5 页面能力

| 页面 | 能力 |
| --- | --- |
| 歌曲 | 全部歌曲表；搜索（300ms 防抖）；筛选 全部/收藏/最近播放；按来源筛选；列排序；双击播放；右键菜单（播放、加入歌单、收藏、定位文件） |
| 歌单 | 新建 / 重命名 / 删除；加曲 / 移曲 / 上移 / 下移；播放全部 |
| 音乐库 | 来源管理（启停、移除、目录存在性检测）；扫描进度与结果；曲库统计（歌曲/专辑/艺术家/总时长/失效数）；失效文件检查与清理；清转码缓存；打开数据目录 |
| 专辑 | 封面墙 + 搜索；专辑详情（封面、艺术家、年份、曲目表、播放整张） |
| 播放 | 大封面、收藏、进度、传输控制、随机与循环、当前队列 |
| 设置 | 默认音量、启动恢复上次播放、默认播放模式与随机、强调色、ffmpeg 状态、清缓存、版本信息 |

### 3.6 工程化

- 测试：**44 个 Python 测试全绿**（v2 建表与 v1→v2 迁移、搜索/排序/筛选、收藏与统计、专辑聚合、歌单增删改、设置读写、播放队列、播放控制器、扫描与增量扫描、DPAPI 凭据、WebDAV 客户端与来源集成）
- Electron 资产测试：62 个 TypeScript 测试全绿（保留但不再使用）
- 打包：`scripts/build-exe.ps1` → `dist/Melody/Melody.exe`（onedir），**实测可启动并出图**；内置 ffmpeg/ffprobe 到 `_internal/`
- 文档：`docs/architecture-redesign.md`、`docs/remote-library-interface.md`、`docs/screenshots/`（7 张页面截图）

## 4. 与原计划的阶段对照

| 原计划 | 状态 | 说明 |
| --- | --- | --- |
| 阶段 0 工程骨架 | ✅ 完成 | Electron 版完成；构建/测试/隔离约定被原生版沿用 |
| 阶段 1 核心闭环 | ✅ 完成（原生实现） | 扫描、浏览、搜索、播放、队列、歌单、收藏均已可用 |
| 阶段 2 体验补全 | ◐ 部分 | 已有：格式转码、主题色、会话恢复、设置页；缺：**歌词、均衡器、可视化、托盘、全局媒体键、迷你模式、睡眠定时器、倍速播放** |
| 阶段 3 管理与生态 | ◐ 部分 | 已有：设置、缓存清理、曲库统计、来源抽象、WebDAV 连接测试与凭据加密；缺：**标签编辑、智能歌单、M3U/PLS 导入导出、插件系统、主题包、i18n**；WebDAV 扫描/播放待实现 |

## 5. 未完成清单（按优先级）

**P0（下一步先做）**
1. 用真实音乐库试跑，修使用中暴露的问题
2. 打包优化：411MB 偏大（ffmpeg/ffprobe 各 135MB），换共享版或按需只带 ffprobe
3. 应用图标、单文件安装包（Inno Setup / NSIS）

**P1（体验）**
4. 歌词：`.lrc` 旁挂 + 内嵌 USLT，播放页滚动显示
5. 键盘快捷键与系统媒体键；系统托盘；迷你模式
6. 专辑页排序、艺术家聚合页、最近添加页

**P2（进阶）**
7. 均衡器（10 段）与可视化
8. 标签编辑（ffmpeg 无损改写 + 原子替换）
9. 智能歌单（查询 DSL）、M3U/PLS 导入导出
10. WebDAV 实装：连接测试已完成，剩余扫描/封面/播放代理（按 `docs/remote-library-interface.md`）
11. 多语言、主题包

## 6. 已知问题与技术债

- `.tmp2/` 是沙箱留下的目录（ACL 受限无法删除），已加入 `.gitignore`，可手动删除
- `src/` 与 `node_modules/` 是 Electron 资产，占空间但保留备用
- `dist/` 未进版本库，需用 `scripts/build-exe.ps1` 重建
- PyInstaller 打包依赖 `.cache/pydeps`（未进版本库）
- 封面墙在超大库下未做懒加载

## 7. 质量快照

```
Python 测试   44 passed
TypeScript    62 passed（Electron 资产）
打包          dist/Melody/Melody.exe 可启动（v0.2.0）
截图          docs/screenshots/*.png（7 张）
```
