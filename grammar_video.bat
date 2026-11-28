@echo off
rem Reel files for the grammar chapters: joins each scene's recorded clips and writes its captions and script
rem into G:\My Drive\_VIDEO\<course>-<slug>\, ready for make_video.bat. Uses no ElevenLabs characters.
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -E tools\chapter_video.py %*
pause
