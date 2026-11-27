# CuriousLingua — Voice Creation Standards

Version: 1.1 | Status: for Marissa's approval. Version 1.0 was drafted by ChatGPT; 1.1 fits it to the site's own tools (27 November 2026). What changed is listed at the end.

## 1. Purpose
Create authentic, pleasant, intelligible voices for language-learning conversations, stories, expressions and podcasts. Learners should hear natural native speech, not exaggerated textbook delivery.

## 2. How it is done here
This page says what a good voice is. The facts about the voices in use are kept elsewhere, and are not repeated here.

- **The registry** is `assets\data\voices.json`: for each course, the voice, the ElevenLabs model and the loudness. A dialogue names its own speakers' voices in its `"voice"` line; for Emma and Lucas, copy that line from an existing speaking lesson of the same course.
- **The tools** are `2_audio.bat`, `record_scenes.bat` and `record_pending.bat` (`COMMANDS.md`). They ask before using any ElevenLabs characters, record only the clips that are missing, keep every raw take with its timings in `media\elevenlabs-raw\`, check each clip with Whisper, and upload to R2.
- **The keys** are in the system environment of Marissa's computer. Never in a file.
- **Japanese pitch** is checked with `pitch.bat`, against the same lines read by AivisSpeech.

## 3. Core voice profile
- Warm, friendly, educated-sounding, cheerful and approachable.
- Smooth, rich, buttery or velvety timbre; no harsh, piercing, shrill or excessively nasal delivery.
- Clear articulation, natural rhythm, appropriate stress and expressive but restrained intonation.
- Well-paced, with meaningful pauses; never rushed, robotic, monotonous or artificially syllable-by-syllable.
- Default dialogue age impression: 25–30. Other ages may be selected to suit characters.
- Male voices: warm, resonant, medium-low to deep, without forced bass or vocal fry.
- Female voices: warm, smooth, clear, mature and naturally expressive; avoid exaggerated sweetness or childish delivery.
- Prefer original synthetic voices rather than imitations of identifiable people.

## 4. Language profiles
| Language | Accent target | Special checks |
|---|---|---|
| English | The course voice in the registry is a Modern British RP woman, and she is Emma in the dialogues. **Open question for Marissa:** the English conversations are written in American English (apartment, vacuumed, one mile). Either is fine; mixing them in one lesson is the thing to decide | Natural reductions, stress, linking; do not mix accents unintentionally |
| French | Contemporary standard metropolitan French, Parisian pronunciation | Liaison, enchaînement, nasal vowels, schwa and natural register |
| Japanese | Standard Tokyo Japanese | Pitch accent, mora timing, long vowels, gemination, contextual kanji readings; avoid anime-like delivery. The voice reads the kana, or a line's `"say"` (the same sentence with kanji) when kana alone is misread |
| Korean | Standard Seoul Korean. Four voices, two women and two men; each dialogue takes one of each | Batchim, sound changes, vowel distinctions, honorific register; avoid exaggerated drama delivery. Whisper cannot check Korean by itself: read its "heard" column |
| Spanish | Latin American Spanish, Mexican usage (decided). Two voices: Sp-Maria is Emma, Sp-Jose is Lucas | Consistent regional pronunciation, stress, vowels and natural connected speech |
| Burmese | No Burmese voice is set up. Authentic native Burmese, with regional variety approved by Marissa | Tone, phonation, natural phrasing; prefer approved native recordings or authorized speech-to-speech when TTS fails |

No accent is literally accentless. Use a named standard variety. Do not infer nationality or language competence from voice timbre.

The Japanese and Korean recordings have not been checked by a native speaker. Whisper and the pitch report catch wrong words and odd pitch; they do not make a recording correct.

## 5. Reusable ElevenLabs Voice Design prompts
Use concise English descriptions. Generate only when authorized. These are starting prompts, not guarantees of output quality.

### English — male
> A native General American English male voice, age 25–30, educated and articulate. Warm, friendly, cheerful, rich and velvety, with a naturally resonant lower register. Clear pronunciation, smooth conversational rhythm, measured pacing and subtle expression. No harshness, forced bass or announcer delivery.

### English — female
> A native General American English female voice, age 25–30, educated, warm and cheerful. Buttery smooth, clear, expressive and well-paced, with natural conversational intonation. Mature and approachable, never shrill, breathy or overly sweet.

### British English — female
> A native British English female voice with contemporary Modern RP pronunciation. Warm, refined, educated, clear and naturally expressive. Silky smooth timbre, gentle confidence and measured conversational pacing. Never stiff, theatrical or exaggeratedly posh.

### French — male
> A native French male voice, age 25–30, with contemporary standard Parisian pronunciation. Educated, warm, friendly and cheerful, with a deep, rich, velvety tone. Clear articulation, natural French rhythm, expressive yet restrained, and well-paced conversational delivery.

### French — female
> A native French female voice, age 25–30, with contemporary standard Parisian pronunciation. Sweet but mature, warm, cheerful and educated. Silky, buttery smooth timbre, clear articulation, natural musicality and well-paced expressive conversation. Never shrill or overly theatrical.

### Japanese — male
> A native Japanese male voice, age 25–30, speaking standard Tokyo Japanese. Educated, friendly, warm and richly resonant, with a smooth lower register. Clear articulation, natural pitch accent and mora timing, measured conversational pacing. Never stiff, harsh or rushed.

### Japanese — female
> A native Japanese female voice, age 25–30, speaking standard Tokyo Japanese. Warm, cheerful, educated and approachable, with a buttery smooth mature tone. Clear pronunciation, natural pitch accent and well-paced conversational rhythm. No childish, excessively sweet or anime-like delivery.

### Korean — male
> A native Korean male voice, age 25–30, speaking standard Seoul Korean. Warm, friendly, educated, deep and velvety. Clear articulation, natural Korean sound transitions and measured conversational pacing. Expressive but restrained, never harsh or overly dramatic.

### Korean — female
> A native Korean female voice, age 25–30, speaking standard Seoul Korean. Cheerful, warm, educated and naturally expressive. Smooth, rich, gentle timbre, clear articulation and well-paced conversational delivery. Never piercing, childish or exaggeratedly breathy.

### Spanish — male
> A native Mexican Spanish male voice, age 25–30, with clear Latin American pronunciation. Educated, warm, friendly and cheerful, with a rich, velvety lower register. Natural rhythm, precise articulation and measured pacing. Never harsh, rushed or theatrical.

### Spanish — female
> A native Mexican Spanish female voice, age 25–30, with clear Latin American pronunciation. Educated, cheerful, friendly and warm, with a buttery smooth mature timbre. Natural stress, clear vowels and well-paced expressive conversation. Never sharp or excessively sweet.

### Podcast host
> A warm, cheerful, educated young adult host, age 25–30. Friendly, curious and engaging, with a smooth rich voice, clear articulation and well-paced delivery. Speak directly to the learner with natural enthusiasm, not like a commercial announcer. Use the approved language and accent profile.

## 6. Delivery by lesson type
- A1: clear phrase boundaries and slightly relaxed pacing; preserve native rhythm.
- A2: natural everyday dialogue with manageable pacing.
- B1/B2: increasingly natural speed and connected speech, without sacrificing clarity.
- Stories: expressive narration, appropriate emotional variation, no unnecessary melodrama.
- Conversations: distinct voices, consistent roles, believable turn-taking. Record them scene by scene (`record_scenes.bat`), so the two voices answer each other.
- Expressions: isolate the target expression when required, then deliver examples naturally.
- Podcast: friendly transitions, enough time for learners to repeat, distinct host and example voices.
- Titles and subtitles: include in audio only when the lesson format calls for them; verify all required segments exist.

## 7. Approval and quality control
1. Audition a short representative passage before approving a voice. Include questions, statements, numbers and difficult language-specific sounds.
2. Listen for timbre, clarity, naturalness, pacing, accent, consistency and fatigue over longer listening.
3. Compare audio with source text; check omissions, repetitions, wrong readings, clipping and unnatural pauses.
4. Use local Whisper transcription as a content check, not proof of correct pronunciation. Seek qualified native review where pronunciation cannot be reliably assessed.
5. Reject audio with wrong speaker, wrong language, incorrect meaning, distracting artifacts or material pronunciation errors.
6. An approved voice goes into `assets\data\voices.json`, or into the lesson's `"voice"` line. Never silently substitute an approved voice.
7. Regenerate only the defective clip (`audio.py make <lesson> --redo N`): the old clip and its raw take are moved aside, not deleted.

## 8. Technical and cost controls
- Use only authorized voices and recordings; obtain consent for voice cloning or speech-to-speech.
- Loudness is set per course in the registry. French and Japanese clips are never re-encoded after leveling. In the offline files, English audio is made smaller and French and Japanese are embedded exactly as recorded (`tools\offline.py` says which). Do not impose new encoding settings without approval.
- Estimate characters before generation. No paid calls, batch regeneration or retries without authorization. One approved job at a time; stop on failure rather than looping.
- Reuse existing valid audio: a lesson's `aud_dir` keeps pointing at the folder its clips were recorded in, even after the lesson is renamed. Shadowing pages reuse parts of dialogue clips and cost nothing.
- Marissa's approval is required for permanent voice changes, new regional accent defaults and paid generation.

## What changed from version 1.0
- Added "How it is done here": the registry, the tools and the keys already exist, so the standard points to them.
- Spanish is no longer "proposed": Latin American, Mexican usage, with two voices in use. The two Spanish prompts now say Mexican.
- English: recorded what the registry holds (a British RP voice), and raised the American-wording question instead of asserting General American.
- Korean and Japanese: added what the site already does (four Korean voices, `"say"`, the pitch check) and that neither has had a native check.
- Removed "keep lossless masters" and "record prompt, settings and sample path for every voice": ElevenLabs returns MP3, and nothing in the project keeps such a log. Raw takes are kept, which is the part that matters.
- "Save voice IDs in a local voice registry" now names the registry.
