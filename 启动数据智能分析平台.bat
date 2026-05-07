@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PORTABLE_PYTHON=%~dp0runtime\python\python.exe"
set "VENV_PYTHON=%~dp0runtime\python\Scripts\python.exe"
set "PYTHON_EXE=%PORTABLE_PYTHON%"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%VENV_PYTHON%"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE="
if not defined PYTHON_EXE for %%I in (python.exe) do set "PYTHON_EXE=%%~$PATH:I"
if not defined PYTHON_EXE for %%I in (py.exe) do set "PY_LAUNCHER=%%~$PATH:I"

if not defined PYTHON_EXE if defined PY_LAUNCHER (
  "%PY_LAUNCHER%" -3 -c "import sys; print(sys.executable)" > "%TEMP%\chart_python_path.txt" 2>nul
  set /p PYTHON_EXE=<"%TEMP%\chart_python_path.txt"
  del "%TEMP%\chart_python_path.txt" >nul 2>nul
)

if not defined PYTHON_EXE (
  echo Python was not found.
  echo Please install Python 3.11 or later first.
  echo Or run:
  echo %~dp0first_setup.bat
  echo.
  pause
  exit /b 1
)

if defined PYTHON_EXE (
  call "%PYTHON_EXE%" -c "import pandas" >nul 2>nul
  if errorlevel 1 (
    echo Installing missing Python packages...
    call "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
      echo Failed to install required Python packages.
      pause
      exit /b 1
    )
  )
)

title Chart Launcher
echo Starting chart platform...
echo URL: http://127.0.0.1:8866
echo Keep this window open while using the app.
echo.

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8866 .*LISTENING"') do (
  taskkill /PID %%P /F >nul 2>nul
)

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8866'"
call "%PYTHON_EXE%" "%~dp0start_platform.py"

echo.
echo The platform stopped or failed to start.
pause
