# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir / onefile，内置 ffmpeg/ffprobe）。

使用方式见 scripts/build-exe.ps1：
- 默认 onedir：dist/Melody/Melody.exe + _internal/
- 设置 MELODY_ONEFILE=1（脚本 -Mode onefile）：dist/Melody.exe 单文件
"""

from pathlib import Path
import os

ROOT = Path(SPECPATH).parent
FFMPEG_BIN = ROOT / "vendor" / "ffmpeg" / "bin"

# 设置 MELODY_CONSOLE=1 可生成带控制台的调试版，便于排查打包后的启动错误。
CONSOLE = os.environ.get("MELODY_CONSOLE") == "1"
ONEFILE = os.environ.get("MELODY_ONEFILE") == "1"
# 可选：把 onefile 的运行时解压目录固定到指定路径（默认用系统临时目录）。
RUNTIME_TMPDIR = os.environ.get("MELODY_ONEFILE_TMPDIR") or None
APP_NAME = "MelodyDebug" if CONSOLE else "Melody"

binaries = []
for name in ("ffmpeg.exe", "ffprobe.exe"):
    candidate = FFMPEG_BIN / name
    if candidate.exists():
        binaries.append((str(candidate), "."))
    else:
        print(f"[melody.spec] WARNING: 缺少 {candidate}，打包后将依赖系统 ffmpeg")

a = Analysis(
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT / "desktop")],
    binaries=binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pytest",
        "numpy",
        "pandas",
        "matplotlib",
        "IPython",
        "sqlite3.test",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if ONEFILE:
    # 单文件：所有依赖（含 ffmpeg/ffprobe）打进同一个 exe；
    # 启动时 PyInstaller 会先解压到临时目录，因此首次启动比 onedir 慢。
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "packaging" / "icon.ico"),
        version=str(ROOT / "packaging" / "version_info.txt"),
        runtime_tmpdir=RUNTIME_TMPDIR,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "packaging" / "icon.ico"),
        version=str(ROOT / "packaging" / "version_info.txt"),
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
