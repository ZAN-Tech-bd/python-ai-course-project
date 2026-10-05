@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set PYLAUNCHER=py
) else (
    set PYLAUNCHER=python
)

if not exist ".venv" (
    echo Creating virtual environment in .venv ...
    %PYLAUNCHER% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python 3.9-3.12 is installed and on PATH.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

echo Installing/updating dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. See errors above.
    pause
    exit /b 1
)

echo.
echo Starting Draw in Air...
python main.py

pause
