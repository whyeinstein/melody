@echo off
rem 双击打包 Melody（需要本机有 ffmpeg 与 PyInstaller，详见 scripts/build-exe.ps1）
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build-exe.ps1" %*
echo.
pause
endlocal
