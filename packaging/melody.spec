# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir，内置 ffmpeg/ffprobe）。

使用方式见 scripts/build-exe.ps1。
"""

from pathlib import Path
import os

ROOT = Path(SPECPATH).parent
FFMPEG_BIN = ROOT / "vendor" / "ffmpeg" / "bin"

# 设置 MELODY_CONSOLE=1 可生成带控制台的调试版，便于排查打包后的启动错误。
CONSOLE = os.environ.get("MELODY_CONSOLE") == "1"
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
