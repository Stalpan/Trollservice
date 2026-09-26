@echo off
cd /d "%~dp0"
echo Starting Trollservice on http://127.0.0.1:5000  (Ctrl+C to stop)
.venv\Scripts\python.exe app.py
pause
