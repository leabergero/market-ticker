@echo off
REM Compilador e instalador para Windows

echo Building Ticker Widget for Windows...

set PROJECT_DIR=%~dp0..
set BUILD_DIR=%PROJECT_DIR%\dist
set BACKEND_DIR=%PROJECT_DIR%\backend
set FRONTEND_DIR=%PROJECT_DIR%\frontend

REM Limpiar build anterior
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

REM Backend
echo Packaging backend...
xcopy /E /I "%BACKEND_DIR%" "%BUILD_DIR%\backend"
xcopy /E /I "%PROJECT_DIR%\config" "%BUILD_DIR%\config"

REM Frontend
echo Packaging frontend...
python -m venv "%BUILD_DIR%\venv"
call "%BUILD_DIR%\venv\Scripts\activate.bat"
pip install --upgrade pip
pip install -r "%FRONTEND_DIR%\requirements.txt"
pip install -r "%BACKEND_DIR%\requirements.txt"
copy "%FRONTEND_DIR%\main.py" "%BUILD_DIR%\main.py"

REM PyInstaller para crear ejecutable
echo Building executable...
pyinstaller --onefile --windowed ^
  --add-data "%BUILD_DIR%\backend;backend" ^
  --add-data "%BUILD_DIR%\config;config" ^
  "%BUILD_DIR%\main.py"

REM Script de inicio
(
  echo @echo off
  echo cd "%%~dp0"
  echo start "" "venv\Scripts\python.exe" backend\app.py
  echo timeout /t 2
  echo start "" "dist\main.exe"
) > "%BUILD_DIR%\run.bat"

echo Build complete!
echo Output: %BUILD_DIR%
echo To run: %BUILD_DIR%\run.bat
pause
