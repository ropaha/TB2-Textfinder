@echo off
setlocal
cd /d "%~dp0"
title TB2-Textfinder - EXE Builder
echo TB2-Textfinder - Windows EXE erstellen
if not exist "TB2_Textfinder.py" (
 echo FEHLER: TB2_Textfinder.py fehlt.
 pause
 exit /b 1
)
where py >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=py -3") else (set "PYTHON_CMD=python")
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
 echo Python 3.10 oder neuer erforderlich.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 %PYTHON_CMD% -m venv ".venv"
 if errorlevel 1 goto :error
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
if not exist "%~dp0logo.ico" (
 echo FEHLER: logo.ico fehlt neben dieser BAT-Datei.
 pause
 exit /b 1
)
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon "%~dp0logo.ico" --add-data "%~dp0logo.ico;." --name "TB2_Textfinder" --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0" "%~dp0TB2_Textfinder.py"
if errorlevel 1 goto :error
echo ERFOLG: dist\TB2_Textfinder.exe
explorer "%CD%\dist"
pause
exit /b 0
:error
echo Build fehlgeschlagen. Internet fuer PyInstaller-Installation erforderlich.
pause
exit /b 1
