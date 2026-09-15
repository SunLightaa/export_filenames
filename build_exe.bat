@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

"%PYTHON%" -m pip install -r requirements.txt
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "export_filenames" export_filenames.py

echo.
echo 打包完成：dist\export_filenames.exe
pause
