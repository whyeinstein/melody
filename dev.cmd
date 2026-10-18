@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
if not exist logs mkdir logs
del /q logs\*.log 2>nul
echo === electron compatibility matrix === > logs\compat.txt
echo session=%SESSIONNAME% user=%USERNAME% >> logs\compat.txt
whoami /groups 2>&1 | findstr /i "Mandatory" >> logs\compat.txt
set "ELECTRON_RUN_AS_NODE="

set "E44=%~dp0node_modules\electron\dist\electron.exe"
set "E40=%~dp0.cache\electron-test\40\dist\electron.exe"
set "E38=%~dp0.cache\electron-test\38\dist\electron.exe"
set "APP=%~dp0.cache\testapp"

echo [1] VS Code control >> logs\compat.txt
if exist "D:\Microsoft VS Code\Code.exe" (
  "D:\Microsoft VS Code\Code.exe" --version >> logs\compat.txt 2>&1
  echo   exit=!ERRORLEVEL! >> logs\compat.txt
) else (
  echo   Code.exe not found >> logs\compat.txt
)

echo [2] E44 --version --no-sandbox >> logs\compat.txt
%E44% --version --no-sandbox >> logs\compat.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt

echo [3] E40 --version --no-sandbox >> logs\compat.txt
%E40% --version --no-sandbox >> logs\compat.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt

echo [4] E38 --version --no-sandbox >> logs\compat.txt
%E38% --version --no-sandbox >> logs\compat.txt 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt

del /q .cache\testapp\ok.txt 2>nul
echo [5] E44 app default >> logs\compat.txt
%E44% "%APP%" --disable-gpu >> logs\run-44-default.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q .cache\testapp\ok.txt 2>nul
echo [6] E44 app --no-sandbox >> logs\compat.txt
%E44% "%APP%" --no-sandbox --disable-gpu >> logs\run-44-nosandbox.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q .cache\testapp\ok.txt 2>nul
echo [7] E40 app default >> logs\compat.txt
%E40% "%APP%" --disable-gpu >> logs\run-40-default.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q .cache\testapp\ok.txt 2>nul
echo [8] E40 app --no-sandbox >> logs\compat.txt
%E40% "%APP%" --no-sandbox --disable-gpu >> logs\run-40-nosandbox.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q .cache\testapp\ok.txt 2>nul
echo [9] E38 app default >> logs\compat.txt
%E38% "%APP%" --disable-gpu >> logs\run-38-default.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q .cache\testapp\ok.txt 2>nul
echo [10] E38 app --no-sandbox >> logs\compat.txt
%E38% "%APP%" --no-sandbox --disable-gpu >> logs\run-38-nosandbox.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist .cache\testapp\ok.txt (echo   ok=YES >> logs\compat.txt) else (echo   ok=NO >> logs\compat.txt)

del /q logs\boot.log 2>nul
echo [11] melody headless (E44 --no-sandbox) >> logs\compat.txt
set "MELODY_HEADLESS=1"
set "MELODY_SMOKE=1"
set "MELODY_SMOKE_OUT=%~dp0.cache\headless-info.json"
%E44% . --no-sandbox --disable-gpu >> logs\run-melody-headless.log 2>&1
echo   exit=!ERRORLEVEL! >> logs\compat.txt
if exist logs\boot.log (echo   bootlog=YES >> logs\compat.txt) else (echo   bootlog=NO >> logs\compat.txt)
if exist .cache\headless-info.json (echo   appinfo=YES >> logs\compat.txt) else (echo   appinfo=NO >> logs\compat.txt)

echo === matrix done === >> logs\compat.txt
echo.
type logs\compat.txt
pause
endlocal
