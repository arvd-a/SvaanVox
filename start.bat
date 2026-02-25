@echo off
echo ==================================================
echo   Starting SvaanVox v2 (with GPU Acceleration)
echo ==================================================
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please wait for the setup to finish.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python app.py
pause
