@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=py -3") else (set "PYTHON_CMD=python")
%PYTHON_CMD% tools\build.py negativtester --local
if errorlevel 1 goto :error
if /i "%~1"=="/nopause" exit /b 0
explorer "%~dp0dist"
pause
exit /b 0
:error
echo FEHLER: Build fehlgeschlagen.
if /i "%~1"=="/nopause" exit /b 1
pause
exit /b 1
