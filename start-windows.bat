@echo off
cd /d "%~dp0"
if not exist "backend\.env" (
  echo First complete docs\WINDOWS_SETUP.md and create backend\.env.
  pause
  exit /b 1
)
if not exist "backend\.venv\Scripts\python.exe" (
  echo Backend dependencies missing. Complete docs\WINDOWS_SETUP.md first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend dependencies missing. Run npm install inside frontend first.
  pause
  exit /b 1
)
start "Sentinel Backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "Sentinel Frontend" /D "%~dp0frontend" cmd /k "npm run dev"
echo Start MySQL in XAMPP and make sure Ollama is running.
echo Open http://127.0.0.1:5173 after Vite reports ready.
pause
