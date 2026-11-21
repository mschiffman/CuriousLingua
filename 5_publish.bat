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
rem The website is built from the main branch only: publishing from any other branch never reaches it.
set "BR="
for /f "delims=" %%b in ('git branch --show-current') do set "BR=%%b"
if /i not "%BR%"=="main" (
  echo.
  echo NOT PUBLISHED: you are on branch "%BR%", but the website only shows "main".
  echo Switch first with:  git switch main
  pause & exit /b 1
)
set "MSG="
set /p MSG=Commit message (Enter = "update lessons"):
if "%MSG%"=="" set "MSG=update lessons"
git add -A
git commit -m "%MSG%"
git push origin main || (
  echo.
  echo PUSH FAILED: the website was NOT updated. Read the message above.
  pause & exit /b 1
)
echo.
echo Pushed to main. Cloudflare usually shows the change within a minute or two.
pause
