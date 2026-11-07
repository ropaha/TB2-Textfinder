@echo off
setlocal
cd /d "%~dp0"
title TB2 - Beide EXE-Dateien erstellen
echo ============================================
echo  TB2 Finder und Negativtester - EXE Build
echo ============================================
echo.
call "%~dp0Build_TB2_Textfinder_EXE.bat" /nopause
if errorlevel 1 goto :error
call "%~dp0Build_TB2_Negativtester_EXE.bat" /nopause
if errorlevel 1 goto :error
echo.
echo Beide EXE-Dateien erfolgreich erstellt:
echo   dist\TB2_Textfinder.exe
echo   dist\TB2_Negativtester.exe
explorer "%~dp0dist"
pause
exit /b 0
:error
echo.
echo FEHLER: Mindestens ein Build ist fehlgeschlagen.
pause
exit /b 1
