@echo off
rem Offline single-file lessons (fonts, pictures and audio inside) -> <course>\single\
cd /d "%~dp0"
echo   Enter      lessons whose offline copy is missing or out of date
echo   all        every lesson
echo   or type a lesson, a strand or a course:  fr/expressions/greetings   eng/reading   jap
set "PICK="
set /p PICK=Build: 
if "%PICK%"=="" set "PICK=--changed"
python -E tools\offline.py %PICK%
pause
