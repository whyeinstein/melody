<#
.SYNOPSIS
    生成 Melody 专用的自签名代码签名证书（仅本机使用，不写入任何密码）。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\signing\new-self-signed-cert.ps1
#>
param(
    [string]$Subject = "CN=Melody (whyeinstein), O=Melody",
    [int]$Years = 5
)

$ErrorActionPreference = "Stop"

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $Subject `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyUsage DigitalSignature `
    -NotAfter (Get-Date).AddYears($Years) `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")

$outDir = Join-Path $PSScriptRoot "..\..\.cache\signing"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$cerPath = Join-Path $outDir "melody-selfsigned.cer"
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null

Write-Host "已生成证书："
Write-Host "  主题：$($cert.Subject)"
Write-Host "  指纹：$($cert.Thumbprint)"
Write-Host "  有效期至：$($cert.NotAfter)"
Write-Host "  公钥证书：$cerPath"
Write-Host ""
Write-Host "如需在本机信任该证书（安装到 当前用户\受信任的根证书 + 受信任的发布者），执行："
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\signing\trust-self-signed-cert.ps1 -Thumbprint $($cert.Thumbprint)"
