# 发布签名说明

Windows 上的「未知发布者 / 已保护你的电脑」提示，根源是 exe 没有受信任的代码签名。
本仓库提供三种路径，按使用场景选择。

## 方案一：自签名证书（免费，仅本机有效）

适合自己使用：生成一张只属于 Melody 的证书，签名后在本机信任它。

```powershell
# 1) 生成证书（写入 当前用户\个人，同时导出 .cer 到 .cache\signing）
powershell -ExecutionPolicy Bypass -File scripts\signing\new-self-signed-cert.ps1

# 2) 给 exe 签名（换成上一步输出的指纹）
powershell -ExecutionPolicy Bypass -File scripts\signing\sign-exe.ps1 -Thumbprint <指纹>

# 3) 让本机信任这张证书（会弹一次安全确认，点「是」）
powershell -ExecutionPolicy Bypass -File scripts\signing\trust-self-signed-cert.ps1 -Thumbprint <指纹>
```

限制：**只对这台电脑有效**。别人下载后仍会看到「未知发布者」，除非他们手动信任你的证书。
如果只是解决自己电脑上的提示，这条路最省事。

撤销：

```powershell
certutil -user -delstore Root <指纹>
certutil -user -delstore TrustedPublisher <指纹>
```

## 方案二：SignPath（开源项目免费，推荐对外分发）

SignPath Foundation 为开源项目提供免费代码签名，签名证书受 Windows 信任，
SmartScreen 信誉会随时间积累。

流程：

1. 在 https://signpath.io 注册并申请 Foundation 计划（需要 GitHub 仓库公开，本仓库已满足）
2. 在 SignPath 创建组织与项目，获取：
   - `organization-id`
   - `project-slug`（建议 `melody`）
   - `signing-policy-slug`（建议 `release-signing`）
   - `artifact-configuration-slug`（`zip`）
3. 在 GitHub 安装 SignPath GitHub App，并授权本仓库
4. 在仓库 Secrets 里添加 `SIGNPATH_API_TOKEN`，Variables 里添加 `SIGNPATH_ORGANIZATION_ID`
5. 使用 `.github/workflows/sign-release.yml` 手动触发，产物会带正式签名

> 审批通常需要几天；通过后每次发版都可以自动签名。

## 方案三：商业证书（最省心）

| 类型 | SmartScreen | 成本 | 说明 |
| --- | --- | --- | --- |
| Azure Trusted Signing | 逐步建立信誉 | 约 $9.9/月 | 需 Azure 订阅与实名验证，适合长期发版 |
| OV 代码签名证书 | 积累信誉后不再提示 | 约 ¥1500–3000/年 | 需要 U 盾/云签名服务 |
| EV 代码签名证书 | **立即信任** | 约 ¥3000–5000/年 | 硬件令牌，最贵 |

## 与打包流程的衔接

`scripts/build-exe.ps1` 打包完成后，可以用 `scripts/signing/sign-exe.ps1` 对
`dist\Melody\Melody.exe` 签名；正式证书签完后建议加 `-Timestamp` 参数打时间戳，
保证证书过期后签名仍有效。

## 其他降低误报的做法

- exe 已通过 `packaging/version_info.txt` 写入产品名、版本、版权
- 保持版本号与发布说明一致，避免用户看到「无版本信息」
- 在 Release 说明中写明「首次运行如出现提示，请解除文件锁定」
