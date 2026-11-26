@echo off
cd /d "%~dp0"
set "VAULT=G:\My Drive\OBSIDIAN\LANGSITE"
if not exist "%VAULT%" mkdir "%VAULT%"
copy /y README.md "%VAULT%\LANGSITE README.md" >nul
copy /y COMMANDS.md "%VAULT%\LANGSITE COMMANDS.md" >nul
echo Copied README.md and COMMANDS.md to %VAULT%
pause