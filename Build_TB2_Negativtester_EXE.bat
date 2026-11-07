@echo off
setlocal
cd /d "%~dp0"
title TB2_Negativtester - EXE erstellen
echo.
echo Erstelle TB2_Negativtester.exe ...
if not exist "%~dp0TB2_Negativtester.py" (
 echo FEHLER: TB2_Negativtester.py fehlt.
 goto :error
)
if not exist "%~dp0logo.ico" (
 echo FEHLER: logo.ico fehlt.
 goto :error
)
where py >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=py -3") else (set "PYTHON_CMD=python")
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto :error
if not exist ".venv\Scripts\python.exe" (
 %PYTHON_CMD% -m venv ".venv"
 if errorlevel 1 goto :error
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error
python -m pip install -r "%~dp0requirements-build.txt"
if errorlevel 1 goto :error
REM Spec im Projektordner, damit Icon-Pfade nicht in build/ umgedeutet werden.
REM --hidden-import stellt die Finder-Abhaengigkeit des Testers sicher.
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon "%~dp0logo.ico" --add-data "%~dp0logo.ico;." --hidden-import TB2_Textfinder --name "TB2_Negativtester" --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0" "%~dp0TB2_Negativtester.py"
if errorlevel 1 goto :error
if not exist "%~dp0dist\TB2_Negativtester.exe" goto :error
echo ERFOLG: dist\TB2_Negativtester.exe
if /i "%~1"=="/nopause" exit /b 0
explorer "%~dp0dist"
pause
exit /b 0
:error
echo FEHLER: Build von TB2_Negativtester fehlgeschlagen.
if /i "%~1"=="/nopause" exit /b 1
pause
exit /b 1
