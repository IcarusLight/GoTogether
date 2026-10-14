@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
exit /b
:missing
echo Run setup.cmd first.
pause
exit /b 1
