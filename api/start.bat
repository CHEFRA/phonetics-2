@echo off
cd /d "%~dp0"
wsl -e bash -c "cd /home/lcl/data/projects/phonetics-2/api && source .venv/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000"
