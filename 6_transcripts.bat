@echo off
rem Printable transcripts (PDF) of the speaking lessons -> ^<course^>\speaking\^<lesson^>.pdf, beside the page.
rem Printed by Microsoft Edge without opening it. Then the pages are rebuilt, so each lesson shows its button.
cd /d "%~dp0"
echo   Enter      lessons whose transcript is missing or out of date
echo   all        every speaking lesson
echo   or type a lesson or a course:  fr/speaking/f013_disbelief   jap
set "PICK="
set /p PICK=Make: 
if "%PICK%"=="" set "PICK=--changed"
python -E tools\transcript.py %PICK%
pause
