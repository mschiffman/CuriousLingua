# LANGSITE

One site, five courses: **French** (adults, A1–B2), **English** (children in Myanmar, Starter–B2), **Japanese** (speaking only, A1–B2, English and Burmese support), **Korean** (speaking first, with Hangul beside the romanization, A1–B2; it mirrors the Japanese course lesson for lesson), **Spanish** (Latin American, Mexican usage; speaking and expressions only, A1–B2, English support; folder `spa`).

## The one rule

Lessons are the `.json` files in `content\`. Every `.html` page is generated from them by `tools\build.py`. Edit the lesson file, never the page.

```
content\<course>\<strand>\<slug>.json   ->   <course>\<strand>\<slug>.html
content\fr\expressions\greetings.json   ->   fr\expressions\greetings.html
```

Courses: `fr`, `eng`, `jap`, `kor`. Strands, level names and course texts are in `site.json`. A course may give a strand its own line of description with `"strand_text": { "sounds": "..." }`.

## The .bat files

| File | What it does |
|---|---|
| `SETUP.bat` | Run once: unpacks the site and copies `img\` and `media\` from the old LANGUAGES folder (read only) |
| `preview.bat` | Rebuilds and opens the site at http://localhost:8000 |
| `1_images.bat` | Same as your `all_downloads_to_ytstory.bat`: moves the numbered PNGs from Downloads to `G:\My Drive\_YOUTUBE\<folder>`, converts them at 80% size with Squoosh settings (MozJPEG, quality 75) into `img\ytstory\<name>` here |
| `2_audio.bat` | Menu: ElevenLabs balance, lessons needing clips, make one or all, new takes, Whisper check, upload to R2 |
| `record_pending.bat` | Every card page and dialogue still waiting for audio, in one go: lists them, asks, records the missing clips, waits for you, uploads |
| `pitch.bat` | Japanese only: draws the pitch of a lesson's clips beside the same lines read by AivisSpeech (open it first) and marks the lines to listen to. Report in `_reports\pitch\`. Details in `COMMANDS.md` |
| `3_offline.bat` | Builds the single-file offline lessons in `<course>\single\`. A course's `offline_url` in `site.json` is the shared folder its pages point to. They are shared on the Google Drive shared drive; the website offers no downloads |
| `4_check.bat` | Status report: counts per level and strand, audio to record, missing pictures, things to review |
| `6_transcripts.bat` | Makes the printable transcript (PDF) of each speaking lesson, beside its page. See "Transcripts" |
| `5_publish.bat` | Rebuilds every page; commits and pushes when the folder is a git repository |

## Lesson types

Every lesson file has `title`, `level` (`pre-a1` `a1` `a2` `b1` `b2` `c1`), `topic` (the heading it sits under on the strand page), `type`, and the audio wire: `aud_dir` and `aud_ext`. Optional: `subtitle`, `intro`, `order`, `notes`, `focus`, `register`, `review` (a note to yourself; shows in the status report).

| `type` | Used for | Data |
|---|---|---|
| `cards` | Expression flashcards (the dark blue design) | `categories` and optional `quiz`, same format as the old expression pages |
| `reader` | Picture readers, picture vocabulary | `img_dir`, `pages` (same format as the old story pages), optional `translation` + `tr` lines |
| `dialogue` | Speaking, listening, Japanese phrases | `lines` (or `sections` of lines), optional `speakers`, `support` |
| `shadow` | Shadowing practice | `chunks`: `{ "text": "...", "tr": "..." }`, or parts of another lesson's clips: `{ "text": "...", "clip": 3, "t": [start, end] }` (see Audio wire) |
| `text` | Reading texts for adults (French) | `img`, `paragraphs`: lists of sentences `{ "text", "tr", "gloss": { "word": ["/IPA/", "meaning", "base form /IPA/"] } }`. See `content\fr\reading\amber.json` |
| `practice` | Exercise pages and video | `blocks`, each with a `kind`: `truefalse`, `choice`, `cloze`, `open`, `order` or `video`. See `content\fr\reading\amber_exercises.json` |
| | More in a `practice` block | `slides` (a list of pictures to page through) and `picture` (`src`, `seconds`: a picture to memorise, hidden when the time is up) are block kinds too. Any block may have `"audio"` (a recording under the media base, or a list of `{ "label", "src" }`; on an `open` block it appears with the answers) and `"transcript"`. A `cloze` item with `"n"` gets a play button for clip `n` (dictation); a `choice` or `listen` item may have `"why"`, shown after Check. See `content\fr\vocabulary\marche_listening.json` |
| `words` | Themed word lists (French vocabulary) | optional opening picture `img` + `img_alt`; a built-in Quiz (hear a word, choose it; `"listen_pick": "fr"` shows spellings instead of meanings); `groups`: `{ "title", optional "sub", "notes": [...], "audio" (a clip for the heading), "words": [ { "fr", "g": "m" or "f", "ipa", "en", "audio": "volcan.mp3" } ] }`. Each word's `audio` is a named file in `glossary_dir` (`maison.mp3`); `python -E tools\audio.py words <lesson>` records the ones that are missing and writes the names in. For Japanese sound lessons `fr` holds the romaji, `ipa` the kana, and `say` what the voice reads (kana, or kanji where a kana word was misread); clips are numbered (`001.mp3`), and `"voices": [id, id]` gives each group of words to the next voice in turn. See `content\fr\vocabulary\landforms.json` |
| `hotspots` | Pictures with tappable dots, with a quiz mode | `slides`: `{ "img", "alt", "spots": [ { "x", "y" (percent from the left and top), "fr", "g", "ipa", "en", "audio" } ] }`. Usually a supplement of a word list. See `content\fr\vocabulary\landforms_hotspots.json` |
| `grammar` | Grammar notes (the French tenses) | `sections`: `{ "title", "blocks": [...] }`. A block may have `label`, `title`, `formula`, `text`, `points`, `examples` (`{ "fr", "en" }`), `table` (`{ "head", "rows" }`) and `note`. In any of these, `**...**` marks the form to notice, `*...*` is italic. No audio. See `content\fr\grammar\imparfait.json` |
| `timeline` | The tenses on one line, with a slider | `verbs`, and `tenses`: `{ "key", "name", "en", "x" (percent along the line), "dy" (pixels above or below it), "up" (label above), "span" (`[from, to]` in percent: a bar through the point, for a tense that lasts), "stem" (`[from, to]` in pixels from the line: a dashed line to a point off the line), "mood", "hint", "use", "structure", "forms": { "<verb>": ["the form", "a line under it"] }, "examples", "lesson" (the lesson its button opens) }`. See `content\fr\grammar\tenses.json` |
| `family` | A family tree where every word depends on who « moi » is, with a slider and a quiz | `people`: `{ "id", "name", "g": "m" or "f", "row" (generation, 1 at the top), "x" (place along the row, in card widths), "parents": [id, id] }`; `couples`: `[[id, id]]`; `start` (who is « moi » at first); `stages`: `{ "fr", "en" }`, what the slider names, ring by ring; `terms`: the words, keyed by link and gender (`"uncle_f": { "fr": "tante", "ipa", "en", "stage": 3 }`). The page works out who is what for whom, so a new person only needs `parents` or a line in `couples`. Give a term `"audio": "tante.mp3"` (a file in `glossary_dir`) and it is played. See `content\fr\vocabulary\famille.json` |
| `link` | A supplement kept somewhere else, such as a mind map on Google Drive | `href`: the address. Its tile opens it in a new tab; no page is built |
| `page` | A hand-made page shown as a supplement (the mind maps) | None. Like `game`: you keep `<course>\<strand>\<slug>.html` yourself and the build only links to it |
| `game` | Hand-made interactive pages (the 3D preposition quiz) | None. The build lists it but does **not** generate the page: you keep `<course>\<strand>\<slug>.html` yourself, next to anything it loads. Optional `clips`: a list of sentences the page plays, recorded and uploaded by the audio tool like any lesson (`01.mp3`, `02.mp3` …). After an upload, copy the lesson's new `aud_ext` into the page by hand (in `wheres_the_ball.html`, the `CLIPS` line). `tools\offline.py` writes small copies of those clips to `<slug>_audio\` beside the page; the page plays them first, so it works without internet. See `content\eng\grammar\wheres_the_ball.json` |

**Supplements.** A lesson file with `"supplement_of": "amber"` is not listed on its own: it appears in a "Supplemental section" at the bottom of that lesson (same folder). `label` is the chip shown on its tile.

**Related lessons.** `"related": ["fr/vocabulary/marche", "fr/speaking/f001_bakery"]` pairs a lesson with others (any strand; `course/strand/slug`). Write it in one of them only. The lessons form a group, and every lesson of the group shows all the others (a lesson that names a member of a group joins it), in a "Goes with this lesson" section (a row of buttons at the end of a picture story, a line of links under expression flashcards). The build says so when a name does not exist.

**The standard quiz set of a reading text.** Every reading text gets the same two supplements; `content\fr\reading\geothermal_exercises.json` and `geothermal_cloze.json` are the model to copy. Instructions to the learner are in French with *vous*; `label`, `intro` and `review` stay in English.

- `<slug>_exercises.json`: title `<Short title> : exercices`, subtitle `Cinq exercices sur le texte`, label `Exercises`, five blocks in this order and with these titles:
  1. `truefalse`, "1. Vrai ou faux": 6 statements, 3 true and 3 false, each settled by one sentence of the text; a false one changes one fact (a number, a place, a cause).
  2. `choice`, "2. Questions à choix multiples": 5 questions, 3 options each, the right answer not always in the same place; `"why"` quotes the sentence of the text that settles it, in « ».
  3. `cloze`, "3. Complétez les phrases": 6 sentences taken from the text (shortened if long), one content word missing, one from each part of the text.
  4. `open`, "4. Questions ouvertes": 5 questions with a `"model"` answer. The first is always "Sans regarder le texte, résumez-le en trois phrases."; the last is a personal question whose model is "Réponse libre.". The `"note"` is the same on every page.
  5. `order`, "5. Remettez dans l’ordre": 5 events or ideas, listed in `items` in the right order (the order of the story, or of the text when it tells no story; say which in `"intro"`), each a short phrase that cannot fit in two places; `"start"` is the shuffled order they are shown in.
- `<slug>_cloze.json`: title `<Short title> : texte à trous`, subtitle `Complétez avec le nom, le verbe ou l’adjectif qui manque`, label `Cloze test`, the same `intro` as the model, one `cloze` block of 12 **new** everyday sentences, each using one word of the lesson's glossary (a mix of nouns, verbs and adjectives, in the form the sentence needs) and with its English in `"tr"`. No word is used on both pages.

Only one answer may be right for each blank, and nothing may be asked that the text does not say. A page written by a model carries `"review": "Written by Claude from the lesson text. Check the French and the answers before using it with learners."` until you have read it.

**File names** use underscores, not dashes: `amber_cloze.json`, `video_amber.json`. To rename a lesson, save it under the new name and replace the old file's content with `{"retired": true}`; the next build deletes the old file and its pages.

**Speaking lessons: numbers and short addresses.** A speaking lesson is named `<letter><number>_<scene>.json`: `f013_disbelief.json`, `e013_disbelief.json`. The letter is the course (`f` French, `e` English, `j` Japanese, `k` Korean, `s` Spanish). The number names what the lesson teaches, not its script: the lessons that teach the same thing share it in every course, each with its own conversation, and a number is never used again or changed. The scene name is in English and the same in every course. The next free number is one more than the highest in use (all courses together).

Three lines in the lesson file go with the name:

- `"code": "F13"`: the short address shown in the videos. The build writes `f13.html` and `f013.html` at the top of the site, so `curiouslingua.com/f13` opens the lesson. It says so when two lessons have the same code.
- `"scene": 13`: the number alone.
- `"was": ["jy_crois_pas"]`: the names the file had before. Each old address forwards to the lesson, so links already given out go on working. When you rename a lesson, add its old name here. Take a name out and the next build no longer writes its forwarding page (delete the old `.html` by hand).

`topic` is the heading a lesson sits under on the Speaking page: Greetings and politeness, Shops and food, Getting around, Time, Health, Opinions, Reactions. Give a new heading only when a third lesson needs it. `aud_dir` keeps the folder the clips were recorded in, whatever the lesson is called now.

**What the numbers do on the pages.** A lesson with a `code` shows it as a chip on its tile and on its own page. A lesson page opens with a box under its introduction: "Goes with this lesson" (the lessons paired with it by `related`) and "This lesson in other languages" (the lessons of the other courses with the same `scene`, found by the build: nothing to write). The Speaking page of each course has a search box and level buttons. The box looks through each lesson's number, title, subtitle, heading, level, scene titles, `notes` and `"keywords": ["..."]` (words you add when a lesson should be found by a word that is nowhere else in it); not through the lines of the dialogue, or everyday words would find every lesson. Accents, capitals and apostrophes do not matter (`ca va`, `daccord`). Enter opens the lesson when one is left, and `fr/speaking/index.html?q=f13` opens the page with the box filled in. To give another strand a search box, name the strands in `site.json`: `"search": ["speaking", "reading"]`.

Any `reader`, `dialogue`, `shadow` or `text` lesson can end with a quiz:

```json
"questions": [ { "q": "Where do the blocks go?", "options": ["On the shelf", "In the box"], "answer": 1, "why": "Put the blocks in the box." } ]
```

A dialogue line: `{ "who": "A", "text": "Bonjour !", "tr": { "en": "Hello!" }, "note": "..." }`.
A Japanese line: `{ "who": "A", "romaji": "Konnichiwa.", "kana": "こんにちは。", "tr": { "en": "Hello.", "my": "မင်္ဂလာပါ။" } }`. The voice reads the kana, or `"say"` when the line has one: the same sentence written with kanji, which the voice reads and pitches more reliably than kana alone.
A Korean line: `{ "who": "A", "rom": "Annyeonghaseyo.", "hangul": "안녕하세요.", "tr": { "en": "Hello." } }`. The page opens on **Both** (the romanization with the Hangul under it); the Romanized / 한글 / Both buttons switch. The voice will read the Hangul. The romanization is Revised Romanization, written as the words are said (`hangungmal` for 한국말). In a Korean sound lesson (`words`) `fr` holds the romanization, `ipa` and `say` the Hangul.

Copy an existing file in the same strand to start a new lesson.

A Japanese or Korean expression card (`cards`) has five parts, like the French and English ones: `["Kore wa ikura desu ka.", "How much is this?", "これはいくらですか。\n\nKore: this (near me).", "Sumimasen, kono kasa wa ikura desu ka.\nすみません、この傘はいくらですか。", "Excuse me, how much is this umbrella?"]`. The card shows the romanization and the English; the note opens with the phrase in Japanese script or Hangul; the example gives the romanization with the script under it. **The voice reads the first line of the note** when it is in Japanese script or Hangul, never the romanization, so keep that line first.

**Explanation languages on expression pages.** A `cards` lesson may let the visitor choose the language of the explanations from a menu under the title. Name the languages in the lesson, the first being the one the cards are written in: `"langs": ["my", "es", "fr"]` on an English page, `"langs": ["en", "my"]` on a Japanese or Korean one (`my` Burmese, `en` English, `es` Spanish, `fr` French). Each card then ends with one more item holding the other languages: `["Hello.", "မင်္ဂလာပါ။", "<note>", "<example>", "<example in Burmese>", {"es": ["Hola.", "<note in Spanish>", "<example in Spanish>"], "fr": [...]}]`: the meaning, the note, then one translation per example. On a Japanese or Korean card the note in the other language repeats the line in Japanese script or Hangul first. A category takes `"tr": {"es": "Saludar"}` (or `["title", "description"]`). Whatever is missing in the chosen language is shown in the first one, and a page without `langs` has no menu, so pages can be translated one at a time. The choice is remembered per course on the visitor's device. Audio is not affected: the voice reads the same lines. A category's description is translated in the same place: `"tr": {"es": ["Saludar", "Las primeras palabras…"]}`. The quiz follows the same menu. The cards' meanings and notes come from the cards; what a question says itself goes in `tr` on the question: `"tr": {"es": {"my": "<the scene in Spanish>", "wrong": {"Hey!": "<note>"}, "note": "…", "cue": "…", "decoys": {"be": "<note>"}}}`, and a tip in `quizTags` may be given per language: `{"feeling": {"my": "Match the feeling…", "es": "…", "fr": "…"}}`. The quiz's own buttons and headings stay in English.

## Transcripts

Every speaking lesson can have a printable transcript: `<course>\speaking\<lesson>.pdf`, beside its page and published with it. `6_transcripts.bat` makes the ones that are missing or older than their lesson file (`tools\transcript.py`), then rebuilds the pages. A lesson page shows a "Transcript (PDF)" button only when its PDF is there, so run it after writing or changing a speaking lesson, before `5_publish.bat`.

The PDF holds the title, the lesson's number, level and heading, the short address with a QR code, every scene with its lines and their translation, and the lesson's `notes`. The notes of single lines and the introduction are left out, so that a dialogue fits on one sheet printed on both sides when it can. Paper size is A4. Japanese and Korean lines show the romanization with the script under it; a lesson with no translation is set in one column.

It is printed by Microsoft Edge (Chrome if Edge is not there), which is already on the computer and is never opened on screen: only a browser sets Burmese, Japanese and Korean correctly. The QR code needs one small package, once: `pip install segno`. Without it the PDFs are made with the address alone. The layout is the `page()` function in `tools\transcript.py`; `STRANDS` there names the strands that get transcripts. Renaming or retiring a lesson removes its PDF with its page.

## Audio wire

`aud_dir` is the folder on R2 **and** under `media\` (`"fr/speaking/boulangerie/"`). Clips are `01.mp3`, `02.mp3` … in reading order. While `aud_ext` is `"mp3?v=pending"` the Play buttons are grey. `2_audio.bat` makes the clips, uploads them and replaces `pending` with a dated tag.

A `text` lesson can instead use one existing recording: `"audio_file": "lessons/read/amber.m4a"` plus `"t": [start, end]` (seconds) on each sentence. Nothing is cut or re-encoded. See `content\fr\reading\amber.json`. `python -E tools\audio.py upload <lesson>` sends the recording (and the lesson's numbered glossary clips) to R2 and stamps `"audio_ver"` in the lesson file: a new take keeps the name `audio.mp3` and gets a new tag, so nobody is served a saved copy of the old one. The page then shows a player (play, pause, stop, slider). Word clips named by word go in `"glossary_dir": "lessons/read/amber/"` with `"glossary": [{ "word": "ambre", "en": "amber" }]`; add `"audio": "goutte.m4a"` when the file name differs from the word or is not an .mp3.

`"aud_shared": true` marks a lesson that reuses another lesson's clips (the first shadowing pages do); the audio tool leaves those alone.

**Shadowing chunks without new takes.** A shadowing chunk can be a part of a dialogue line's clip instead of a recording of its own: `{ "text": "Ils sont légers.", "clip": 1, "t": [3.05, 4.0] }` plays seconds 3.05 to 4.0 of `01.mp3`. You never type the `t` values:

```
python -E tools\audio.py shadow fr/speaking/conv43                  drafts content\fr\pronunciation\shadow_conv43.json, one chunk per sentence
python -E tools\audio.py chunks fr/pronunciation/shadow_conv43      finds every chunk inside its clip and writes its "t"
```

Split or join chunks in the drafted file as you like (each keeps the `clip` number of its line; the words must be the line's words), then run `chunks` again. It uses no ElevenLabs characters: every take is saved with the time of each character (`NN.json` beside the raw take), and clips made before that are timed by Whisper. A chunk it cannot find plays its whole clip and is listed as `NO TIME`.

Voices and loudness per course: `assets\data\voices.json`. A dialogue gives each speaker a voice with `"voice": { "E": "<voice id>", "L": "<voice id>" }`. A lesson may use another ElevenLabs model than its course with `"voice_model": "eleven_v4"`. Korean uses ElevenLabs `eleven_v4` with four voices: Ko-Jisoo (the course voice) and Ko-Nam for women, Ko-SunSoo and Ko-Kim for men. Each dialogue gives its speakers one woman and one man (`"voice": {"A": ..., "B": ...}`); each sound lesson gives its groups of words a woman and a man in turn (`"voices"`). Spanish uses two voices: Sp-Maria (the course voice, and Emma in the dialogues) and Sp-Jose (Lucas); each dialogue names them in its `voice`. Whisper does not compare Korean automatically: it writes numbers as digits and hears lone syllables as English (국 as *cook*), so read its "heard" column.

## Pictures

A reader's pictures are `img\...\1.jpg`, `2.jpg` … in its `img_dir`. A missing picture shows a dashed placeholder. Give a page `"alt": "Mia brushing her teeth"` and the placeholder shows that description.

## Levels

Imported lessons carry `"level_provisional": true`: the level is a guess from the file name. Set the real `level`, delete that line. `4_check.bat` lists what is left.

## About, Contact, Privacy Policy

Three pages about the site itself, linked from the footer of every page: `about.html`, `contact.html`, `privacy.html`. Like the lessons, they are generated (`info_pages()` in `tools\build.py`).

- The text of **About** and **Privacy Policy** is in `content\pages\about.md` and `content\pages\privacy.md`. Edit the file, then build. `# ` is the page title, a `### ` line straight after it is the line under the title; then `## ` headings, paragraphs, `- ` lists, `---`, `**bold**`, `[words](address)`.
- The **Contact** form is delivered by [Web3Forms](https://web3forms.com), a form-forwarding service (a site with no server cannot send email itself). Its access key goes in `site.json`: `"contact": { "access_key": "..." }`. The key stands for the mailbox, so no email address is written in the page. While the key is empty the build says so and the form tells visitors it is not switched on yet. Spam: a hidden box only robots tick, and a form sent within 3 seconds of opening the page is thanked but never sent.
- When the site starts doing something new with visitors' information (analytics, a newsletter, comments, ads), update `privacy.md` and its date.

## Publishing

This folder is a git repository; its remote is the public GitHub repository `mschiffman/CuriousLingua` (branch `main`). `5_publish.bat` rebuilds, commits and pushes. The site is online at https://curiouslingua.mschiffm.workers.dev/ : the Cloudflare Worker `curiouslingua` rebuilds it from `main` after every push (`wrangler.jsonc` serves this folder as a static site; `.assetsignore` lists what stays off the live site). `media\`, the offline copies and the working folders are in `.gitignore`.

## Changing the design

Page shells are in `tools\build.py`, behaviour in `assets\js\site.js`, colours and fonts in `tools\tailwind.config.js` and `tools\site.src.css`. After changing classes, run `tools\rebuild_css.bat` (needs Node). Adding lessons never needs it.

**Motion.** `assets\js\motion.js` (GSAP, in `assets\vendor\`) runs on every page: titles rise word by word, tiles fade in as they scroll into view, numbers count up, tiles lean toward the mouse. Visitors who ask for reduced motion, or are on a slow or data-saver connection, get the plain page (`<html class="lite">`).

**The home page globe.** `assets\js\globe.js` (Three.js) draws the Earth in the dark hero: the course countries are lit (France, the USA, Mexico, Japan, Korea; eight at most), the globe tours between them, it can be dragged, and a click on a country (or its label, or a language button) flies in and opens that course. Which country belongs to which course, and where its label sits, is at the top of `tools\globe.py` (`HIGHLIGHT`, `ANCHOR`, `LABEL`; the order of `HIGHLIGHT` is the order of the tour; a label that should sit beside its country, not above it, is named in `SIDE` in `globe.js`); run `python -E tools\globe.py` after changing it (needs Pillow). It writes the pictures in `assets\img\globe\` and the borders in `assets\data\globe.json`; its source files are kept in `_archive\globe-src\` (not in git, downloaded again when missing). In lite mode, and until the 3D globe has loaded, the page shows the still picture `assets\img\globe\poster.webp`. The home page text (the four steps, the greetings that drift by) is in `home()` in `tools\build.py`; the bright course colours for the dark hero are `--glow` in `tools\site.src.css`.

The expression pages keep their original design: `assets\css\cards.css`, `expression-flash.js` and `expression-quiz.js` are copies of the originals.

## Where things came from

`tools\import_legacy.js` converted the old pages: 40 French expression pages, 24 English expression pages, 62 story and picture-vocabulary readers. Run it again to pick up new old-site pages; it never overwrites `level`, `topic`, `order` or titles you have edited.
