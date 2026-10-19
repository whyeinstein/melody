# vendor/ffmpeg

打包时由 `scripts/build-exe.ps1` 把 `ffmpeg.exe`、`ffprobe.exe` 复制到 `vendor/ffmpeg/bin/`，
再由 `packaging/melody.spec` 打进 `dist/Melody/`。

二进制体积较大且涉及发行许可，因此**不入库**（见 `.gitignore`）。
开发时也可以不复制，程序会依次查找：

1. 环境变量 `MELODY_FFMPEG_DIR`
2. 打包目录（`_MEIPASS` / exe 同级）
3. 仓库内 `vendor/ffmpeg/bin`
4. `%ProgramFiles%\ffmpeg\bin`
5. 系统 `PATH`

想换更小的 ffmpeg 发行版（如 gyan.dev 的 essentials build）时，直接替换这两个文件即可。
