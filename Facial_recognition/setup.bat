@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set PYLAUNCHER=py -3
) else (
    set PYLAUNCHER=python
)

echo Creating virtual environment in .venv ...
%PYLAUNCHER% -m venv .venv
if not exist ".venv\Scripts\activate.bat" (
    echo Failed to create virtual environment. Make sure Python 3 is installed and on PATH.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete. Run run.bat to start face detection.
pause
