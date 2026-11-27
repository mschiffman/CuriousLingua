# CuriousLingua — Image Creation Standards

Version: 1.1 | Status: for Marissa's approval. Version 1.0 was drafted by ChatGPT; 1.1 fits it to the site's own tools (27 November 2026). What changed is listed at the end.

## 1. Purpose
Create charming, clear, culturally credible illustrations that help language learners understand stories and conversations immediately. Every image must serve the lesson, not merely decorate it.

## 2. How it is done here
This page says what a good picture is. How pictures reach the site and the videos is already fixed by the tools:

- **Pictures for the site.** Save a story's pictures as `1.png`, `2.png` … in Downloads and run `1_images.bat`. It moves the PNGs to `G:\My Drive\_YOUTUBE\<folder>` (these are the masters) and writes JPGs at 80% size into `img\ytstory\<name>\`. A picture story finds its pictures by number: `1.jpg`, `2.jpg` … in its `img_dir`. A missing picture shows a dashed box with the page's `alt` text, so a lesson can be built before its pictures exist.
- **Pictures for videos.** They go in `G:\My Drive\_VIDEO`, named after the audio or numbered in a folder of that name. The first picture decides whether the video is tall or wide, and pictures are cropped to fill the frame. The rules are in that folder's `README.md`.
- **No words on the picture.** The title and the captions are added when the video is made. Facebook and Shorts cover the bottom of the picture, so the captions sit higher there: keep faces and hands out of the lower part of a tall picture.

## 3. Signature visual style
- Clean, crisp, polished digital illustrations with confident, uncluttered lines.
- Charming, expressive characters; warm, inviting colors; soft natural lighting; readable silhouettes.
- Prefer a contemporary illustrated storybook/editorial look with controlled detail and gentle shading.
- Avoid busy ink hatching, scratchy outlines, excessive texture, visual clutter, muddy colors and overly plastic rendering.
- Use an approved reference image when supplied. Match its visual language, palette, line quality and character proportions rather than inventing a new style.
- Default to illustrations, not photorealistic photographs, unless explicitly requested.
- Keep adult characters recognizably adult; use age-appropriate proportions and expressions.

## 4. Output formats
| Use | Aspect ratio | Size |
|---|---|---|
| Facebook Reels / YouTube Shorts | 9:16 | 1080 × 1920 px |
| Landscape stories / reading slides | 16:9 | 1920 × 1080 px |
| Site and offline lessons | As the lesson needs | The JPG that `1_images.bat` writes; the PNG master is kept |
| Other formats | As requested | Confirm before generating |

Generate at the requested aspect ratio rather than relying on destructive cropping. If the generator cannot output exact pixel dimensions, resize or upscale proportionally and inspect the final result. Do not stretch images.

## 5. Composition and storytelling
- One clear visual idea per scene. Show the action or expression the learner needs to understand.
- Keep faces, gestures and important objects large enough to read on a phone.
- For vertical videos, reserve unobtrusive space for subtitles and platform overlays. Preview with the actual caption layout; avoid placing essential details near the right edge or bottom controls.
- Do not embed dialogue, captions, logos, watermarks or random lettering unless explicitly requested.
- Make eye direction and body orientation meaningful: customers look at vendors, speakers look at their conversational partners, and characters look toward objects they are interacting with.
- Match the script exactly: speaker roles, gender when specified, number of people, objects, actions, location and time of day.
- Use varied camera framing when it improves storytelling; avoid repetitive poses across sequential scenes.

## 6. Character and scene continuity
For every multi-image story or conversation, establish a character sheet or written reference before generating the sequence. Record:
- Character names or IDs, age impression, facial features, hairstyle, build, clothing and accessories.
- Setting, furniture, architecture, recurring objects, lighting and color palette.
- Relative positions and scene geography, including doors, windows, counters, bridges and railings when relevant.

Keep the same people recognizable throughout. Change clothing, props or environment only when the story requires it. Preserve left/right orientation where it matters to the action. Use the approved first image as a reference for subsequent images when possible.

**Emma and Lucas** are in most of the speaking videos, in every language (Emi and Riku in Japanese). No written character sheet for them exists yet. Until one does, give the generator the most recent approved picture of them as the reference, and say so in the prompt. Writing that sheet once, with one approved picture of each, is the cheapest way to keep them recognizable.

## 7. Cultural and linguistic authenticity
- Follow the requested country and setting, not merely the language of the dialogue.
- Japanese scenes set in Japan should use credible Japanese interiors, streets, shops and contemporary clothing; depict Japanese characters when specified.
- Apply equivalent care to Korean, French, Spanish-speaking, English-speaking and Myanmar settings. Do not assume every speaker lives in the country associated with the language. The Spanish course is Mexican.
- Avoid stereotypes, caricatures and mixing unrelated cultural motifs.
- If signage is essential, verify the language, spelling and script. Otherwise keep signs unobtrusive or blank.
- Respect the exact requested roles (for example, female customer and male shopkeeper) rather than substituting characters.

## 8. Reusable generation prompts
Replace bracketed fields with verified lesson details. Do not leave placeholders in a submitted generation prompt.

### General illustration
> Create a charming, polished digital storybook illustration for a language-learning lesson. Clean crisp lines, uncluttered composition, warm harmonious colors, gentle natural lighting, expressive believable faces and natural body language. Scene: [exact action and setting]. Characters: [approved character descriptions and roles]. Make the action immediately understandable. Correct anatomy, natural eye alignment and meaningful gaze. No embedded captions, watermarks or unnecessary lettering. [Aspect ratio].

### Vertical conversation series
> Create [number] separate vertical 9:16 illustrations for the following conversation scenes. Use the supplied approved illustration as the style and character reference. Preserve facial features, hairstyles, clothing, proportions, setting and recurring objects across the sequence. Each image depicts one specified moment: [scene descriptions]. Characters face their conversation partners naturally. Keep essential faces and gestures away from subtitle and platform-overlay areas. Clean crisp lines, charming expressions, warm colors, controlled detail. No text or watermarks.

### Landscape story sequence
> Create [number] separate 16:9 storybook illustrations for [story title]. Establish a consistent cast and setting using [approved reference]. Follow the scene-by-scene script exactly, preserving character identity, clothing, props and spatial continuity. Clear visual storytelling, clean crisp outlines, warm inviting colors, gentle shading, expressive but believable faces. No embedded captions. [Scene descriptions].

### Targeted correction
> Correct only [specific defect] in this approved illustration. Preserve all other characters, facial identity, clothing, pose, composition, background, lighting, style and aspect ratio. [Exact desired correction]. Do not introduce new objects or redesign the scene.

Example: correct the child's eye alignment so both eyes have a natural coordinated gaze toward the intended object; preserve the rest of the image.

## 9. Mandatory visual QA
Inspect every final image individually and compare the full sequence before approval.

- [ ] Correct scene, action, characters, speaker roles and cultural setting.
- [ ] Correct aspect ratio and final dimensions; no distortion or accidental crop.
- [ ] Consistent faces, hair, clothing, props and setting across scenes.
- [ ] Natural eye alignment, pupils and gaze; no unintended crossed eyes.
- [ ] Believable hands, fingers, limbs, anatomy and object contact.
- [ ] Characters look toward the correct person or object.
- [ ] Correct number of people and objects; no duplicates or unwanted additions.
- [ ] No broken geometry, floating objects, impossible furniture or inconsistent railings.
- [ ] No unwanted text, logos, watermarks or distracting artifacts.
- [ ] Readable at mobile size; compatible with actual subtitle placement.
- [ ] Matches approved reference style and communicates the intended lesson.

Reject material failures. Do not mark an image approved solely because an automated checker passes it. Use targeted editing for isolated defects instead of regenerating an entire sequence.

## 10. Files and cost
- The PNG in `_YOUTUBE` is the master. Never overwrite it; the JPGs can always be made again from it.
- Name pictures the way the tools expect: `1.png`, `2.png` … for a story, and for a video the names in `_VIDEO\README.md`. Do not invent another scheme.
- Keep the prompt with the script when a picture may need redoing. Nothing in the project records prompts today; that is a habit to start, not a rule being broken.
- Do not call paid FLUX or other image APIs without Marissa's approval. Estimate cost and number of outputs first.
- No unlimited retries. Generate a small sample, inspect it, then proceed only within the authorized budget. Stop and report repeated failures. Prefer a targeted correction to another full run.
- Do not delete, publish, upload or replace approved pictures without authorization.

## 11. Decision hierarchy
Explicit lesson instructions override defaults. Approved references override generic style descriptions. If a required character, location, aspect ratio or paid-generation authorization is missing, ask rather than inventing it. Creative choices not specified may be made within these standards and recorded when consequential.

## What changed from version 1.0
- Added "How it is done here": the picture step, the folders and the names already exist.
- File names: removed the proposed `lesson-id_scene-01` scheme. The build and the video tool find pictures by number, so another scheme would break both.
- Formats: the site's pictures are JPG, made by `1_images.bat`, not WebP.
- Removed the per-image log (source lesson, prompt, model, settings, revision, approval). Nothing keeps it today; one line asks for the prompt to be kept instead.
- Added Emma and Lucas, who are in most of the pictures and were not mentioned, and that the Spanish course is Mexican.
- The 16:9 size is no longer marked "proposed": 1920 is the long side `make_video.py` already uses.
