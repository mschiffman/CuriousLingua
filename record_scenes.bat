@echo off
rem Records a dialogue scene by scene (the two voices play each scene together), levels each scene,
rem cuts it into the lesson's clips, checks them and offers to upload. It asks before using any ElevenLabs characters.
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -E tools\scene.py %*
:again
echo.
choice /c YN /n /m "Is there another project to process? (Y/N) "
if errorlevel 2 goto done
echo.
python -E tools\scene.py
goto again
:done
pause
