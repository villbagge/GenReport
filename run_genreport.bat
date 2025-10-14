@echo off
setlocal

REM === Project base paths ===
set "BASEDIR=C:\GIT\GenReport\GenReport"
set "GEDFILE=%BASEDIR%\input.ged"
set "OUTDIR=%BASEDIR%"

REM === Switch to the project folder ===
pushd "%BASEDIR%"

REM === Ensure virtual environment exists ===
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv 2>nul || python -m venv .venv
)

REM === Activate the virtual environment ===
call ".venv\Scripts\activate"
if errorlevel 1 (
    echo Failed to activate virtual environment.
    popd & endlocal & pause & exit /b 1
)

REM === Ensure the package is installed in editable mode ===
if not exist ".venv\Lib\site-packages\genreport.egg-link" (
    echo Installing package in editable mode...
    pip install -e . >nul
)

REM === Run the report ===
echo Running GenReport...
python -m genreport.cli --input "%GEDFILE%" --outdir "%OUTDIR%"

echo.
echo Done. Output written to "%OUTDIR%"
echo.
pause

REM === Clean up ===
popd
endlocal
