"""Audio for the lessons: ElevenLabs takes, leveling, Whisper check, upload to R2.

    python -E tools/audio.py                         the menu (what 2_audio.bat opens)
    python -E tools/audio.py status                  every lesson with clips still to make
    python -E tools/audio.py make <lesson>           make the missing clips (a picture story: then its page clips too, see `pages`)
    python -E tools/audio.py make <lesson> --only 3 4     only these
    python -E tools/audio.py make <lesson> --redo 6 12    new takes (old clip and raw take are moved aside, not deleted)
    python -E tools/audio.py check <lesson>          Whisper on every clip, compared with the text
    python -E tools/audio.py upload <lesson>         send new/changed clips to R2, set the ?v= tag, rebuild the page
                                                     (a text lesson: its one recording and glossary clips; the tag is "audio_ver")
    python -E tools/audio.py trim <lesson>           cut the silence (and the breath) after the speech from clips made before the
                                                     tool did that itself; `trim all` for every lesson, --dry only lists. Then `upload`
    python -E tools/audio.py balance                 ElevenLabs characters left
    python -E tools/audio.py words <word list>       record the words of a word list or hotspot page that have no clip yet (named files:
                                                     maison.mp3); --redo maison.mp3 for a new take. Then `upload` as usual
    python -E tools/audio.py shadow <dialogue>       draft a shadowing lesson from a dialogue: its sentences, as parts of the same clips
    python -E tools/audio.py chunks <shadow lesson>  find each chunk inside its clip and write its "t": [start, end]. Uses no characters
    python -E tools/audio.py pages <story>           one clip per page of a picture story (p01.mp3 ...), read in one go, for Play page;
                                                     each chunk's place in it is written into the page. --redo 3 for a new take
    python -E tools/audio.py narrate <reading text>  read a reading text in one take (its "audio_file"), time every sentence in it,
                                                     and record its glossary words. --redo for a new take of the text

<lesson> is course/strand/slug, e.g. fr/speaking/boulangerie.

Wire: the lesson file's "aud_dir" is both the R2 folder and the folder under media/. Clips are
01.mp3, 02.mp3 ... in reading order. Raw takes go to media/elevenlabs-raw/<aud_dir with _>/.
Every take is asked for with the time of each character (NN.json beside the raw take): that is what `chunks` reads,
so shadowing chunks are played as parts of the line's clip and are never recorded a second time.
A lesson is "pending" while "aud_ext" is "mp3?v=pending"; upload replaces that with a dated tag.
Voices and loudness per course: assets/data/voices.json.
  English   48 kHz stereo 320 kbps, as the existing story and expression clips
  French, Japanese   mono 192 kbps, leveled by gain only
Needs ffmpeg and whisper; ELEVENLABS_API_KEY, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID
(User environment variables); for upload, boto3 + truststore. Run with -E, not -I.
"""
import array, base64, datetime, math, hashlib, json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C, BUCKET = lib.ROOT, lib.cfg(), "languages"
VOICES = json.load(open(os.path.join(ROOT, "assets", "data", "voices.json"), encoding="utf-8"))


def env(k):
    if os.environ.get(k):
        return os.environ[k].strip()
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            return winreg.QueryValueEx(h, k)[0].strip()
    except Exception:
        sys.exit(f"{k} is not set (User environment variables)")


def get(lid):
    lid = lid.replace("\\", "/").strip("/")
    for L in lib.lessons():
        if L["id"] == lid:
            return L
    sys.exit(f"no lesson {lid} (expected course/strand/slug)")


def texts(L):
    return {n: lib.spoken(t) for n, t in lib.clips(L)}


def who(L):
    """clip number -> speaker key, for lessons that give each speaker a voice"""
    if L.get("type") != "dialogue":
        return {}
    return {l["n"]: l.get("who") for sec in L["sections"] for l in sec["lines"]}


def paths(L):
    if L.get("aud_shared"):
        sys.exit(f'{L["id"]} reuses the clips of another lesson ("aud_shared"): make the audio there')
    if not os.path.isdir(os.path.join(ROOT, "media")):
        sys.exit("media/ is not in this folder yet: run SETUP.bat first, or existing clips would be made again")
    if not L.get("aud_dir") or L["aud_dir"].startswith("http"):
        sys.exit(f'{L["id"]}: set "aud_dir" in the lesson file first, e.g. "{L["id"]}/"')
    media = lib.media_dir(L)
    raw = os.path.join(ROOT, "media", "elevenlabs-raw", L["aud_dir"].strip("/").replace("/", "_"))
    return media, raw


def narrator(L):
    """(voice, model) when no speaker has a voice of their own: the lesson's "voice": {"narrator": id} and "voice_model",
    else, for a picture story, the course's "story_voice" and "story_model" (voices.json: French stories are read by
    Fr-Sophie with eleven_v4), else the course voice and model."""
    v = VOICES[L["course"]]
    story = L.get("type") == "reader"
    voice = (L.get("voice") or {}).get("narrator") or (story and v.get("story_voice")) or v["voice"]
    model = L.get("voice_model") or (story and v.get("story_model")) or v["model"]
    return voice, model


def missing(L):
    return [n for n in texts(L) if not os.path.exists(lib.clip_file(L, n) or "")]


def balance():
    req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": env("ELEVENLABS_API_KEY")})
    sub = json.load(urllib.request.urlopen(req, timeout=20))
    return sub["character_limit"] - sub["character_count"], sub["character_limit"]


def tts(text, voice, model, dest):
    """One take, saved to dest. The request also asks for the time of every character and saves that beside the
    take (NN.json), so `chunks` can find phrases inside the clip later without paying for new takes."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    body = json.dumps({"text": text, "model_id": model}).encode()
    head = {"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "/with-timestamps?output_format=mp3_44100_192", data=body, headers=head)) as r:
            got = json.load(r)
        open(dest, "wb").write(base64.b64decode(got["audio_base64"]))
        if got.get("alignment"):
            save_timings(dest[:-4] + ".json", text, "elevenlabs", got["alignment"])
        else:
            print("   ElevenLabs sent no timings with this take: `chunks` will use Whisper for it")
        return
    except urllib.error.HTTPError as err:
        if err.code not in (400, 404, 405, 422):   # anything else (key, quota ...) would fail the plain request too
            sys.exit(f"ElevenLabs refused the request ({err.code}): {err.read().decode(errors='replace')}")
        print(f"   no timings for this voice/model ({err.code}): plain take instead, `chunks` will use Whisper for it")
    try:   # a refused request is not billed, so this is still one take
        with urllib.request.urlopen(urllib.request.Request(url + "?output_format=mp3_44100_192", data=body, headers=head)) as r:
            open(dest, "wb").write(r.read())
    except urllib.error.HTTPError as err:
        sys.exit(f"ElevenLabs refused the request ({err.code}): {err.read().decode(errors='replace')}")


def save_timings(path, text, source, al):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"text": text, "source": source, "characters": al["characters"], "character_start_times_seconds": al["character_start_times_seconds"],
               "character_end_times_seconds": al["character_end_times_seconds"]}, open(path, "w", encoding="utf-8"), ensure_ascii=False)


def lufs(path, chain):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", chain + ",ebur128", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def speech_end(path):
    """Where the speech of a take ends, in seconds, or None when there is no tail worth cutting.
    ElevenLabs often adds a second of silence after a short line, sometimes with a breath in it, and Play all then
    stalls between clips. A last burst of sound is not speech when it is very faint (27 dB under the loudest part),
    or comes after a pause of 0.3 s and is still clearly quieter (12 dB under). The start is never touched: the
    times of the shadowing chunks count from it."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a, w = array.array("h", pcm[:len(pcm) // 2 * 2]), 320   # 20 ms windows
    db = [20 * math.log10(max(1.0, math.sqrt(sum(x * x for x in a[i:i + w]) / w)) / 32768) for i in range(0, len(a) - w + 1, w)]
    if not db:
        return None
    peak, runs = max(db), []
    for i, x in enumerate(db):   # runs of sound: [first window, the window after the last]
        if x > peak - 36:
            if runs and runs[-1][1] == i:
                runs[-1][1] = i + 1
            else:
                runs.append([i, i + 1])
    while len(runs) > 1:
        top, gap = max(db[runs[-1][0]:runs[-1][1]]), (runs[-1][0] - runs[-2][1]) * 0.02
        if top < peak - 27 or (gap >= 0.3 and top < peak - 12):
            runs.pop()
        else:
            break
    end = runs[-1][1] * 0.02 + 0.15
    return end if len(db) * 0.02 - end > 0.2 else None


def level(src, dest, target, stereo):
    """loudnorm misses the target on short clips, so measure and apply the gain directly"""
    base = "pan=stereo|c0=c0|c1=c0,aresample=48000" if stereo else "aresample=44100"
    end = speech_end(src)
    if end:
        base = f"atrim=end={end:.2f},afade=t=out:st={end - 0.06:.2f}:d=0.06," + base
    gain = target - lufs(src, base)
    for _ in range(3):   # the limiter shaves some loudness off; correct for it
        chain = f"{base},volume={gain:.2f}dB,alimiter=limit=0.891:level=false"
        got = lufs(src, chain)
        if abs(got - target) < 0.3:
            break
        gain += target - got
    out = ["-b:a", "320k"] if stereo else ["-ac", "1", "-b:a", "192k"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", chain, *out, dest], check=True)
    return got


def letters(s, lang):
    s = re.sub(r"\[[^\]]*\]", "", s).lower()   # a stage direction, [shocked], is acted, not said
    if lang == "fr":
        import unicodedata
        s = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z]", "", re.sub(r"\bok\b", "okay", s))


def whisper(L, nums):
    v, tx = VOICES[L["course"]], texts(L)
    files = [lib.clip_file(L, n) for n in nums]
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["whisper", *files, "--model", "small", "--language", v["whisper"], "--output_format", "txt", "--output_dir", tmp,
                        "--verbose", "False", "--fp16", "False"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        for n in nums:
            heard = open(os.path.join(tmp, f"{n:02d}.txt"), encoding="utf-8").read().strip()
            flag = ""
            if v["whisper"] in ("en", "fr") and letters(heard, v["whisper"]) != letters(tx[n], v["whisper"]):
                flag, bad = "   <<< check", bad + 1
            print(f"{n:02d}.mp3  {tx[n]}  | heard: {heard}{flag}")
    if v["whisper"] not in ("en", "fr"):
        print("Japanese and Korean are not compared automatically: read the 'heard' column.")
    else:
        print(f"Whisper: {bad} of {len(nums)} clip(s) to listen to (re-take only if the words are wrong).")


def make(L, only, redo):
    v = VOICES[L["course"]]
    media, raw = paths(L)
    os.makedirs(media, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    tx, speaker, per = texts(L), who(L), L.get("voice", {})
    todo = [n for n in tx if (not only or n in only) and (n in redo or not os.path.exists(lib.clip_file(L, n)))]
    if not todo:
        print(f"{L['id']}: nothing to make ({len(tx)} clips)")
        return
    if redo:
        aside = os.path.join(raw, "_replaced_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S"))
        os.makedirs(aside)
        for n in redo:
            for f, name in ((lib.clip_file(L, n), f"{n:02d}.mp3"), (os.path.join(raw, f"{n:02d}.mp3"), f"raw_{n:02d}.mp3"),
                            (os.path.join(raw, f"{n:02d}.json"), f"raw_{n:02d}.json")):   # the old take's timings go with it
                if os.path.exists(f):
                    shutil.move(f, os.path.join(aside, name))
    for n in todo:
        voice = per.get(speaker.get(n)) or narrator(L)[0]
        if not voice:
            sys.exit(f"no voice for {L['course']}: set it in assets/data/voices.json")
        rawf = os.path.join(raw, f"{n:02d}.mp3")
        tts(tx[n], voice, narrator(L)[1], rawf)   # "voice_model" in a lesson overrides the course model
        got = level(rawf, lib.clip_file(L, n), v["lufs"], stereo=L["course"] == "eng")
        print(f"{n:02d}.mp3 {got:6.1f} LUFS  {tx[n]}")
    whisper(L, todo)
    left = missing(L)
    print(f"{L['id']}: {len(todo)} clip(s) made, {len(left)} still missing" + ("" if left else ". Next: upload."))
    if L.get("type") == "reader" and not left:   # a picture story has two sets of clips: the chunks, and each page read in one go
        pages(L)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def trim(L, dry=False):
    """Level the clips again from their raw takes, now without the tail. Only clips that still have one; the old clip is moved aside."""
    if L.get("aud_shared") or L.get("audio_file") or not L.get("aud_dir") or L["aud_dir"].startswith("http"):
        return 0
    v = VOICES[L["course"]]
    media, raw = paths(L)
    aside, done, no_raw = os.path.join(raw, "_untrimmed_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S")), [], 0
    for n in texts(L):
        clip, rawf = lib.clip_file(L, n), os.path.join(raw, f"{n:02d}.mp3")
        if not os.path.exists(clip):
            continue
        if not os.path.exists(rawf):
            no_raw += 1
            continue
        end, was = speech_end(rawf), duration(clip)
        if not end or was - end < 0.2:
            continue
        done.append(n)
        if dry:
            continue
        os.makedirs(aside, exist_ok=True)
        shutil.move(clip, os.path.join(aside, f"{n:02d}.mp3"))
        level(rawf, clip, v["lufs"], stereo=L["course"] == "eng")
        print(f"   {n:02d}.mp3  {was:5.2f} s -> {duration(clip):5.2f} s")
    if done or no_raw:
        print(f"{L['id']}: {len(done)} clip(s) {'to trim' if dry else 'trimmed'}" + (f", {no_raw} without a raw take (left alone)" if no_raw else "") + ("" if dry or not done else ". Next: upload."))
    return len(done)


def plain(s):
    """letters and digits only, lower case, no accents: what is compared when a chunk is looked up inside a clip"""
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFD", s.casefold()) if ch.isalnum())


def timings(L, nums):
    """{clip number: the time of every character}, or None for a clip that is not on this computer. The times are
    saved with each take (NN.json beside the raw take). Clips made before that get theirs from Whisper, once:
    free, a little less exact, and saved in the same place."""
    raw = os.path.join(ROOT, "media", "elevenlabs-raw", L["aud_dir"].strip("/").replace("/", "_"))
    saved = lambda n: os.path.join(raw, f"{n:02d}.json")
    need = [n for n in nums if not os.path.exists(saved(n)) and os.path.exists(lib.clip_file(L, n) or "")]
    if need:
        print(f"Whisper is timing {len(need)} clip(s) that have no saved timings ...")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["whisper", *[lib.clip_file(L, n) for n in need], "--model", "small", "--language", VOICES[L["course"]]["whisper"],
                            "--word_timestamps", "True", "--output_format", "json", "--output_dir", tmp, "--verbose", "False", "--fp16", "False"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            for n in need:
                heard = json.load(open(os.path.join(tmp, f"{n:02d}.json"), encoding="utf-8"))
                chars, starts, ends = [], [], []
                for seg in heard["segments"]:
                    for w in seg.get("words", []):   # Whisper times whole words: spread each word's time evenly over its letters
                        word = w["word"].strip()
                        step = (w["end"] - w["start"]) / max(len(word), 1)
                        for i, ch in enumerate(word):
                            chars.append(ch)
                            starts.append(round(w["start"] + i * step, 3))
                            ends.append(round(w["start"] + (i + 1) * step, 3))
                save_timings(saved(n), heard.get("text", "").strip(), "whisper",
                             {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends})
    return {n: json.load(open(saved(n), encoding="utf-8")) if os.path.exists(saved(n)) else None for n in nums}


def chunk_times(L):
    """({chunk n: [start, end]}, [(chunk, reason it was not found)]) for the chunks that name a "clip"."""
    out, lost, groups = {}, [], {}
    for c in L.get("chunks", []):
        if c.get("clip"):
            groups.setdefault(c["clip"], []).append(c)
    known = timings(L, list(groups))
    for clip, group in groups.items():
        al = known[clip]
        if not al:
            lost += [(c, f"clip {clip:02d}.mp3 is not on this computer") for c in group]
            continue
        line = []   # one (letter, start, end) per letter the voice said
        for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
            line += [(x, a, b) for x in plain(ch)]
        said, pos, found = "".join(x[0] for x in line), 0, []
        for c in group:
            want = plain(lib.spoken(c["text"]))
            i = said.find(want, pos) if want else -1
            if i < 0 and want:
                i = said.find(want)   # chunks listed out of order
            if i < 0:
                lost.append((c, f"not found in clip {clip:02d}" + (" (Whisper heard: " + al.get("text", "") + ")" if al.get("source") == "whisper" else "")))
                continue
            found.append((c["n"], line[i][1], line[i + len(want) - 1][2]))
            pos = i + len(want)
        found.sort(key=lambda x: x[1])
        for k, (n, a, b) in enumerate(found):   # a little air around each chunk, but never into its neighbour
            lo, hi = a - 0.08, b + 0.15
            if k and found[k - 1][2] <= a:
                lo = max(lo, (found[k - 1][2] + a) / 2)
            if k + 1 < len(found) and b <= found[k + 1][1]:
                hi = min(hi, (b + found[k + 1][1]) / 2)
            out[n] = [round(max(lo, 0), 2), round(hi, 2)]
    return out, lost


def chunks(L):
    """Writes "t": [start, end] into every chunk of a shadowing lesson that names the "clip" it is part of."""
    if L.get("type") != "shadow" or not any(c.get("clip") for c in L.get("chunks", [])):
        sys.exit(f'{L["id"]}: no chunk names a clip. In a shadowing lesson, give each chunk the number of the clip it is part of: {{"text": "...", "clip": 3}}')
    if not L.get("aud_dir") or L["aud_dir"].startswith("http"):
        sys.exit(f'{L["id"]}: set "aud_dir" to the folder of the clips first')
    times, lost = chunk_times(L)
    doc = json.load(open(L["file"], encoding="utf-8"))
    for mine, c in zip(doc["chunks"], L["chunks"]):
        if c["n"] in times:
            mine["t"] = times[c["n"]]
        elif c.get("clip"):
            mine.pop("t", None)   # not found any more: play the whole clip rather than a stale range
    open(L["file"], "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    for c in L["chunks"]:
        if c["n"] in times:
            print(f"{c['n']:>3}  clip {c['clip']:02d}  {times[c['n']][0]:6.2f} - {times[c['n']][1]:6.2f}  {c['text']}")
    for c, why in lost:
        print(f"{c['n']:>3}  NO TIME: {why}  | {c['text']}")
    print(f"{L['id']}: {len(times)} chunk(s) timed, {len(lost)} not found. No ElevenLabs characters used.")
    import build
    build.main()


def page_text(p):
    """the whole text of a story page, as the voice reads it in one go"""
    return " ".join(lib.spoken(c[0]) for s in p["sentences"] for c in s)


def pages(L, redo=()):
    """A picture story: one more clip per page (p01.mp3, p02.mp3 ...), the whole page read in one go, so that Play page
    sounds like reading and not like a list of chunks. Each chunk is found inside its page's take from the character
    times saved with it, and written into the page as "t": {"<chunk>": [start, end]}: the page lights up each chunk as
    the voice reaches it. The chunk clips stay: a tap on a chunk still plays its own clip."""
    if L.get("type") != "reader":
        sys.exit(f'{L["id"]}: `pages` is for a picture story ("type": "reader")')
    v = VOICES[L["course"]]
    media, raw = paths(L)
    os.makedirs(media, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    voice, model = narrator(L)
    doc = json.load(open(L["file"], encoding="utf-8"))
    made, lost = [], []
    for k, (p, mine) in enumerate(zip(L["pages"], doc["pages"]), 1):
        name, text = f"p{k:02d}", page_text(p)
        dest, rawf, rawj = os.path.join(media, name + ".mp3"), os.path.join(raw, name + ".mp3"), os.path.join(raw, name + ".json")
        if not os.path.exists(dest) or k in redo:
            if os.path.exists(dest):   # a new take: the old one is moved aside, not deleted
                aside = os.path.join(raw, "_replaced_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S"))
                os.makedirs(aside, exist_ok=True)
                for f in (dest, rawf, rawj):
                    if os.path.exists(f):
                        shutil.move(f, os.path.join(aside, ("raw_" if f != dest else "") + os.path.basename(f)))
            tts(text, voice, model, rawf)
            got = level(rawf, dest, v["lufs"], stereo=L["course"] == "eng")
            made.append(k)
            print(f"{name}.mp3 {got:6.1f} LUFS  {text}")
        if not os.path.exists(rawj):
            lost.append(f"{name}: no character times saved with this take: Play page will play the chunks one by one")
            mine.pop("audio", None); mine.pop("t", None)
            continue
        al = json.load(open(rawj, encoding="utf-8"))
        line = []   # one (letter, start, end) per letter the voice said
        for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
            line += [(x, a, b) for x in plain(ch)]
        said, pos, t = "".join(x[0] for x in line), 0, {}
        for c in (c for s in p["sentences"] for c in s):
            want = plain(lib.spoken(c[0]))
            i = said.find(want, pos) if want else -1
            if i < 0:
                lost.append(f"{name}: chunk {c[1]} not found: {c[0]}")
                continue
            t[str(c[1])] = [round(line[i][1], 2), round(line[i + len(want) - 1][2], 2)]
            pos = i + len(want)
        mine["audio"], mine["t"] = name, t
    open(L["file"], "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    for x in lost:
        print("   " + x)
    if made:
        bad = 0
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["whisper", *[os.path.join(media, f"p{k:02d}.mp3") for k in made], "--model", "small", "--language", v["whisper"],
                            "--output_format", "txt", "--output_dir", tmp, "--verbose", "False", "--fp16", "False"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            for k in made:
                heard = " ".join(open(os.path.join(tmp, f"p{k:02d}.txt"), encoding="utf-8").read().split())
                if v["whisper"] in ("en", "fr") and letters(heard, v["whisper"]) != letters(page_text(L["pages"][k - 1]), v["whisper"]):
                    bad += 1
                    print(f"   check: p{k:02d}.mp3  heard: {heard}")
        print(f"Whisper: {bad} of {len(made)} page clip(s) to listen to. New take: python -E tools\\audio.py pages {L['id']} --redo 3")
    print(f"{L['id']}: {len(made)} page clip(s) made, {len(L['pages']) - len(made)} already there. Next: upload.")
    import build
    build.main()


def narrate(L, redo=False):
    """A reading text ("type": "text") read in one take: saved as its "audio_file" under media/, and each sentence gets
    "t": [start, end] from the character times of that take, so the page plays and follows it sentence by sentence.
    The glossary words that have no clip yet are recorded too, in the same voice (01.mp3 ... in "glossary_dir"; a word
    may have "say": what the voice reads). --redo makes a new take of the text. Then `upload`, as for any reading text."""
    if L.get("type") != "text" or not L.get("audio_file") or L["audio_file"].startswith("http"):
        sys.exit(f'{L["id"]}: `narrate` is for a reading text with "audio_file" set, e.g. "lessons/read/asia/audio.mp3"')
    v = VOICES[L["course"]]
    voice, model = narrator(L)
    dest = os.path.join(ROOT, "media", *L["audio_file"].split("/"))
    raw = os.path.join(ROOT, "media", "elevenlabs-raw", os.path.dirname(L["audio_file"]).replace("/", "_"))
    rawf, rawj = os.path.join(raw, "narration.mp3"), os.path.join(raw, "narration.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    doc = json.load(open(L["file"], encoding="utf-8"))
    paras = doc["paragraphs"]
    head = [lib.spoken(doc[k]) for k in ("title", "subtitle") if doc.get(k)]   # the take opens with the title and subtitle, as the user records them
    text = "\n\n".join(head + [" ".join(lib.spoken(s["text"]) for s in p) for p in paras])   # a blank line between paragraphs: a longer pause
    if not os.path.exists(dest) or redo:
        if os.path.exists(dest):   # a new take: the old one is moved aside, not deleted
            aside = os.path.join(raw, "_replaced_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S"))
            os.makedirs(aside, exist_ok=True)
            for f in (dest, rawf, rawj):
                if os.path.exists(f):
                    shutil.move(f, os.path.join(aside, os.path.basename(f)))
        tts(text, voice, model, rawf)
        got = level(rawf, dest, v["lufs"], stereo=L["course"] == "eng")
        print(f"{L['audio_file']} {got:6.1f} LUFS, {len(text)} characters, {duration(dest):.0f} s")
    if not os.path.exists(rawj):
        sys.exit("no character times were saved with this take: the sentences cannot be timed")
    al = json.load(open(rawj, encoding="utf-8"))
    line = []   # one (letter, start, end) per letter the voice said
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        line += [(x, a, b) for x in plain(ch)]
    said, pos, found, lost = "".join(x[0] for x in line), 0, [], []
    sents = [s for p in paras for s in p]
    for s in sents:
        want = plain(lib.spoken(s["text"]))
        i = said.find(want, pos) if want else -1
        if i < 0:
            lost.append(s["text"])
            s.pop("t", None)
            continue
        found.append((s, line[i][1], line[i + len(want) - 1][2]))
        pos = i + len(want)
    for k, (s, a, b) in enumerate(found):   # a little air around each sentence, but never into its neighbour
        lo, hi = a - 0.1, b + 0.25
        if k:
            lo = max(lo, (found[k - 1][2] + a) / 2)
        if k + 1 < len(found):
            hi = min(hi, (b + found[k + 1][1]) / 2)
        s["t"] = [round(max(lo, 0), 2), round(hi, 2)]
    gd, made = L.get("glossary_dir", ""), 0
    if gd and doc.get("glossary"):
        gdir = os.path.join(ROOT, "media", *gd.strip("/").split("/"))
        graw = os.path.join(ROOT, "media", "elevenlabs-raw", gd.strip("/").replace("/", "_"))
        os.makedirs(gdir, exist_ok=True)
        os.makedirs(graw, exist_ok=True)
        for i, g in enumerate(doc["glossary"], 1):
            name = g.get("audio") or f"{i:02d}.mp3"
            if not os.path.exists(os.path.join(gdir, name)):
                say = lib.spoken(g.get("say") or g["word"]).replace(" / ", ", ")
                tts(say, voice, model, os.path.join(graw, name))
                level(os.path.join(graw, name), os.path.join(gdir, name), v["lufs"], stereo=L["course"] == "eng")
                made += 1
            g["audio"] = name
    open(L["file"], "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    for x in lost:
        print(f"   NOT FOUND in the take (no time): {x}")
    print(f"{L['id']}: {len(found)} of {len(sents)} sentence(s) timed, {made} glossary clip(s) made. Listen, then: upload.")
    import build
    build.main()


def shadow(L):
    """Drafts a shadowing lesson from a dialogue: each sentence becomes a chunk of its line's clip. No new takes."""
    if L.get("type") != "dialogue":
        sys.exit(f"{L['id']} is not a dialogue")
    if "pronunciation" not in C["courses"][L["course"]]["strands"]:
        sys.exit(f"{L['course']} has no pronunciation strand in site.json")
    dest = os.path.join(ROOT, "content", L["course"], "pronunciation", f"shadow_{L['slug']}.json")
    if os.path.exists(dest):
        sys.exit(f"{os.path.relpath(dest, ROOT)} is already there: edit its chunks, then run `chunks {L['course']}/pronunciation/shadow_{L['slug']}`")
    parts = [{"text": p.strip(), "clip": n} for n, text in lib.clips(L) for p in re.split(r"(?<=[.!?…])\s+|(?<=[。！？])", lib.spoken(text)) if p.strip()]
    doc = {"title": "Shadowing: " + L.get("title", L["slug"]), "level": L.get("level"), "topic": "Shadowing practice", "type": "shadow",
           "aud_shared": True, "aud_dir": L["aud_dir"], "aud_ext": L.get("aud_ext", "mp3?v=pending"), "chunks": parts}
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps({k: v for k, v in doc.items() if v is not None}, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {os.path.relpath(dest, ROOT)}: {len(parts)} chunks from {len(lib.clips(L))} clips.")
    print(f"Split or join chunks there if you like (keep each chunk's \"clip\"), then: python -E tools\\audio.py chunks {L['course']}/pronunciation/shadow_{L['slug']}")


def word_file(text):
    """maison -> maison.mp3, porte d'entrée -> porte_d_entree.mp3: the file a word's clip is saved under"""
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", lib.spoken(text).lower().replace("œ", "oe").replace("æ", "ae")) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") + ".mp3"


def named_words(doc):
    """every word of a word list, every dot of a hotspot page and every term of a family tree (the same dicts, so they can be changed in place)"""
    return ([w for g in doc.get("groups", []) for w in g.get("words", [])] + [p for s in doc.get("slides", []) for p in s.get("spots", [])]
            + list(doc.get("terms", {}).values()))


def words(L, redo=()):
    """A word list or a hotspot page: records every word that has no clip yet, as a named file in "glossary_dir"
    (maison.mp3), and writes its name into the lesson file as "audio". A word list and its hotspot page share the
    folder, so a word is recorded once. Single words are made with the course's "word_model" in voices.json
    (eleven_v3 for English, which reads short sounds better; eleven_v4 when none is set)."""
    if L.get("type") not in ("words", "hotspots", "family") or not L.get("glossary_dir"):
        sys.exit(f'{L["id"]}: this command is for a word list, hotspot page or family tree with "glossary_dir" set, e.g. "lessons/noun/house/"')
    v, gd = VOICES[L["course"]], L["glossary_dir"]
    if not v["voice"]:
        sys.exit(f"no voice for {L['course']}: set it in assets/data/voices.json")
    media = lib.find("media/" + gd) or os.path.join(ROOT, "media", *gd.strip("/").split("/"))
    raw = os.path.join(ROOT, "media", "elevenlabs-raw", gd.strip("/").replace("/", "_"))
    os.makedirs(media, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    doc = json.load(open(L["file"], encoding="utf-8"))
    made = {}
    # "voices": a list of voice ids; each group of words is read by the next one in turn (a pair to compare stays in one voice)
    turn = doc.get("voices") or []
    todo = [(w, w.get("voice") or (turn[gi % len(turn)] if turn else v["voice"])) for gi, g in enumerate(doc.get("groups", [])) for w in g.get("words", [])]
    first = turn[0] if turn else v["voice"]   # hotspots and family terms: the lesson's first voice, unless a word has its own
    todo += [(p, p.get("voice") or first) for s in doc.get("slides", []) for p in s.get("spots", [])]
    todo += [(t, t.get("voice") or first) for t in doc.get("terms", {}).values()]   # a family tree: one clip per word
    numbered = L["course"] in ("jap", "kor") or doc.get("clip_names") == "number"   # romaji cannot name a file: obasan and obāsan would collide
    taken = {w["audio"] for w, _ in todo if w.get("audio")}
    for k, (w, voice) in enumerate(todo, 1):
        say = lib.spoken(w.get("say") or w["fr"]).replace(" / ", ", ")   # "say": what the voice reads, when it is not the text shown
        name = w.get("audio")
        if not name and numbered:
            name = next(f"{i:03d}.mp3" for i in range(k, 2000) if f"{i:03d}.mp3" not in taken)
            taken.add(name)
        name = name or word_file(w["fr"])
        dest = os.path.join(media, name)
        if name not in made and (not os.path.exists(dest) or name in redo):
            if os.path.exists(dest):   # a new take: the old clip is moved aside, not deleted
                aside = os.path.join(raw, "_replaced_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S"))
                os.makedirs(aside, exist_ok=True)
                shutil.move(dest, os.path.join(aside, name))
            tts(say, voice, v.get("word_model", "eleven_v4"), os.path.join(raw, name))
            level(os.path.join(raw, name), dest, v["lufs"], stereo=L["course"] == "eng")
            made[name] = say
        w["audio"] = name
    open(L["file"], "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    total = len({w["audio"] for w in named_words(doc)})
    print(f"{L['id']}: {len(made)} clip(s) made ({sum(map(len, made.values()))} characters), {total - len(made)} already there")
    if made:
        bad = 0
        with tempfile.TemporaryDirectory() as tmp:   # single words need the bigger Whisper model to be judged fairly
            subprocess.run(["whisper", *[os.path.join(media, n) for n in made], "--model", "medium", "--language", v["whisper"], "--output_format", "txt",
                            "--output_dir", tmp, "--verbose", "False", "--fp16", "False"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            for n, say in made.items():
                heard = open(os.path.join(tmp, n[:-4] + ".txt"), encoding="utf-8").read().strip()
                if v["whisper"] not in ("en", "fr"):   # Japanese comes back in other characters than it was written in: listed, not judged
                    print(f"   {n}  {say}  | heard: {heard}")
                elif plain(heard) != plain(say):
                    bad += 1
                    print(f"   check: {n}  '{say}'  heard as '{heard}'")
        print(f"Whisper: {bad} of {len(made)} clip(s) to listen to. New take: python -E tools\\audio.py words {L['id']} --redo <file.mp3>. Then: upload.")
    import build
    build.main()


def r2():
    import truststore
    truststore.inject_into_ssl()   # use the Windows certificate store
    import boto3
    return boto3.client("s3", endpoint_url=f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com", aws_access_key_id=env("R2_ACCESS_KEY_ID"),
                        aws_secret_access_key=env("R2_SECRET_ACCESS_KEY"), region_name="auto")


def upload_recording(L):
    """A lesson with one recording for the whole text ("audio_file"): sends that file and the lesson's own numbered
    glossary clips to R2, and stamps "audio_ver" in the lesson file when anything was new. The file keeps its name:
    the tag is what makes browsers and the CDN fetch a new take."""
    files = {}   # R2 key -> file on this computer
    if L.get("audio_file"):
        f = lib.find("media/" + L["audio_file"])
        if not f:
            sys.exit(f'{L["audio_file"]} is not in media/: nothing to upload')
        files[L["audio_file"]] = f
    gd = L.get("glossary_dir", "")
    heads = [{"audio": L["title_audio"]}] if L.get("title_audio") else []   # the recorded title and group headings of a word list
    heads += [{"audio": g["audio"]} for g in L.get("groups", []) if g.get("audio")]
    for w in named_words(L) + heads:   # a word list or hotspot page: its named clips
        if gd and w.get("audio"):
            p = lib.find("media/" + gd + w["audio"])
            if not p:
                sys.exit(f'{gd}{w["audio"]} is not in media/: not uploading')
            files[gd + w["audio"]] = p
    if not files:
        sys.exit(f'{L["id"]}: nothing to upload yet (record the words first: python -E tools\\audio.py words {L["id"]})')
    for g in L.get("glossary", []):
        if gd and g.get("audio"):
            p = lib.find("media/" + gd + g["audio"])
            if not p:
                sys.exit(f'glossary clip {gd}{g["audio"]} is not in media/: not uploading')
            files[gd + g["audio"]] = p
    md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    s3, online = r2(), {}
    for prefix in sorted({k.rsplit("/", 1)[0] + "/" for k in files}):
        for pg in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
            online.update({o["Key"]: o["ETag"].strip('"') for o in pg.get("Contents", [])})
    todo = [k for k, p in files.items() if online.get(k) != md5(p)]
    for k in todo:
        s3.upload_file(files[k], BUCKET, k, ExtraArgs={"ContentType": "audio/mp4" if k.endswith(".m4a") else "audio/mpeg"})
    print(f"R2 {L.get('audio_file') or gd}: {len(files) - len(todo)} already online, {len(todo)} uploaded")
    def stamp():
        ver = datetime.datetime.now().strftime("%y%m%d%H%M")
        src = open(L["file"], encoding="utf-8").read()
        if '"audio_ver"' in src:
            new = re.sub(r'"audio_ver":\s*"[^"]*"', f'"audio_ver": "{ver}"', src, count=1)
        else:
            key = "audio_file" if L.get("audio_file") else "glossary_dir"   # the tag goes on the line after it
            new = re.sub(r'^(\s*)("' + key + r'":\s*"[^"]*",?)[ \t]*$', lambda m: f'{m.group(1)}{m.group(2).rstrip(",")},\n{m.group(1)}"audio_ver": "{ver}",', src, count=1, flags=re.M)
        if new == src:
            sys.exit(f'could not find "{key}" in {L["file"]}: add "audio_ver": "{ver}" by hand')
        json.loads(new)   # never leave a lesson file that does not parse
        open(L["file"], "w", encoding="utf-8", newline="\n").write(new)
        print(f"audio_ver set to {ver}")
        return ver

    def cdn(ver):   # the clips the CDN does not serve as they are on this computer, under this tag
        return [k for k, p in files.items()   # old clips have spaces and apostrophes in their names
                if hashlib.md5(subprocess.run(["curl", "-s", f"{C['media_base']}{urllib.parse.quote(k)}?v={ver}"], capture_output=True).stdout).hexdigest() != md5(p)]

    ver, fresh = L.get("audio_ver", ""), bool(todo or not L.get("audio_ver"))
    if fresh:
        ver = stamp()
    wrong = cdn(ver)
    if wrong and not fresh:   # a clip shared with another lesson was sent by that lesson's upload: this one needs a new tag too
        print(f"CDN still serves the old {', '.join(wrong)} under this lesson's tag")
        ver = stamp()
        wrong = cdn(ver)
    print(f"CDN check: {len(files) - len(wrong)}/{len(files)} match" + (f", DIFFERENT: {wrong}" if wrong else ""))
    import build
    build.main()
    if wrong:
        sys.exit("the CDN is serving different files: upload again to get a new tag")


def upload(L):
    if L.get("audio_file") or L.get("type") in ("words", "hotspots", "family"):
        return upload_recording(L)
    media, _ = paths(L)
    tx = texts(L)
    gone = missing(L)
    if gone:
        sys.exit(f"missing clips, not uploading: {gone}")
    import truststore
    truststore.inject_into_ssl()   # use the Windows certificate store
    import boto3
    s3 = boto3.client("s3", endpoint_url=f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com", aws_access_key_id=env("R2_ACCESS_KEY_ID"),
                      aws_secret_access_key=env("R2_SECRET_ACCESS_KEY"), region_name="auto")
    prefix = L["aud_dir"].strip("/") + "/"
    names = [f"{n:02d}.mp3" for n in tx] + [p["audio"] + ".mp3" for p in L.get("pages", []) if p.get("audio")]   # a story's page clips too
    md5 = lambda f: hashlib.md5(open(os.path.join(media, f), "rb").read()).hexdigest()
    online = {}
    for pg in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        online.update({o["Key"]: o["ETag"].strip('"') for o in pg.get("Contents", [])})
    todo = [f for f in names if online.get(prefix + f) != md5(f)]
    for f in todo:
        s3.upload_file(os.path.join(media, f), BUCKET, prefix + f, ExtraArgs={"ContentType": "audio/mpeg"})
    print(f"R2 {prefix}: {len(online)} already online, {len(todo)} uploaded")
    ext = L.get("aud_ext", "mp3?v=pending")
    if todo or "pending" in ext:
        ext = "mp3?v=" + datetime.datetime.now().strftime("%y%m%d%H%M")
        src = open(L["file"], encoding="utf-8").read()
        new = re.sub(r'"aud_ext":\s*"[^"]*"', f'"aud_ext": "{ext}"', src, count=1)
        if new == src:
            sys.exit(f'could not find "aud_ext" in {L["file"]}: set it to "{ext}" by hand')
        open(L["file"], "w", encoding="utf-8", newline="\n").write(new)
        print(f"aud_ext set to {ext}")
        for S in lib.lessons():   # lessons that play these same clips ("aud_shared") follow the new tag
            if S.get("aud_shared") and S.get("aud_dir") == L["aud_dir"] and S["id"] != L["id"]:
                old = open(S["file"], encoding="utf-8").read()
                upd = re.sub(r'"aud_ext":\s*"[^"]*"', f'"aud_ext": "{ext}"', old, count=1)
                if upd != old:
                    open(S["file"], "w", encoding="utf-8", newline="\n").write(upd)
                    print(f"aud_ext set in {S['id']} too")
    # only now ask the CDN: a request for a clip that is not there yet is cached as "not found" for 4 hours
    wrong = []
    for f in names:
        got = subprocess.run(["curl", "-s", f"{C['media_base']}{prefix}{f[:-4]}.{ext}"], capture_output=True).stdout
        if hashlib.md5(got).hexdigest() != md5(f):
            wrong.append(f)
    print(f"CDN check: {len(names) - len(wrong)}/{len(names)} match" + (f", DIFFERENT: {wrong}" if wrong else ""))
    import build
    build.main()
    if wrong:
        sys.exit("the CDN is serving different files: upload again to get a new tag")


def status(show=True):
    rows = []
    if not os.path.isdir(os.path.join(ROOT, "media")):
        sys.exit("media/ is not in this folder yet: run SETUP.bat first")
    for L in lib.lessons():
        tx = texts(L)
        if not tx or not L.get("aud_dir") or L["aud_dir"].startswith("http") or L.get("aud_shared"):
            continue
        miss = missing(L)
        if miss or lib.pending(L):
            rows.append((L, len(tx), miss, sum(len(tx[n]) for n in miss)))
    if show:
        for i, (L, total, miss, chars) in enumerate(rows, 1):
            state = "ready to upload" if not miss else f"{total - len(miss)}/{total} clips"
            print(f"{i:>3}  {L['id']:<44} {state:<16} {chars:>6,} characters to make")
        print(f"{len(rows)} lesson(s) need audio work; {sum(r[3] for r in rows):,} characters in all")
    return rows


def menu():
    while True:
        print("\n=== Audio ===")
        try:
            left, limit = balance()
            print(f"ElevenLabs: {left:,} characters left of {limit:,}")
        except SystemExit as err:
            print(err)
        except Exception as err:
            print(f"ElevenLabs balance: could not read it ({err})")
        rows = status()
        if not rows:
            input("Nothing to do. Press Enter to close.")
            return
        pick = input("\nLesson number (Enter to quit): ").strip()
        if not pick.isdigit() or not 1 <= int(pick) <= len(rows):
            return
        L, total, miss, chars = rows[int(pick) - 1]
        print(f"\n{L['id']}: {len(miss)} of {total} clips missing, about {chars:,} characters")
        print("  1  make ONE clip (the next missing one)\n  2  make ALL missing clips\n  3  new takes of some clips\n  4  Whisper check all\n  5  upload to R2\n  6  offline copy")
        act = input("Choice: ").strip()
        try:
            if act == "1" and miss:
                make(L, [miss[0]], [])
            elif act == "2" and miss and input(f"Use about {chars:,} characters? (y/n) ").lower() == "y":
                make(L, [], [])
            elif act == "3":
                nums = [int(x) for x in re.findall(r"\d+", input("Clip numbers: "))]
                if nums:
                    make(L, nums, nums)
            elif act == "4":
                whisper(L, [n for n in texts(L) if n not in miss])
            elif act == "5" and input("Upload to R2? (y/n) ").lower() == "y":
                upload(L)
            elif act == "6":
                subprocess.run([sys.executable, "-E", os.path.join(ROOT, "tools", "offline.py"), L["id"]])
        except SystemExit as err:
            print(err)


if __name__ == "__main__":
    a = sys.argv[1:]
    nums = lambda flag: [int(x) for x in a[a.index(flag) + 1:] if x.isdigit()] if flag in a else []
    if not a:
        menu()
    elif a[0] == "status":
        status()
    elif a[0] == "balance":
        print("ElevenLabs: {:,} characters left of {:,}".format(*balance()))
    elif a[0] == "make" and len(a) > 1:
        redo = nums("--redo")
        make(get(a[1]), nums("--only") or redo, redo)
    elif a[0] == "check" and len(a) > 1:
        L = get(a[1])
        whisper(L, [n for n in texts(L) if n not in missing(L)])
    elif a[0] == "trim" and len(a) > 1:
        if a[1] == "all":
            n = sum(trim(L, "--dry" in a) for L in lib.lessons())
            print(f"{n} clip(s) in all")
        else:
            trim(get(a[1]), "--dry" in a)
    elif a[0] == "upload" and len(a) > 1:
        upload(get(a[1]))
    elif a[0] == "shadow" and len(a) > 1:
        shadow(get(a[1]))
    elif a[0] == "chunks" and len(a) > 1:
        chunks(get(a[1]))
    elif a[0] == "pages" and len(a) > 1:
        pages(get(a[1]), nums("--redo"))
    elif a[0] == "narrate" and len(a) > 1:
        narrate(get(a[1]), "--redo" in a)
    elif a[0] == "words" and len(a) > 1:
        words(get(a[1]), [x for x in a[a.index("--redo") + 1:]] if "--redo" in a else [])
    else:
        sys.exit(__doc__)
