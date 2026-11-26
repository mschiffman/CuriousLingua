@echo off
rem Pitch check: draws the pitch of a lesson's clips beside the same lines read by AivisSpeech, and opens the report.
rem Open AivisSpeech first for the reference. Nothing is recorded and no lesson file is changed.
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -E tools\pitch.py %* --open
pause
