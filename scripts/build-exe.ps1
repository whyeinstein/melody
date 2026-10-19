<#
.SYNOPSIS
    打包 Melody 为 Windows 可执行程序（onedir，内置 ffmpeg/ffprobe）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1
    powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1 -FfmpegDir "D:\ffmpeg\bin"
#>
param(
    [string]$FfmpegDir = $env:MELODY_FFMPEG_DIR,
    [string]$PyInstallerPath = ".cache\pydeps"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $FfmpegDir) {
    $FfmpegDir = "D:\tool\ffmpeg-7.0.2-full_build\bin"
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe")) -or
    -not (Test-Path (Join-Path $FfmpegDir "ffprobe.exe"))) {
    throw "在 $FfmpegDir 找不到 ffmpeg.exe / ffprobe.exe。请用 -FfmpegDir 指定 ffmpeg 的 bin 目录。"
}

Write-Host "[1/4] 复制 ffmpeg / ffprobe 到 vendor\ffmpeg\bin ..."
$vendor = Join-Path $root "vendor\ffmpeg\bin"
New-Item -ItemType Directory -Path $vendor -Force | Out-Null
Copy-Item (Join-Path $FfmpegDir "ffmpeg.exe") $vendor -Force
Copy-Item (Join-Path $FfmpegDir "ffprobe.exe") $vendor -Force

Write-Host "[2/4] 准备 PyInstaller ..."
$pyInstaller = Join-Path $root $PyInstallerPath
if (-not (Test-Path $pyInstaller)) {
    throw "找不到 PyInstaller：$pyInstaller。请先安装（pip install pyinstaller）或把 -PyInstallerPath 指向解包目录。"
}
$env:PYTHONPATH = (Resolve-Path $pyInstaller).Path

Write-Host "[3/4] 运行 PyInstaller ..."
python -m PyInstaller packaging\melody.spec --noconfirm --clean `
    --distpath "dist" --workpath ".cache\pyinstaller-build"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 失败（exit=$LASTEXITCODE）"
}

Write-Host "[4/4] 完成"
$exe = Join-Path $root "dist\Melody\Melody.exe"
if (Test-Path $exe) {
    $size = [math]::Round(((Get-ChildItem (Join-Path $root "dist\Melody") -Recurse |
        Measure-Object Length -Sum).Sum / 1MB), 1)
    Write-Host "输出：$exe（目录约 $size MB）"
} else {
    throw "未找到输出文件 $exe"
}
