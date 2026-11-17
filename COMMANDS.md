# Commands for the Languages site

Everything is run from the site folder, `G:\My Drive\LANGSITE`. The `.bat` files are in that folder: double-click them. The Python tools are in `tools\`: run them from a terminal opened in the site folder, always as `python -E tools\<name>.py`.

`README.md` explains the lesson files and their formats. This file is only about what to run.

## Where things are

| Path | What it is |
|---|---|
| `*.bat` (site folder) | The double-click tools, numbered in the order you normally use them |
| `tools\*.py` | The Python tools the `.bat` files call |
| `content\<course>\<strand>\<slug>.json` | The lessons. **This is what you edit.** |
| `<course>\<strand>\<slug>.html` | The pages. Generated: never edit them (game pages are the one exception, see below) |
| `site.json` | Courses, strands, level names |
| `assets\data\voices.json` | The ElevenLabs voice, model and loudness of each course |
| `media\` | Local copy of the audio that is on R2 |
| `media\elevenlabs-raw\` | Raw takes and their timings (`NN.mp3`, `NN.json`) |
| `img\` | Pictures |
| `_reports\status.md` | The last status report |
| `_archive\` | Things taken off the site but kept |

## The .bat files

| File | Use it to | Runs |
|---|---|---|
| `preview.bat` | Rebuild the pages and open the site at http://localhost:8000. Close the window to stop. | `tools\build.py`, then a local web server |
| `1_images.bat` | Move the numbered PNGs from Downloads to `G:\My Drive\_YOUTUBE\<folder>` and convert them to JPG in `img\ytstory` | `tools\convert.py` |
| `2_audio.bat` | Open the audio menu: lessons needing clips, make clips, new takes, Whisper check, upload | `tools\audio.py` |
| `3_offline.bat` | Build single-file offline lessons in `<course>\single\` | `tools\offline.py` |
| `4_check.bat` | Write and open the status report | `tools\check.py` |
| `5_publish.bat` | Rebuild every page; commit and push when the folder is a git repository | `tools\build.py`, then git |
| `SETUP.bat` | Run once on a new computer: unpack the site and copy `img\` and `media\` from the old LANGUAGES folder | `tools\build.py`, `tools\check.py` |
| `tools\rebuild_css.bat` | Rebuild `assets\css\site.css` after changing page classes (needs Node) | Tailwind |

## Everyday tasks

### Look at the site

Double-click `preview.bat`, or:

```
python -E tools\build.py
```

`build.py` regenerates every page from `content\`. Run it after any change to a lesson file.

### Add, change or remove a lesson

- **Add:** copy a lesson file in the same strand, rename it (underscores, no dashes), edit it, rebuild.
- **Change:** edit the `.json`, rebuild.
- **Rename:** save it under the new name, and replace the old file's content with `{"retired": true}`. The next build deletes the old file and its pages.
- **Remove:** replace the file's content with `{"retired": true}` and rebuild. Copy it to `_archive\` first if you may want it back.
- **Game pages** (`"type": "game"`, such as `eng\grammar\wheres_the_ball.html`): the build lists them but never writes them. You keep the `.html` yourself, with anything it loads (`three.min.js`) beside it. If the game has recorded sentences (the `clips` list in its lesson file), record and upload them like any lesson, then copy the new `aud_ext` from the lesson file into the page's `CLIPS` line.

### Check what is missing

```
python -E tools\check.py
```

Counts per level and strand, audio still to record, clips not on this computer, missing pictures, lessons flagged for review. Same as `4_check.bat`. The report is `_reports\status.md`.

```
python -E tools\images.py
```

Lists the lessons that are missing pictures and the folder each one expects.

## Audio

A lesson is written `course/strand/slug`, for example `fr/listening/home_pantry_shelves`.

| Command | What it does | Uses ElevenLabs characters |
|---|---|---|
| `python -E tools\audio.py` | The menu (same as `2_audio.bat`) | |
| `python -E tools\audio.py status` | Every lesson with clips still to make | no |
| `python -E tools\audio.py make <lesson>` | Make the missing clips, level them, run Whisper on them | **yes** |
| `python -E tools\audio.py make <lesson> --only 3 4` | Make only clips 3 and 4 | **yes** |
| `python -E tools\audio.py make <lesson> --redo 6 12` | New takes of clips 6 and 12. The old clips are moved aside, not deleted | **yes** |
| `python -E tools\audio.py check <lesson>` | Whisper on every clip, compared with the text | no |
| `python -E tools\audio.py upload <lesson>` | Send new or changed clips to R2, set the `?v=` tag, rebuild | no |
| `python -E tools\audio.py balance` | Characters left. Fails with "401" if the API key cannot read the subscription | no |

The usual order for a new lesson: `make`, listen to the clips Whisper marks `<<< check`, `--redo` the bad ones, then `upload`.

Things to know:

- **Upload is what makes sound appear on the site.** Until then the Play buttons are grey (`"aud_ext": "mp3?v=pending"`).
- **The menu only lists lessons that are pending or have clips missing.** A lesson that already has a `?v=` tag and all its clips on disk does not appear: upload it by name.
- **Two voices in a dialogue:** add `"voice": {"E": "<voice id>"}` to the lesson file, one entry per speaker who should not use the course voice. The course voice is in `assets\data\voices.json`.
- **Japanese** has no voice chosen yet, so `make` stops for Japanese lessons.

### Shadowing chunks without new recordings

Record the dialogue once, one clip per speaker turn. The shadowing chunks are then played as parts of those clips.

```
python -E tools\audio.py shadow fr/listening/home_pantry_shelves
```

Drafts `content\fr\pronunciation\shadow_home_pantry_shelves.json`: one chunk per sentence, each with the `clip` number of its line.

```
python -E tools\audio.py chunks fr/pronunciation/shadow_home_pantry_shelves
```

Finds every chunk inside its clip and writes its `"t": [start, end]`, then rebuilds. Uses no characters.

- Split or join chunks in the drafted file if you like, keeping each chunk's `clip` number and the line's own words, then run `chunks` again.
- A chunk it cannot find is listed as `NO TIME` and plays its whole clip.
- New takes are saved with their timings. Clips recorded before November 2026 are timed by Whisper the first time, which is a little less exact.
- After a `--redo` of a dialogue clip, run `chunks` again for its shadowing lesson: the timings of the new take are different.

## Offline copies

Double-click `3_offline.bat`, or:

```
python -E tools\offline.py --changed
python -E tools\offline.py all
python -E tools\offline.py fr/expressions/greetings
python -E tools\offline.py eng/reading
```

Each lesson becomes one `.html` with fonts, pictures and audio inside, in `<course>\single\`.

A game is different: its page is not copied. Its clips are written, small, into a folder beside the page (`eng\grammar\wheres_the_ball_audio\`), and the page plays those first and the online ones only if the folder is missing. So the game has its voice without internet as long as the page, `three.min.js` and that folder stay together. After a new take of a game clip, run `python -E tools\offline.py eng/grammar/wheres_the_ball` (or `--changed`) to refresh the folder.

## Publishing

Double-click `5_publish.bat`. It rebuilds every page, then commits and pushes to the GitHub repository `mschiffman/CuriousLingua` (public). A minute or so later the Cloudflare Worker `curiouslingua` has rebuilt the live site: https://curiouslingua.mschiffm.workers.dev/

Audio is separate from publishing: clips go online with `audio.py upload`, pages go online with `5_publish.bat`.

## Changing the design

Page shells are in `tools\build.py`, behaviour in `assets\js\site.js`, colours and fonts in `tools\tailwind.config.js` and `tools\site.src.css`. After changing classes, run `tools\rebuild_css.bat`.

## What the tools need

- **Python**, with `boto3` and `truststore` for uploads.
- **ffmpeg** and **whisper** on the PATH, for leveling and checking clips.
- **Node**, only for `tools\rebuild_css.bat`.
- **User environment variables:** `ELEVENLABS_API_KEY`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`.
