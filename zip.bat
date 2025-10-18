@echo off
setlocal EnableExtensions

REM ── Derive project name from current folder
for %%I in ("%CD%") do set "PROJECT=%%~nxI"

REM ── Timestamp (yyyyMMdd-HHmmss) via PowerShell (locale-safe)
for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyyMMdd-HHmmss\")"') do set "STAMP=%%I"

REM ── Output dir and filename (optional label as %1)
set "OUTDIR=%CD%\releases"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
set "LABEL=%~1"
if defined LABEL (
  set "ZIP=%OUTDIR%\%PROJECT%-%STAMP%-%LABEL%.zip"
) else (
  set "ZIP=%OUTDIR%\%PROJECT%-%STAMP%.zip"
)

echo Creating: "%ZIP%"
echo.

REM ── Prefer bsdtar (Windows 10+), with excludes
tar --version >nul 2>&1
if %errorlevel%==0 (
  tar -a -c -f "%ZIP%" ^
    --exclude=.git --exclude=.git\* ^
    --exclude=venv --exclude=venv\* ^
    --exclude=.venv --exclude=.venv\* ^
    --exclude=__pycache__ --exclude=**\__pycache__\* ^
    --exclude=.pytest_cache --exclude=**\.pytest_cache\* ^
    --exclude=.mypy_cache --exclude=**\.mypy_cache\* ^
    --exclude=.coverage --exclude=**\.coverage\* ^
    --exclude=*.zip --exclude=releases\* ^
    --exclude=.idea --exclude=.vscode ^
    *
  if %errorlevel%==0 goto :done
  echo tar failed, falling back to PowerShell...
  echo.
)

REM ── Fallback: PowerShell Compress-Archive with robust path filtering
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$zip = '%ZIP%';" ^
  "$files = Get-ChildItem -Recurse -File -Force | Where-Object {" ^
  "  $_.FullName -notmatch '\\\\.git(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\(venv|\\.venv)(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\__pycache__(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\.pytest_cache(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\.mypy_cache(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\releases(\\\\|$)' -and" ^
  "  $_.FullName -notmatch '\\\\(.idea|.vscode)(\\\\|$)' -and" ^
  "  $_.Extension -ne '.zip' };" ^
  "if (Test-Path $zip) { Remove-Item $zip -Force };" ^
  "Compress-Archive -Path $files -DestinationPath $zip -CompressionLevel Optimal -Force;" ^
  "Write-Host 'Created' $zip"

:done
echo.
echo Done! Created: "%ZIP%"
endlocal
