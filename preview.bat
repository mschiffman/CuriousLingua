@echo off
rem Opens the site in the browser from this folder (http://localhost:8000). Close this window to stop.
cd /d "%~dp0"
python -E tools\build.py
start "" http://localhost:8000/
python -m http.server 8000
