# ADR 0001：嵌入式数据库选型

- 状态：已采纳
- 日期：2026-10-18

## 背景

音乐库需要持久化曲目、封面、播放列表与播放历史，规模目标 1 万～10 万条。
候选：

1. `node:sqlite`（Electron 自带 Node 的内置 SQLite，零依赖、无原生编译）
2. `better-sqlite3`（成熟，但需要为 Electron ABI 重新编译，依赖 MSVC 工具链）
3. `sql.js`（WASM，纯 JS，但整库内存态、无并发写、FTS 支持不确定）

## 证据

- 本机 Node 24.13：`node:sqlite` 的 `DatabaseSync` 可用（建表/插入/查询通过）。
- Electron 44.9.0 自带 Node 24.22.0：用 `ELECTRON_RUN_AS_NODE=1 electron.exe -e "require('node:sqlite')"` 实测通过，
  输出 `NODE_SQLITE_OK ok 24.22.0`。该二进制与主进程使用的是同一个 Node 构建，
  因此主进程内 `await import('node:sqlite')` 可用。
- 未验证项：`better-sqlite3` 在本机 MSVC 工作负载下能否顺利为 Electron 重新编译（VS 2022 已安装，但 C++ 工作负载未知）。

## 决策

采用 **`node:sqlite`**：主进程内通过统一的 `DbHandle` 适配接口使用（`prepare/exec/close/transaction`），
迁移用纯 SQL 文件 + `meta.schema_version`。

约束：

- 每次启动由 `probeStorage()` 自检；不可用时应用显式报错并提示降级方案，而不是静默崩溃。
- `node:sqlite` 目前标记为 experimental，API 变动风险由适配层隔离。
- 全文检索先探测 FTS5 是否可用；不可用则回退到 `LIKE` + 归一化列（`*_norm`），行为一致。

## 后果

- 安装体积与 CI 复杂度下降，无需 node-gyp / electron-rebuild。
- 若未来 Electron 移除或改动 `node:sqlite`，只需替换 `DbHandle` 实现（`better-sqlite3` 或 `sql.js`）。
