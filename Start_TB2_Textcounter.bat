@echo off
setlocal
cd /d "%~dp0"
title TB2-Textcounter

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0TB2_Textcounter.py"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto :no_python
    python "%~dp0TB2_Textcounter.py"
)
if errorlevel 1 goto :error
exit /b 0

:no_python
echo FEHLER: Python 3 wurde nicht gefunden.
echo Bitte Python 3 installieren oder den Python-Pfad pruefen.
goto :pause_error

:error
echo FEHLER: TB2_Textcounter.py konnte nicht gestartet werden.
:pause_error
echo.
pause
exit /b 1
