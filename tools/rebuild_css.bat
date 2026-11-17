@echo off
rem Only needed after changing the page shells in tools\build.py or assets\js\site.js (needs Node).
cd /d "%~dp0.."
npx --yes tailwindcss@3.4.17 -c tools\tailwind.config.js -i tools\site.src.css -o assets\css\site.css --minify
pause
