@echo off
rem Run once. Unpacks the site here, then copies your pictures and audio from the old LANGUAGES folder.
rem The old folder is only read, never changed. Safe to run again: it only copies what is missing.
setlocal
cd /d "%~dp0"
set "SRC=C:\Users\mschi\OneDrive\Desktop\LANGUAGES"
if exist site.zip (
  echo 1/3  Unpacking the site...
  tar -xf site.zip || (echo Could not unpack site.zip & pause & exit /b 1)
)
if not exist "%SRC%\media" (echo Cannot find %SRC% - edit SRC at the top of this file. & pause & exit /b 1)
echo 2/3  Copying img and media from %SRC%  (about 3 GB, a few minutes)...
robocopy "%SRC%\img" "%~dp0img" /E /R:1 /W:1 /NFL /NDL /NJH /MT:8
robocopy "%SRC%\media" "%~dp0media" /E /XD "%SRC%\media\rfi" "%SRC%\media\lessons\pimsleur" "%SRC%\media\lessons\korean" /XF *.py /R:1 /W:1 /NFL /NDL /NJH /MT:8
echo 3/3  Building the pages...
python -E tools\build.py
python -E tools\check.py
echo.
echo Done. Double-click preview.bat to look at the site.
pause
