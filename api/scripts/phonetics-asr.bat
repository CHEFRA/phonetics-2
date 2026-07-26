@echo off
REM Start ASR desktop client (voice recognition + system tray), activate via global hotkey
cd /d "%~dp0.."
.venv\Scripts\python.exe desktop/asr_client.py
