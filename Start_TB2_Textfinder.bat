@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0TB2_Textfinder.py"
) else (
    python "%~dp0TB2_Textfinder.py"
)

if errorlevel 1 (
    echo.
    echo Das Programm konnte nicht gestartet werden.
    echo Bitte Python 3.10 oder neuer mit Tkinter installieren.
    pause
)
