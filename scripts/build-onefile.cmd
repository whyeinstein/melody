@echo off
rem Build a single-file Melody.exe (onefile). Requires ffmpeg and PyInstaller.
rem See scripts/build-exe.ps1 for details.
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build-exe.ps1" -Mode onefile %*
echo.
pause
endlocal
