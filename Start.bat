@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if exist "dist\苍岚笺.exe" (
    start "" "dist\苍岚笺.exe"
    exit /b 0
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "run.py"
    exit /b 0
)
echo Please create the virtual environment first. See README.md.
pause
exit /b 1
