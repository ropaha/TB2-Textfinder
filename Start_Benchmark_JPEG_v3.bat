@rem Startet tests/benchmark_jpeg_v3.py mit interaktiver Parameterabfrage.
@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
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
echo Die eingebauten Standard-Suchbegriffe werden immer mitgeprueft.
set /p "termsfile=Optionale UTF-8-Datei mit Suchbegriffen (Enter = keine): "
set /p "term=Zusaetzlicher Suchbegriff (Enter = keiner): "
set /p "case=Gross-/Kleinschreibung beachten? (J/N) [N]: "
set /p "maxfiles=Maximale Dateianzahl (0 = alle) [0]: "
if not defined maxfiles set "maxfiles=0"
echo.
if defined termsfile (
  if defined term (
    if /i "%case%"=="J" (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --terms-file "%termsfile%" --term "%term%" --case-sensitive --max-files "%maxfiles%"
    ) else (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --terms-file "%termsfile%" --term "%term%" --max-files "%maxfiles%"
    )
  ) else (
    if /i "%case%"=="J" (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --terms-file "%termsfile%" --case-sensitive --max-files "%maxfiles%"
    ) else (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --terms-file "%termsfile%" --max-files "%maxfiles%"
    )
  )
) else (
  if defined term (
    if /i "%case%"=="J" (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --term "%term%" --case-sensitive --max-files "%maxfiles%"
    ) else (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --term "%term%" --max-files "%maxfiles%"
    )
  ) else (
    if /i "%case%"=="J" (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --case-sensitive --max-files "%maxfiles%"
    ) else (
      py -3 "tests\benchmark_jpeg_v3.py" "%folder%" --max-files "%maxfiles%"
    )
  )
)

echo.
echo Benchmark beendet. Rueckgabecode: %errorlevel%
pause
endlocal
