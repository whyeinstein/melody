@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
if not exist logs mkdir logs
del /q logs\*.log 2>nul
echo === matrix start === > logs\dev-launch.txt
echo session=%SESSIONNAME% user=%USERNAME% runasnode=[%ELECTRON_RUN_AS_NODE%] >> logs\dev-launch.txt
whoami /groups 2>&1 | findstr /i "Mandatory Restricted" >> logs\dev-launch.txt
set "ELECTRON_RUN_AS_NODE="

set "E44=%~dp0node_modules\electron\dist\electron.exe"
set "E42=%~dp0.cache\electron-test\42\dist\electron.exe"

echo [1] 44 --version
%E44% --version >> logs\dev-launch.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [2] 44 --version --no-sandbox
%E44% --version --no-sandbox >> logs\dev-launch.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [3] 44 --version --disable-gpu-sandbox --disable-gpu --no-sandbox
%E44% --version --disable-gpu-sandbox --disable-gpu --no-sandbox >> logs\dev-launch.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [4] 44 app default
%E44% . >> logs\run-44-default.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [5] 44 app --no-sandbox --disable-gpu
%E44% . --no-sandbox --disable-gpu >> logs\run-44-nosandbox.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [6] 44 app --no-sandbox --disable-gpu --disable-gpu-sandbox --disable-software-rasterizer --in-process-gpu
%E44% . --no-sandbox --disable-gpu --disable-gpu-sandbox --disable-software-rasterizer --in-process-gpu >> logs\run-44-full-off.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [7] 42 app --no-sandbox --disable-gpu
%E42% . --no-sandbox --disable-gpu >> logs\run-42-nosandbox.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo [8] 42 --version
%E42% --version >> logs\dev-launch.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\dev-launch.txt

echo === matrix done === >> logs\dev-launch.txt
echo.
type logs\dev-launch.txt
pause
endlocal
