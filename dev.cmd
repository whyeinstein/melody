@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
if not exist logs mkdir logs
del /q logs\*.log 2>nul
echo started > logs\dev-launch.txt
echo session=%SESSIONNAME% user=%USERNAME% runasnode=[%ELECTRON_RUN_AS_NODE%] >> logs\dev-launch.txt
whoami /groups 2>&1 | findstr /i "Mandatory" >> logs\dev-launch.txt
set "ELECTRON_RUN_AS_NODE="
set "ELECTRON_ENABLE_LOGGING=1"
set "MELODY_DIAG=1"

echo === electron --version (plain) === >> logs\dev-launch.txt
node_modules\electron\dist\electron.exe --version >> logs\dev-launch.txt 2>&1
echo version exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo === electron --version (disable-gpu-sandbox) === >> logs\dev-launch.txt
node_modules\electron\dist\electron.exe --version --disable-gpu-sandbox >> logs\dev-launch.txt 2>&1
echo version+gpusandbox exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [melody] RUN 1/3: baseline (expect crash) ...
set "MELODY_EXTRA_ARGS="
call npm run dev > logs\run1.log 2>&1
echo run1 baseline exit=!ERRORLEVEL! >> logs\dev-launch.txt
if exist logs\chromium.log copy /y logs\chromium.log logs\chromium-run1.log >nul

echo [melody] RUN 2/3: --disable-gpu-sandbox (if a window appears, close it to continue) ...
set "MELODY_EXTRA_ARGS=--disable-gpu-sandbox"
call npm run dev > logs\run2.log 2>&1
echo run2 disable-gpu-sandbox exit=!ERRORLEVEL! >> logs\dev-launch.txt
if exist logs\chromium.log copy /y logs\chromium.log logs\chromium-run2.log >nul

echo [melody] RUN 3/3: --disable-gpu-sandbox --disable-gpu ...
set "MELODY_EXTRA_ARGS=--disable-gpu-sandbox --disable-gpu"
call npm run dev > logs\run3.log 2>&1
echo run3 gpusandbox+nogpu exit=!ERRORLEVEL! >> logs\dev-launch.txt
if exist logs\chromium.log copy /y logs\chromium.log logs\chromium-run3.log >nul

echo.
echo [melody] diagnostics finished, see logs\ folder
type logs\dev-launch.txt
pause
endlocal
