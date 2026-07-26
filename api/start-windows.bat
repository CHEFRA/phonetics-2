@echo off
REM Start FastAPI backend (ASR inference API), listens on 0.0.0.0:8000
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000