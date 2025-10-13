@echo off
REM === activate the virtual environment ===
call .venv\Scripts\activate

REM === run the program ===
python -m genreport.cli --input "%~dp0input.ged" --output "%~dp0output.txt"

REM === pause so you can see the result ===
echo.
echo Done. Output saved to output.txt
pause
