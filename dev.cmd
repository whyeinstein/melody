@echo off
setlocal
cd /d "%~dp0"

rem 从资源管理器双击即可启动开发模式。
rem 注意：不要在 DSH / 代理派生出来的终端里运行本文件——
rem 那种终端带有 ELECTRON_RUN_AS_NODE=1 且禁止 Chromium 需要的命名管道，
rem 会导致 electron.exe 启动即退出且没有任何报错。

set "ELECTRON_RUN_AS_NODE="
set "ELECTRON_ENABLE_LOGGING=1"

if not exist "node_modules\electron\dist\electron.exe" (
  echo [melody] 依赖不完整，先执行 npm install ...
  call npm install
)

echo [melody] 正在启动开发模式，窗口会在几秒内出现...
call npm run dev
set "exitCode=%ERRORLEVEL%"

echo.
echo [melody] electron-vite 已退出，退出码 %exitCode%
echo [melody] 如果窗口没有出现，请把 %%APPDATA%%\melody\logs\boot.log 的内容发给开发者。
pause
endlocal
