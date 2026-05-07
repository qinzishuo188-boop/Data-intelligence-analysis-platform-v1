@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="
for %%I in (python.exe) do set "PYTHON_EXE=%%~$PATH:I"
if not defined PYTHON_EXE for %%I in (py.exe) do set "PY_LAUNCHER=%%~$PATH:I"

if not defined PYTHON_EXE if defined PY_LAUNCHER (
  "%PY_LAUNCHER%" -3 -c "import sys; print(sys.executable)" > "%TEMP%\chart_python_path.txt" 2>nul
  set /p PYTHON_EXE=<"%TEMP%\chart_python_path.txt"
  del "%TEMP%\chart_python_path.txt" >nul 2>nul
)

if not defined PYTHON_EXE (
  echo Python was not found.
  echo Please install Python 3.11 or later first.
  pause
  exit /b 1
)

echo Creating local virtual environment...
call "%PYTHON_EXE%" -m venv "%~dp0runtime\python"
if errorlevel 1 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)

echo Installing Python packages...
call "%~dp0runtime\python\Scripts\python.exe" -m pip install --upgrade pip
call "%~dp0runtime\python\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"

echo.
echo Python environment is ready.
echo If you also need PPT export on another computer, install Node.js separately.
pause
