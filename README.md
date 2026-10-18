# Melody

本地音乐播放器。当前可用版本是 **PyQt5 原生桌面程序**（`desktop/`），不依赖浏览器、不联网。

## 快速开始

1. 双击项目根目录的 **`melody.cmd`**（无控制台窗口，直接开播放器）
2. 点「添加文件夹」选择音乐目录，自动扫描入库
3. 双击歌曲播放；底部是播放条（上一首 / 播放暂停 / 下一首 / 进度 / 音量）
4. 左上搜索框可按标题、艺术家、专辑过滤

遇到问题可双击 `dev.cmd`（带控制台）查看报错，崩溃信息写入 `%APPDATA%\Melody\crash.log`。

## 当前功能

- 添加 / 移除音乐文件夹，增量扫描（不改动的文件不重复解析）
- 支持 mp3 / flac / wav / ogg / m4a / aac / wma / ape / wv 等格式：
  元数据用 `ffprobe` 解析；QtMultimedia 原生不支持格式会先用 `ffmpeg` 转码为 WAV 缓存后播放
- 歌曲列表（标题 / 艺术家 / 专辑 / 时长 / 格式）、搜索过滤、按文件夹过滤
- 播放队列即当前列表，支持上一首 / 下一首、进度拖动、音量、自动连播
- 内嵌封面提取与显示
- 音乐库持久化在 `%APPDATA%\Melody\melody.db`

## 目录

```
desktop/
  run.py                 启动入口
  melody_app/
    config.py            路径与格式白名单
    core/db.py           SQLite：文件夹 / 曲目 / 查询
    core/ffprobe.py      ffprobe / ffmpeg 封装（标签、封面、转码）
    core/scanner.py      后台扫描线程
    core/player.py       QMediaPlayer + 转码缓存
    ui/main_window.py    主窗口
    ui/song_table.py     歌曲表模型
    ui/styles.py         QSS 样式
tests_py/                Python 自动化测试（unittest）
```

## 测试

```powershell
python -m unittest discover -s tests_py -v
```

覆盖数据库读写、扫描入库、增量扫描、文件消失清理；扫描测试需要系统 ffmpeg。

## 关于 Electron 版本（已弃用）

`src/` 下保留了一套 Electron + React 实现（功能更完整，含专辑/艺术家视图、队列抽屉、主题等），
但在本机 Windows 10 Enterprise 25H2（build 26200）上 **Electron/Chromium 进程启动即崩溃**
（`0xc0000003`/`0xc0000005`，换 38/40/42/44 版本、关沙箱、关 GPU 均无效），因此改用原生 Qt。

`src/` 的代码与构建配置保留，供其他机器或系统修复后继续使用。

## 后续计划

1. 专辑 / 艺术家视图、播放列表、收藏
2. 歌词（.lrc 与内嵌）显示
3. 界面美化（主题、封面墙、更接近商业播放器的排版）
4. 系统托盘、全局媒体键、迷你模式
