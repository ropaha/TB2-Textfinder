@rem Startet tests/benchmark_jpeg_v2.py mit interaktiver Parameterabfrage.
@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0.."
where py >nul 2>&1
if errorlevel 1 (
  echo Python-Launcher "py" wurde nicht gefunden.
  pause
  exit /b 1
)
echo.
set /p "folder=TB2/TBL-Suchordner (Pflicht): "
if not defined folder (
  echo Kein Ordner angegeben.
  pause
  exit /b 1
)
if not exist "%folder%\." (
  echo Ordner nicht gefunden: "%folder%"
  pause
  exit /b 1
)
set /p "term=Suchbegriff [Gerken]: "
if not defined term set "term=Gerken"
set /p "limit=Profil-Limit (0 = aus) [100]: "
if not defined limit set "limit=100"
echo.
py -3 "tests\benchmark_jpeg_v2.py" "%folder%" --term "%term%" --profile-limit "%limit%"

echo.
echo Benchmark beendet. Rueckgabecode: %errorlevel%
pause
endlocal
