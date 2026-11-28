# CuriousLingua: project map

Read this first. It says where things are and which file owns each subject. It holds no detail of its own: when a fact here and the file it points to disagree, the file it points to is right, and this page needs fixing.

## What this is

A free language-learning site, curiouslingua.com, with five courses (French, English for children in Myanmar, Japanese, Korean, Latin American Spanish), and the short videos that send people to it. One person, Marissa, writes, records, builds and publishes all of it.

## The rules that always apply

1. **Lessons are the `.json` files in `content\`. Every `.html` page is generated.** Edit the lesson file, never the page. (The exceptions are named in `README.md`.)
2. **Marissa runs the tools.** A cloud session can read and write files in this folder but cannot run the `.bat` files, the build or git here. Make the change, say which `.bat` to run, and stop.
3. **After writing a file into this folder, read it back and compare.** A write has reported success while delivering an older copy.
4. **Nothing is published without her say.** `5_publish.bat` is hers to run.
5. **Ask before anything that costs money**: ElevenLabs characters, paid image generation. Say how much first. The audio tools already ask.
6. **Never delete a lesson file.** Rename or remove it with `{"retired": true}`, as `README.md` describes; the build clears it away.
7. **Every lesson has two forms**: the web page, and the offline single file built by `3_offline.bat`. Plan for both. A speaking lesson also has a printable transcript, made by `6_transcripts.bat`.
8. **File names use underscores, never dashes.**
9. **One fact, one place.** Do not copy voice IDs, paths or settings into a second file. Point to the file that owns them.

## Where things are

| Place | What it is |
|---|---|
| `G:\My Drive\LANGSITE` | This folder: the site, its lessons and its tools. A git repository, public on GitHub as `mschiffman/CuriousLingua` (branch `main`) |
| `content\<course>\<strand>\` | The lessons (`fr`, `eng`, `jap`, `kor`, `spa`) |
| `tools\` | The Python tools the `.bat` files call |
| `assets\data\voices.json` | The voice, model and loudness of each course |
| `media\` | Local copy of the audio; the live copy is on R2 (`media_base` in `site.json`). Not in git |
| `img\` | Pictures. `img\ytstory\<name>\` holds a picture story's `1.jpg`, `2.jpg` … |
| `<course>\single\` | Offline single-file lessons. Not in git; shared on Google Drive. Only the grammar chapters' copies are in git and on the site (their pages have a Download button) |
| `workflows\` | Standards for voices and pictures |
| `G:\My Drive\_VIDEO` | Where the videos are made: `make_video.bat`, with its own `README.md` |
| `G:\My Drive\_YOUTUBE\<folder>` | The original pictures (PNG), moved there by `1_images.bat` |

Everything in this folder that is in git is public. Keys stay in the system environment of her computer, never in a file.

## Which file owns what

| Subject | Read |
|---|---|
| Lesson files and their formats, lesson types, the audio wire, renaming, publishing, changing the design | `README.md` |
| What to run for each task | `COMMANDS.md` |
| Grammar chapters (`g001_present_simple`: scenes, rule, practice, quiz, five explanation languages) | `README.md`, "Grammar chapters" |
| Speaking lesson names, numbers, short addresses, old addresses | `README.md`, "Speaking lessons: numbers and short addresses" |
| Search box, "Goes with this lesson", other languages | `README.md`, "What the numbers do on the pages" |
| Printable transcripts (PDF) | `README.md`, "Transcripts" |
| Courses, strands, level names | `site.json` |
| Voices: which voice, which model, how loud | `assets\data\voices.json`; a dialogue's own speakers are in its `"voice"` line |
| What a good voice sounds like, and how to check one | `workflows\voice-creation-standards.md` |
| What a good picture looks like, and how to check one | `workflows\image-creation-standards.md` |
| Making a video from audio, pictures and a script; the lesson's address on the video (`Code: F13`) | `G:\My Drive\_VIDEO\README.md` |

## Names, in one paragraph

A speaking lesson is `<letter><number>_<scene>.json`: `f013_disbelief.json`, `e013_disbelief.json`. The letter is the course, the number names what the lesson teaches and is shared by every course that teaches it, and the scene name is in English. Its `code` (`F13`) is the address shown in videos: `curiouslingua.com/f13`. A number is never reused. Other strands keep the names they have.

## Emma and Lucas

The speaking conversations are scenes between a couple, Emma and Lucas (Emi and Riku in Japanese): at home, teasing each other over a small everyday mishap, dry, each scene ending on a punchline. Each language gets its own conversation; the humor is rewritten for the culture, not translated. Write the `.md` script first, in the plain form of the scripts beside the lessons (a title, `## ` scene headings, the spoken lines and nothing else), then the lesson file. For their voices, copy the `"voice"` line from an existing speaking lesson of the same course.

## Checked and unchecked

A lesson's `review` line says what nobody has checked yet. The Japanese and Korean lessons have not been checked by a native speaker. `4_check.bat` lists every lesson with a `review` line.

## Not done yet

- Short addresses only work in small letters (`/f13`, not `/F13`).
- The videos already on YouTube and Facebook still carry their old links.
- The expression pages are named differently in each course (`greetings`, `greet_goodbye`; `iMean`, `i_mean`).
- There is no written character sheet for Emma and Lucas (see the image standards).

## Keeping this page true

When a session changes how something is done, it updates the file that owns that subject before it finishes, and this page only if a place, a rule or an owner changed. Take a line out of "Not done yet" when it is done.
