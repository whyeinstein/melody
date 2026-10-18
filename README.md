# Melody

本地音乐播放器：Electron + React + TypeScript，离线可用、架构可扩展。

## 当前状态

- **阶段 0（进行中）**：工程骨架、类型化 IPC、存储引擎选型实测。
- 阶段 1：音乐库扫描、浏览、搜索、播放核心、播放列表。
- 阶段 2：歌词、均衡器、可视化、ffmpeg 转码、托盘与全局热键。
- 阶段 3：标签编辑、智能播放列表、导入导出、插件与主题。

## 环境要求

- Windows 10/11 x64
- Node.js 22+（本项目在 Node 24.13 / npm 11.6 上验证）
- ffmpeg（阶段 2 转码需要；当前仅做探测）

## 快速开始

```powershell
npm install        # 依赖与 Electron 运行时都缓存在项目内的 .cache/
npm run dev        # 启动开发模式
```

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 开发模式（Vite HMR + Electron） |
| `npm run build` | 构建 `out/` |
| `npm run typecheck` | 主进程与渲染进程分别做类型检查 |
| `npm run test` | vitest 单元与集成测试 |
| `npm run fixtures` | 用 ffmpeg 生成测试音乐库（阶段 1） |
| `npm run dist` | 打包 portable / NSIS 安装包 |

## 目录结构

```
src/
  shared/    跨进程共享的类型、IPC 契约（zod）、常量、i18n
  main/      Electron 主进程：数据库、扫描、媒体服务、窗口
  preload/   contextBridge 白名单桥
  renderer/  React 界面、状态、命令与视图注册表
```

## 环境隔离约定

- npm 缓存固定在 `./.cache/npm`，Electron 运行时缓存在 `./.cache/electron`，不污染全局缓存。
- 若需 Python 辅助脚本，使用 `conda env create -f scripts/env/environment.yml` 创建 `melody` 环境；应用本身不依赖 Python。

## 架构要点

- 渲染进程开启 `contextIsolation` + `sandbox`，只能通过 `window.melody` 的受限频道通信。
- 渲染层负责播放状态机与队列；主进程只负责文件系统、数据库与媒体字节流。
- 媒体音频通过本地 HTTP（仅 127.0.0.1）按 trackId 提供，支持 Range 请求。
