@rem Startet tests/benchmark_resource_paths.py mit interaktiver Parameterabfrage.
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
set /p "term=Suchbegriff [Hagen]: "
if not defined term set "term=Hagen"
set /p "expected=Optionale TXT-Datei mit erwarteten Trefferpfaden (Enter = keine): "
set /p "output=CSV-Ausgabedatei [benchmark_resource_paths.csv]: "
if not defined output set "output=benchmark_resource_paths.csv"
echo.
if defined expected (
  py -3 "tests\benchmark_resource_paths.py" "%folder%" --term "%term%" --expected "%expected%" --output "%output%"
) else (
  py -3 "tests\benchmark_resource_paths.py" "%folder%" --term "%term%" --output "%output%"
)

echo.
echo Benchmark beendet. Rueckgabecode: %errorlevel%
pause
endlocal
