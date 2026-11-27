@echo off
rem Run once: gives the .md scripts beside the speaking lessons the same names as their lesson files.
rem Safe to run twice (a script already renamed is skipped). Delete this file afterwards.
cd /d "%~dp0"
if exist "content\fr\speaking\ca_va_pas.md" ren "content\fr\speaking\ca_va_pas.md" "f008_whats_wrong.md"
if exist "content\fr\speaking\cest_pas_vrai.md" ren "content\fr\speaking\cest_pas_vrai.md" "f015_disbelief_2.md"
if exist "content\fr\speaking\faire_le_marche.md" ren "content\fr\speaking\faire_le_marche.md" "f010_market_shopping.md"
if exist "content\fr\speaking\je_suis_malade.md" ren "content\fr\speaking\je_suis_malade.md" "f011_not_feeling_well.md"
if exist "content\fr\speaking\quelle_heure_fr.md" ren "content\fr\speaking\quelle_heure_fr.md" "f004_time.md"
if exist "content\eng\speaking\at_the_market.md" ren "content\eng\speaking\at_the_market.md" "e010_market_shopping.md"
if exist "content\eng\speaking\not_feeling_well.md" ren "content\eng\speaking\not_feeling_well.md" "e011_not_feeling_well.md"
if exist "content\eng\speaking\what_time.md" ren "content\eng\speaking\what_time.md" "e004_time.md"
if exist "content\eng\speaking\youre_kidding.md" ren "content\eng\speaking\youre_kidding.md" "e015_disbelief_2.md"
if exist "content\jap\speaking\hello_goodbye.md" ren "content\jap\speaking\hello_goodbye.md" "j006_greet_goodbye.md"
if exist "content\jap\speaking\not_feeling_well.md" ren "content\jap\speaking\not_feeling_well.md" "j011_not_feeling_well.md"
if exist "content\jap\speaking\not_feeling_well_en.md" ren "content\jap\speaking\not_feeling_well_en.md" "j011_not_feeling_well_en.md"
if exist "content\spa\speaking\hola.md" ren "content\spa\speaking\hola.md" "s006_greet_goodbye.md"
if exist "content\spa\speaking\me_siento_mal.md" ren "content\spa\speaking\me_siento_mal.md" "s011_not_feeling_well.md"
echo Done.
pause
