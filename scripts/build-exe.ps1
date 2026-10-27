<#
.SYNOPSIS
    打包 Melody 为 Windows 可执行程序（内置 ffmpeg/ffprobe）。

.DESCRIPTION
    -Mode onedir  ：默认，输出 dist\Melody\ 目录（启动快，适合日常使用）
    -Mode onefile ：输出单个 dist\Melody.exe（便于分发；每次启动会先解压到临时目录，稍慢）

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1
    powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1 -Mode onefile
    powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1 -FfmpegDir "D:\ffmpeg\bin"
#>
param(
    [ValidateSet("onedir", "onefile")]
    [string]$Mode = "onedir",
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
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "未找到 python.exe。请先安装 Python 3.10+ 并加入 PATH。"
}
python -c "import PyQt5" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "当前 Python 缺少 PyQt5。请运行：python -m pip install PyQt5"
}

$pyInstaller = Join-Path $root $PyInstallerPath
if (Test-Path $pyInstaller) {
    $env:PYTHONPATH = (Resolve-Path $pyInstaller).Path
    Write-Host "  使用本地 PyInstaller 目录：$PyInstallerPath"
} else {
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "未找到 PyInstaller。请先运行：python -m pip install pyinstaller（或用 -PyInstallerPath 指向解包目录）。"
    }
    Write-Host "  使用当前 Python 已安装的 PyInstaller"
}

if ($Mode -eq "onefile") {
    $env:MELODY_ONEFILE = "1"
    $work = ".cache\pyinstaller-build-onefile"
} else {
    $env:MELODY_ONEFILE = "0"
    $work = ".cache\pyinstaller-build"
}

Write-Host "[3/4] 运行 PyInstaller（Mode=$Mode）..."
python -m PyInstaller packaging\melody.spec --noconfirm --clean `
    --distpath "dist" --workpath $work
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 失败（exit=$LASTEXITCODE）"
}

Write-Host "[4/4] 完成"
if ($Mode -eq "onefile") {
    $exe = Join-Path $root "dist\Melody.exe"
    if (Test-Path $exe) {
        $size = [math]::Round(((Get-Item $exe).Length / 1MB), 1)
        Write-Host "输出：$exe（单文件约 $size MB；首次启动需解压到临时目录，会慢几秒）"
    } else {
        throw "未找到输出文件 $exe"
    }
} else {
    $exe = Join-Path $root "dist\Melody\Melody.exe"
    if (Test-Path $exe) {
        $size = [math]::Round(((Get-ChildItem (Join-Path $root "dist\Melody") -Recurse |
            Measure-Object Length -Sum).Sum / 1MB), 1)
        Write-Host "输出：$exe（目录约 $size MB）"
    } else {
        throw "未找到输出文件 $exe"
    }
}
