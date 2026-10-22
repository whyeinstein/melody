<#
.SYNOPSIS
    把自签名证书安装到「当前用户」的受信任根证书与受信任的发布者，仅影响当前 Windows 账号。
.NOTES
    安装根证书时 Windows 可能弹出一次安全确认，需要点「是」。
    撤销：certutil -user -delstore Root <指纹> ; certutil -user -delstore TrustedPublisher <指纹>
#>
param(
    [Parameter(Mandatory = $true)][string]$Thumbprint
)

$ErrorActionPreference = "Stop"
$cert = Get-ChildItem "Cert:\CurrentUser\My\$Thumbprint" -ErrorAction SilentlyContinue
if (-not $cert) { throw "在 当前用户\个人 证书库中找不到指纹 $Thumbprint" }

Import-Certificate -CertStoreLocation "Cert:\CurrentUser\Root" -Cert $cert | Out-Null
Import-Certificate -CertStoreLocation "Cert:\CurrentUser\TrustedPublisher" -Cert $cert | Out-Null

Write-Host "已安装到 当前用户\受信任的根证书 与 受信任的发布者："
Write-Host "  $($cert.Subject)"
Write-Host "  $Thumbprint"
Write-Host ""
Write-Host "撤销方法："
Write-Host "  certutil -user -delstore Root $Thumbprint"
Write-Host "  certutil -user -delstore TrustedPublisher $Thumbprint"
