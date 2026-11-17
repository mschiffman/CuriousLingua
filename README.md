# LANGSITE

One site, three courses: **French** (adults, A1–C1), **English** (children in Myanmar, Starter–C1), **Japanese** (speaking only, A1–B2, English and Burmese support).

## The one rule

Lessons are the `.json` files in `content\`. Every `.html` page is generated from them by `tools\build.py`. Edit the lesson file, never the page.

```
content\<course>\<strand>\<slug>.json   ->   <course>\<strand>\<slug>.html
content\fr\expressions\greetings.json   ->   fr\expressions\greetings.html
```

Courses: `fr`, `eng`, `jap`. Strands, level names and course texts are in `site.json`.

## The .bat files

| File | What it does |
|---|---|
| `SETUP.bat` | Run once: unpacks the site and copies `img\` and `media\` from the old LANGUAGES folder (read only) |
| `preview.bat` | Rebuilds and opens the site at http://localhost:8000 |
| `1_images.bat` | Same as your `all_downloads_to_ytstory.bat`: moves the numbered PNGs from Downloads to `G:\My Drive\_YOUTUBE\<folder>`, converts them at 80% size with Squoosh settings (MozJPEG, quality 75) into `img\ytstory\<name>` here |
| `2_audio.bat` | Menu: ElevenLabs balance, lessons needing clips, make one or all, new takes, Whisper check, upload to R2 |
| `3_offline.bat` | Builds the single-file offline lessons in `<course>\single\`. A course's `offline_url` in `site.json` is the shared folder its pages point to. They are shared on the Google Drive shared drive; the website offers no downloads |
| `4_check.bat` | Status report: counts per level and strand, audio to record, missing pictures, things to review |
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
| `words` | Themed word lists (French vocabulary) | optional opening picture `img` + `img_alt`; a built-in Quiz (hear a word, choose it; `"listen_pick": "fr"` shows spellings instead of meanings); `groups`: `{ "title", optional "sub", "notes": [...], "audio" (a clip for the heading), "words": [ { "fr", "g": "m" or "f", "ipa", "en", "audio": "volcan.mp3" } ] }`. Each word's `audio` is a named file in `glossary_dir` (`maison.mp3`); `python -E tools\audio.py words <lesson>` records the ones that are missing and writes the names in. See `content\fr\vocabulary\landforms.json` |
| `hotspots` | Pictures with tappable dots, with a quiz mode | `slides`: `{ "img", "alt", "spots": [ { "x", "y" (percent from the left and top), "fr", "g", "ipa", "en", "audio" } ] }`. Usually a supplement of a word list. See `content\fr\vocabulary\landforms_hotspots.json` |
| `link` | A supplement kept somewhere else, such as a mind map on Google Drive | `href`: the address. Its tile opens it in a new tab; no page is built |
| `page` | A hand-made page shown as a supplement (the mind maps) | None. Like `game`: you keep `<course>\<strand>\<slug>.html` yourself and the build only links to it |
| `game` | Hand-made interactive pages (the 3D preposition quiz) | None. The build lists it but does **not** generate the page: you keep `<course>\<strand>\<slug>.html` yourself, next to anything it loads. Optional `clips`: a list of sentences the page plays, recorded and uploaded by the audio tool like any lesson (`01.mp3`, `02.mp3` …). After an upload, copy the lesson's new `aud_ext` into the page by hand (in `wheres_the_ball.html`, the `CLIPS` line). `tools\offline.py` writes small copies of those clips to `<slug>_audio\` beside the page; the page plays them first, so it works without internet. See `content\eng\grammar\wheres_the_ball.json` |

**Supplements.** A lesson file with `"supplement_of": "amber"` is not listed on its own: it appears in a "Supplemental section" at the bottom of that lesson (same folder). `label` is the chip shown on its tile.

**File names** use underscores, not dashes: `amber_cloze.json`, `video_amber.json`. To rename a lesson, save it under the new name and replace the old file's content with `{"retired": true}`; the next build deletes the old file and its pages.

Any `reader`, `dialogue`, `shadow` or `text` lesson can end with a quiz:

```json
"questions": [ { "q": "Where do the blocks go?", "options": ["On the shelf", "In the box"], "answer": 1, "why": "Put the blocks in the box." } ]
```

A dialogue line: `{ "who": "A", "text": "Bonjour !", "tr": { "en": "Hello!" }, "note": "..." }`.
A Japanese line: `{ "who": "A", "romaji": "Konnichiwa.", "kana": "こんにちは。", "tr": { "en": "Hello.", "my": "မင်္ဂလာပါ။" } }`. The voice reads the kana.

Copy an existing file in the same strand to start a new lesson.

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

Voices and loudness per course: `assets\data\voices.json`. **The Japanese voice is not chosen yet.**

## Pictures

A reader's pictures are `img\...\1.jpg`, `2.jpg` … in its `img_dir`. A missing picture shows a dashed placeholder. Give a page `"alt": "Mia brushing her teeth"` and the placeholder shows that description.

## Levels

Imported lessons carry `"level_provisional": true`: the level is a guess from the file name. Set the real `level`, delete that line. `4_check.bat` lists what is left.

## Publishing

This folder is a git repository; its remote is the public GitHub repository `mschiffman/CuriousLingua` (branch `main`). `5_publish.bat` rebuilds, commits and pushes. The site is online at https://curiouslingua.mschiffm.workers.dev/ : the Cloudflare Worker `curiouslingua` rebuilds it from `main` after every push (`wrangler.jsonc` serves this folder as a static site; `.assetsignore` lists what stays off the live site). `media\`, the offline copies and the working folders are in `.gitignore`.

## Changing the design

Page shells are in `tools\build.py`, behaviour in `assets\js\site.js`, colours and fonts in `tools\tailwind.config.js` and `tools\site.src.css`. After changing classes, run `tools\rebuild_css.bat` (needs Node). Adding lessons never needs it.

The expression pages keep their original design: `assets\css\cards.css`, `expression-flash.js` and `expression-quiz.js` are copies of the originals.

## Where things came from

`tools\import_legacy.js` converted the old pages: 40 French expression pages, 24 English expression pages, 62 story and picture-vocabulary readers. Run it again to pick up new old-site pages; it never overwrites `level`, `topic`, `order` or titles you have edited.
