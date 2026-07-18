@echo off
REM Arranca backend + banner (sin ventanas de consola)
cd /d "%~dp0"
start "" /min "%~dp0venv\Scripts\pythonw.exe" "%~dp0backend\app.py"
timeout /t 3 >nul
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
