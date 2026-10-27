# 开发环境说明（Windows）

本项目在受限的执行环境（例如 DSH 的沙箱会话）里也能完成编译、类型检查与单元测试，
但有几条与环境相关的约定，遇到问题时先看这里。

## 1. 依赖缓存必须放在项目内

宿主的全局 npm 缓存目录在沙箱下不可写（`EPERM`）。`.npmrc` 已把缓存指向 `./.cache/npm`。

Electron 运行时下载缓存使用 **`electron_config_cache`** 环境变量（不是 `ELECTRON_CACHE`）：

```powershell
$env:electron_config_cache = "$PWD\.cache\electron"
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
node node_modules/electron/install.js
```

## 2. `ELECTRON_RUN_AS_NODE` 必须移除

DSH 自身是 Electron 应用，会给子进程设置 `ELECTRON_RUN_AS_NODE=1`。
带着这个变量启动 `electron.exe` 会退化成普通 Node 进程，报
`The requested module 'electron' does not provide an export named 'BrowserWindow'`。

`scripts/dev/smoke.mjs` 会在启动前删除该变量；手动运行时也要先：

```powershell
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
```

## 3. 受限沙箱下的两条限制

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `vitest` / `electron-vite` 启动即报 `spawn EPERM`（`net use` 探测） | 沙箱禁止带管道的子进程，而 Vite 在 Windows 上会同步执行 `exec("net use")` | 用 `node --import ./scripts/dev/sandbox-exec-patch.mjs …` 启动，只拦截这一条探测命令 |
| Vitest 报 `Failed to start forks worker` | 同上，fork 需要管道 | `vitest.config.ts` 已固定 `pool: 'threads'` |

对应命令（不经过 npm，避免 npm 自身的子进程）：

```powershell
node --import ./scripts/dev/sandbox-exec-patch.mjs node_modules/electron-vite/bin/electron-vite.js build
node --import ./scripts/dev/sandbox-exec-patch.mjs node_modules/vitest/vitest.mjs run
```

## 4. Chromium 窗口无法在代理会话中启动

Electron 的浏览器进程需要完整的令牌与桌面环境。在本仓库的代理会话里
`electron.exe` 会在初始化阶段崩溃（`0xC0000005` / `0x80000003`，
`--no-sandbox` 也无效），但 `--version` 与 `ELECTRON_RUN_AS_NODE` 模式正常。
因此：

- 存储、扫描、媒体库等主进程逻辑用无窗口冒烟与集成测试验证；
- **界面请在用户自己的终端里运行 `npm run dev` 验证**；
- 冒烟启动器：`node scripts/dev/smoke.mjs --headless`（只跑主进程，结果写入 `.cache/smoke-appinfo.json`）。

## 5. Python 辅助环境（可选）

应用本身不依赖 Python。如需 fixture 生成/校验脚本：

```powershell
conda env create -f scripts/env/environment.yml
conda activate melody
```

## 6. PyInstaller onefile 无法在受限沙箱里启动

onefile 版 exe 启动时要把依赖解压到临时目录。DSH 的文件沙箱会拒绝该解压目录写入
（`Access denied`，即使把 `TMP` 指到工作区也一样），所以在本会话里只能**构建** onefile、
不能启动验证；请在普通桌面（资源管理器/终端双击）测试。

- onedir 版（`dist\Melody\Melody.exe` + `_internal\`）不受影响，可在沙箱内直接运行验证；
- 单文件版建议在用户自己的桌面环境验证：`dist\Melody.exe` 双击启动，首次会慢几秒（解压）。
