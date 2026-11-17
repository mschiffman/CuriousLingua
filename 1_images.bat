@echo off
rem Pictures: Downloads -> _YOUTUBE -> img\ytstory in one go. Double-click to run.
rem Same steps as PYTHON AUTOMATIONS\_IMG\PNG to JPG\all_downloads_to_ytstory.bat; only the output
rem folder differs (this site's img\ytstory) and convert.py is the copy in tools\.
rem For images that are already named 1.png, 2.png ... (no renaming step)
rem   1. Moves the numbered PNGs in Downloads into a new folder in G:\My Drive\_YOUTUBE
rem   2. Converts them to JPGs in ytstory (80% size, Squoosh settings), same as convert_youtube.bat
rem   Other PNGs in Downloads (screenshots etc.) are left alone.
setlocal

set "DL=C:\Users\mschi\Downloads"
set "SRC_ROOT=G:\My Drive\_YOUTUBE"
set "OUT_ROOT=%~dp0img\ytstory"
set "CONVERT_PY=%~dp0tools\convert.py"

if not exist "%SRC_ROOT%\" (
    echo Can't find "%SRC_ROOT%". Is Google Drive running?
    goto end
)

rem Only PNGs that are just a number (1.png, 2.png ...) are moved, so other PNGs stay in Downloads
set COUNT=0
for /f "delims=" %%F in ('dir /b /a-d "%DL%\*.png" 2^>nul ^| findstr /r /i /x "[0-9][0-9]*\.png"') do set /a COUNT+=1
if %COUNT%==0 (
    echo No numbered PNG files ^(1.png, 2.png ...^) in "%DL%".
    goto end
)

:askfolder
echo.
set "FOLDER="
set /p "FOLDER=New _YOUTUBE folder name: "
if not defined FOLDER goto askfolder

set "NAME="
set /p "NAME=ytstory name [%FOLDER%]: "
if not defined NAME set "NAME=%FOLDER%"

set "DEST=%SRC_ROOT%\%FOLDER%"

echo.
echo %COUNT% numbered PNG file(s) in Downloads:
for /f "delims=" %%F in ('dir /b /a-d "%DL%\*.png" 2^>nul ^| findstr /r /i /x "[0-9][0-9]*\.png"') do echo   %%F
echo.
echo Move to:     "%DEST%"
if exist "%DEST%\" echo              This folder already exists. The PNGs will be added to it.
echo Convert to:  "%OUT_ROOT%\%NAME%"
if exist "%OUT_ROOT%\%NAME%\" echo              This folder already exists. JPGs with the same names may be replaced.
echo.
choice /m "Go ahead"
if errorlevel 2 goto end

echo.
echo Moving...
if not exist "%DEST%\" mkdir "%DEST%"
if not exist "%DEST%\" goto failed
set MOVED=0
for /f "delims=" %%F in ('dir /b /a-d "%DL%\*.png" 2^>nul ^| findstr /r /i /x "[0-9][0-9]*\.png"') do (
    if exist "%DEST%\%%F" (
        echo KEEP  %%F  - already in the _YOUTUBE folder, left in Downloads
    ) else (
        move "%DL%\%%F" "%DEST%\" >nul && set /a MOVED+=1
    )
)
echo Moved %MOVED% file(s) to "%DEST%".

echo.
echo Converting...
python "%CONVERT_PY%" "%DEST%" --scale 0.8 -o "%OUT_ROOT%\%NAME%"
if errorlevel 1 goto failed

echo.
echo Done. Lessons still missing pictures:
python -E "%~dp0tools\images.py"
goto end

:failed
echo.
echo Stopped - something went wrong. See the messages above.

:end
echo.
pause
endlocal
