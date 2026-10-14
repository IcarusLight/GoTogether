@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:usepython
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" manage.py setup
if errorlevel 1 goto failed
echo Setup complete. Run start.cmd to start the website.
pause
exit /b 0
:failed
echo Setup failed. Check the message above. Python 3.11 or newer is required.
pause
exit /b 1
