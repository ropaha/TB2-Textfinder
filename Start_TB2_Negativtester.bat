@echo off
cd /d "%~dp0"
py -3 TB2_Negativtester.py
if errorlevel 1 (
  echo.
  echo Das Programm konnte nicht gestartet werden.
  echo Bitte pruefe, ob Python 3 installiert ist.
  pause
)
