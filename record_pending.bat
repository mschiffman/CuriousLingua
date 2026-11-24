@echo off
rem Records, checks and uploads every card page and dialogue whose audio is still pending.
rem It lists them and asks before using any ElevenLabs characters.
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -E tools\pending.py
pause
