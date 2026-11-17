"""Audio for the lessons: ElevenLabs takes, leveling, Whisper check, upload to R2.

    python -E tools/audio.py                         the menu (what 2_audio.bat opens)
    python -E tools/audio.py status                  every lesson with clips still to make
    python -E tools/audio.py make <lesson>           make the missing clips
    python -E tools/audio.py make <lesson> --only 3 4     only these
    python -E tools/audio.py make <lesson> --redo 6 12    new takes (old clip and raw take are moved aside, not deleted)
    python -E tools/audio.py check <lesson>          Whisper on every clip, compared with the text
    python -E tools/audio.py upload <lesson>         send new/changed clips to R2, set the ?v= tag, rebuild the page
    python -E tools/audio.py balance                 ElevenLabs characters left
    python -E tools/audio.py shadow <dialogue>       draft a shadowing lesson from a dialogue: its sentences, as parts of the same clips
    python -E tools/audio.py chunks <shadow lesson>  find each chunk inside its clip and write its "t": [start, end]. Uses no characters

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
import base64, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.request

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


def level(src, dest, target, stereo):
    """loudnorm misses the target on short clips, so measure and apply the gain directly"""
    base = "pan=stereo|c0=c0|c1=c0,aresample=48000" if stereo else "aresample=44100"
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
    s = s.lower()
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
        print("Japanese is not compared automatically: read the 'heard' column.")
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
        voice = per.get(speaker.get(n)) or v["voice"]
        if not voice:
            sys.exit(f"no voice for {L['course']}: set it in assets/data/voices.json")
        rawf = os.path.join(raw, f"{n:02d}.mp3")
        tts(tx[n], voice, v["model"], rawf)
        got = level(rawf, lib.clip_file(L, n), v["lufs"], stereo=L["course"] == "eng")
        print(f"{n:02d}.mp3 {got:6.1f} LUFS  {tx[n]}")
    whisper(L, todo)
    left = missing(L)
    print(f"{L['id']}: {len(todo)} clip(s) made, {len(left)} still missing" + ("" if left else ". Next: upload."))


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


def upload(L):
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
    names = [f"{n:02d}.mp3" for n in tx]
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
    elif a[0] == "upload" and len(a) > 1:
        upload(get(a[1]))
    elif a[0] == "shadow" and len(a) > 1:
        shadow(get(a[1]))
    elif a[0] == "chunks" and len(a) > 1:
        chunks(get(a[1]))
    else:
        sys.exit(__doc__)
