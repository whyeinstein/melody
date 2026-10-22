<#
.SYNOPSIS
    用指定证书给 exe 签名（默认签 dist\Melody\Melody.exe）。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\signing\sign-exe.ps1 -Thumbprint <指纹>
    powershell -ExecutionPolicy Bypass -File scripts\signing\sign-exe.ps1 -Thumbprint <指纹> -Timestamp
#>
param(
    [Parameter(Mandatory = $true)][string]$Thumbprint,
    [string]$Path = "dist\Melody\Melody.exe",
    [switch]$Timestamp
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$target = Join-Path $root $Path
if (-not (Test-Path $target)) { throw "找不到要签名的文件：$target" }

$signTool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $signTool) {
    $signTool = Get-ChildItem "D:\Windows Kits\10\bin" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
}
if (-not $signTool) { throw "找不到 signtool.exe（需要 Windows SDK 签名工具）" }

$arguments = @(
    "sign", "/fd", "SHA256", "/sha1", $Thumbprint,
    "/d", "Melody - 本地音乐播放器",
    $target
)
if ($Timestamp) {
    $arguments = @(
        "sign", "/fd", "SHA256", "/td", "SHA256",
        "/tr", "http://timestamp.digicert.com",
        "/sha1", $Thumbprint,
        "/d", "Melody - 本地音乐播放器",
        $target
    )
}

Write-Host "使用 signtool：$($signTool.FullName)"
& $signTool.FullName @arguments
if ($LASTEXITCODE -ne 0) { throw "签名失败（exit=$LASTEXITCODE）" }

$sig = Get-AuthenticodeSignature $target
Write-Host "签名完成：$target"
Write-Host "  状态：$($sig.Status)"
Write-Host "  签名者：$($sig.SignerCertificate.Subject)"
