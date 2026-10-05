@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    rem MediaPipe needs Python 3.9-3.12, so prefer one of those over the default Python.
    set PYLAUNCHER=
    for %%v in (3.12 3.11 3.10 3.9) do (
        if not defined PYLAUNCHER (
            py -%%v -c "" >nul 2>nul && set PYLAUNCHER=py -%%v
        )
    )
    if not defined PYLAUNCHER set PYLAUNCHER=python
    echo Creating virtual environment in .venv ...
    call %%PYLAUNCHER%% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python 3.9-3.12 is installed.
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
echo Starting Ice Cream Catch...
python main.py %*

pause
