@echo off
rem Audio: ElevenLabs takes, leveling, Whisper check, upload to R2. Opens a menu.
cd /d "%~dp0"
python -E tools\audio.py
pause
