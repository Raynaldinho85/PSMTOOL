@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=.venv\Scripts\python.exe"
set "APP_PATH=src/psm_tool/ui/app.py"
set "APP_HOST=127.0.0.1"
set "APP_PORT=8501"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found at "%PYTHON_EXE%".
    echo Create it with:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e .[dev]
    exit /b 1
)

echo Starting PSM Tool on http://%APP_HOST%:%APP_PORT%
echo Press Ctrl+C to stop.
echo.

"%PYTHON_EXE%" -m streamlit run "%APP_PATH%" ^
  --server.address "%APP_HOST%" ^
  --server.port "%APP_PORT%" ^
  --server.headless true ^
  --browser.gatherUsageStats false

exit /b %errorlevel%
