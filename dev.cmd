@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo started > logs\dev-launch.txt
echo inherited ELECTRON_RUN_AS_NODE=[%ELECTRON_RUN_AS_NODE%] >> logs\dev-launch.txt
set "ELECTRON_RUN_AS_NODE="
set "ELECTRON_ENABLE_LOGGING=1"
echo [melody] starting dev mode, a window should appear in a few seconds...
call npm run dev > logs\dev-output.log 2>&1
set "exitCode=%ERRORLEVEL%"
echo npm run dev exited with %exitCode% >> logs\dev-launch.txt
echo.
echo [melody] electron-vite exited, code %exitCode%
echo [melody] full log: %~dp0logs\dev-output.log
echo.
type logs\dev-output.log
echo.
pause
endlocal
