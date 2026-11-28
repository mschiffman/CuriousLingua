@echo off
rem Grammar chapters (scenes, rule, mistakes, practice, quiz): writes <course>\grammar\<slug>.html from the lesson file
cd /d "%~dp0"
python -E tools\grammar_chapter.py
pause
