@echo off
setlocal

REM === Always run from the folder where this .bat lives ===
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

REM === Ensure venv exists (optional safety) ===
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)

REM === Activate venv (use absolute path) ===
call ".venv\Scripts\activate"
if errorlevel 1 (
  echo Failed to activate .venv. Aborting.
  popd & endlocal & pause & exit /b 1
)

REM === Choose input/output (allow passing them as arguments) ===
set "INFILE=%~1"
if "%INFILE%"=="" set "INFILE=%SCRIPT_DIR%input.ged"
set "OUTFILE=%~2"
if "%OUTFILE%"=="" set "OUTFILE=%SCRIPT_DIR%output.md"

REM === Run the program ===
python -m genreport.cli --input "%INFILE%" --output "%OUTFILE%"

echo.
echo Done. Output saved to "%OUTFILE%"

popd
endlocal
pause
