@echo off
rem 双击启动 Melody（无控制台窗口）。
rem 如果窗口没有出现，看 %APPDATA%\Melody\crash.log
setlocal
cd /d "%~dp0"
set "MELODY_PY=pythonw"
where pythonw >nul 2>nul || set "MELODY_PY=python"
start "" %MELODY_PY% "desktop\run.py"
endlocal
