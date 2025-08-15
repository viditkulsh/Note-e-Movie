@echo off
echo Starting Note-E-Movie - Personal Entertainment Library...
echo.

:: Check if required packages are installed
python -c "import PySide6, pandas, openpyxl, numpy" 2>NUL
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install packages
        pause
        exit /b 1
    )
)

:: Run the application
echo Launching Note-E-Movie...
python note_e_movie.py

if errorlevel 1 (
    echo.
    echo Error: Application failed to start
    echo Check note_e_movie.log for details
    pause
)
