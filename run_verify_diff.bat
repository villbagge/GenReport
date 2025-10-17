@echo off
setlocal
REM Usage: run_verify_diff.bat v0.4.0 C:\GIT\GenReport\GenReport\input.ged 1

if "%~1"=="" (
  echo Usage: %~nx0 BASELINE_REF [GED_PATH] [ROOTNUM]
  echo Example: %~nx0 v0.4.0 C:\GIT\GenReport\GenReport\input.ged 1
  exit /b 2
)

set BASELINE=%~1
set GED=%~2
if "%GED%"=="" set GED=C:\GIT\GenReport\GenReport\input.ged
set ROOT=%~3
if "%ROOT%"=="" set ROOT=1

echo Running verify_diff against %BASELINE% ...
python tools\verify_diff.py --baseline %BASELINE% --ged "%GED%" --root %ROOT% --outdir tools
set RC=%ERRORLEVEL%

if %RC%==0 (
  echo.
  echo RESULT: seems ok
) else (
  echo.
  echo RESULT: bad changes detected
)
pause
exit /b %RC%
