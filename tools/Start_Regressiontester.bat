@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0Signum_Regressiontester.py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 wurde nicht gefunden.
        echo Bitte Python 3 installieren und zum PATH hinzufuegen.
        pause
        exit /b 1
    )
    python "%~dp0Signum_Regressiontester.py"
)
if errorlevel 1 (
    echo.
    echo Der Regressionstester wurde mit einem Fehler beendet.
    pause
)
endlocal
