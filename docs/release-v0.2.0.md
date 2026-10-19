# Melody v0.2.0

第一个可用的本地音乐播放器版本（PyQt5 原生 Windows 桌面程序，不依赖浏览器、不联网）。

## 安装与运行

1. 解压 `Melody-0.2.0-win64.zip`
2. 双击 `Melody.exe`（无需安装 Python，已内置运行时与 ffmpeg/ffprobe）
3. 进入「音乐库」页 →「添加本地文件夹」选择音乐目录，自动扫描入库
4. 在「歌曲」页双击播放

> 首次启动会在 `%APPDATA%\Melody` 创建数据库、封面与转码缓存。
> 崩溃日志位于 `%APPDATA%\Melody\crash.log`。

## 功能

- 六个页面：歌曲 / 歌单 / 音乐库 / 专辑 / 播放 / 设置
- 增量扫描本地文件夹，自动清理已消失文件
- 支持 mp3 / flac / wav / ogg / opus / m4a / aac / wma / ape / wv / aiff / dsf / dff 等格式；
  非原生格式自动用 ffmpeg 转码为 WAV 缓存后播放
- 内嵌封面提取与专辑封面墙
- 搜索（标题/艺术家/专辑）、排序、筛选（收藏 / 最近播放 / 来源）
- 播放队列（展示顺序 ≠ 播放顺序）、随机 / 顺序 / 列表循环 / 单曲循环
- 收藏、播放次数、最近播放、会话恢复（记住上次曲目与进度）
- 歌单新建/重命名/删除、加曲/移曲/排序、播放全部
- 曲库统计、失效文件检查与清理、转码缓存清理
- 深色主题与可切换强调色

## 已知限制

- 暂不支持歌词、均衡器、可视化、系统托盘、全局媒体键、迷你模式
- 远程音乐库（WebDAV）仅有接口占位，尚未实现
- 打包为绿色目录版（onedir），未提供安装程序
- 仅提供 Windows x64 版本

## 系统要求

- Windows 10/11 x64
- 约 500 MB 磁盘空间（含内置 ffmpeg）

## 校验

发布包内附 `SHA256.txt`，可用 PowerShell 校验：

```powershell
Get-FileHash .\Melody-0.2.0-win64.zip -Algorithm SHA256
```

## 说明

本项目的 Electron + React 实现保留在仓库 `src/` 目录，供其他环境使用；
由于开发机（Windows 10 Enterprise 25H2 build 26200）上 Electron 进程无法启动，
v0.2.0 起主力实现改为 PyQt5 原生版本（`desktop/`）。
