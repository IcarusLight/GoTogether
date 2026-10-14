@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" manage.py backup
if errorlevel 1 goto failed
pause
exit /b 0
:missing
echo Run setup.cmd first.
:failed
pause
exit /b 1
