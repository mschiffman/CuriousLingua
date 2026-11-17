@echo off
rem Rebuilds every page, then commits and pushes if this folder is a git repository.
cd /d "%~dp0"
python -E tools\build.py || (pause & exit /b 1)
if not exist ".git" (
  echo.
  echo Pages rebuilt. This folder is not a git repository yet, so nothing was pushed.
  echo See README.md, "Publishing".
  pause & exit /b
)
set "MSG="
set /p MSG=Commit message (Enter = "update lessons"): 
if "%MSG%"=="" set "MSG=update lessons"
git add -A
git commit -m "%MSG%"
git push
pause
