@echo off
setlocal
cd /d "%~dp0"

rem 从资源管理器双击启动开发模式，并把完整输出落盘到 logs\dev-output.log。
rem 不要从 DSH / 代理派生的终端启动：那种终端带 ELECTRON_RUN_AS_NODE=1
rem 且禁止 Chromium 需要的命名管道，electron.exe 会启动即退出且没有报错。

if not exist "logs" mkdir "logs"
echo [%date% %time%] dev.cmd started; inherited ELECTRON_RUN_AS_NODE=[%ELECTRON_RUN_AS_NODE%] > "logs\dev-launch.txt"

set "ELECTRON_RUN_AS_NODE="
set "ELECTRON_ENABLE_LOGGING=1"

if not exist "node_modules\electron\dist\electron.exe" (
  echo [melody] 依赖不完整，正在执行 npm install ...
  call npm install >> "logs\dev-output.log" 2>&1
)

echo [melody] 正在启动开发模式，窗口应在几秒内出现；若没有出现，本窗口会显示日志。
call npm run dev >> "logs\dev-output.log" 2>&1
set "exitCode=%ERRORLEVEL%"

echo [%date% %time%] npm run dev exited with %exitCode% >> "logs\dev-launch.txt"

echo.
echo [melody] electron-vite 已退出，退出码 %exitCode%
echo [melody] 完整日志：%~dp0logs\dev-output.log
echo.
type "logs\dev-output.log"
pause
endlocal
