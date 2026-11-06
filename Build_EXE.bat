@echo off
setlocal
cd /d "%~dp0"
title TB2-Textfinder - EXE erstellen

echo ============================================
echo   TB2-Textfinder - Windows-EXE erstellen
echo ============================================
echo.

REM Python Launcher bevorzugen; alternativ den Befehl "python" verwenden.
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo FEHLER: Python 3.10 oder neuer wurde nicht gefunden.
    echo Bitte Python fuer Windows installieren und danach diese BAT erneut starten.
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Erstelle eine eigene Build-Umgebung ...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

echo Aktualisiere pip ...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo Installiere PyInstaller ...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo.
echo Erstelle die EXE ...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TB2_Textfinder --distpath dist --workpath build --specpath build TB2_Textfinder.py
if errorlevel 1 goto :error

echo.
echo ============================================
echo ERFOLG!
echo Die EXE liegt hier:
echo %CD%\dist\TB2_Textfinder.exe
echo ============================================
echo.
if exist "dist\TB2_Textfinder.exe" explorer "%CD%\dist"
pause
exit /b 0

:error
echo.
echo FEHLER: Der Build konnte nicht abgeschlossen werden.
echo Pruefe die Meldungen oben. Eine Internetverbindung wird benoetigt,
echo damit PyInstaller beim ersten Lauf installiert werden kann.
echo.
pause
exit /b 1
