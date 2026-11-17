@echo off
rem Status: lessons per level and strand, audio to record, missing pictures, things to review.
cd /d "%~dp0"
python -E tools\check.py
start "" "_reports\status.md"
pause
