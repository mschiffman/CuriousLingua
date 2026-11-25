"""A dialogue recorded scene by scene, then cut into the usual one-clip-per-line files. What record_scenes.bat runs.

    python -E tools/scene.py                          asks for the lesson and the scenes
    python -E tools/scene.py <lesson>                 every scene of the lesson
    python -E tools/scene.py <lesson> --only 1 3      only scenes 1 and 3
    python -E tools/scene.py <lesson> --list          only show the scenes and their sizes

A scene is one section of a dialogue lesson. ElevenLabs gets the whole scene in one request (text to dialogue), so the
two voices play it together, and it sends back the time at which every line starts and ends. The scene is then
  1. leveled as a whole, once, to the course loudness (so a whisper stays quieter than a shout),
  2. cut at those times into the lesson's clips, 01.mp3, 02.mp3 ... (the clips it replaces are moved aside, not deleted),
  3. checked with Whisper,
and the whole scene is also saved, with a subtitle file timed to the line, for the video of the scene.

A stage direction goes in a line's "say": the page shows "text", the voices get "say".
    { "who": "E", "text": "Elle se repose.", "say": "[shocked] Elle se repose ?", "tr": { "en": "It's resting." } }
Each speaker needs a voice in the lesson file: "voice": { "E": "<voice id>", "L": "<voice id>" }.
The model is the lesson's "voice_model", else the course model in assets/data/voices.json; if ElevenLabs refuses that
model for dialogue, the request is sent again with its own default (a refused request is not billed).
Afterwards: listen on the page (preview.bat), then `python -E tools\\audio.py upload <lesson>`."""
import base64
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio
import lib

API = "https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps?output_format=mp3_44100_192"
REELS = r"G:\My Drive\_YOUTUBE\_VIDEOS\PROCESS"   # the scene recordings for videos go in a folder here (else beside the raw takes)
LEAD, TAIL = 0.05, 0.15      # seconds kept before and after a line when it is cut out
MAX_CHARS = 2000             # ElevenLabs: at most this many characters in one dialogue request


def scenes(L):
    """[(scene number, title, [line, ...])]; a line keeps its clip number "n"."""
    if L.get("type") != "dialogue" or not L.get("sections"):
        sys.exit(f"{L['id']} is not a dialogue with sections: nothing to record by scene")
    return [(k, sec.get("title") or f"Scene {k}", sec["lines"]) for k, sec in enumerate(L["sections"], 1)]


def voiced(l):
    """what the voice is given: the same choice as the line-by-line tool, stage directions included"""
    return lib.spoken(l.get("say") or l.get("kana") or l.get("hangul") or l.get("text") or l.get("romaji", ""))


def shown(l, french):
    """what a subtitle shows: the line as the page prints it"""
    text = lib.spoken(l.get("text") or l.get("romaji") or l.get("rom") or l.get("kana") or l.get("hangul") or "")
    if french:   # no line break before ? ! : ; or inside « »
        text = re.sub(r" ([?!:;»])", "\u00a0\\1", text).replace("« ", "«\u00a0")
    return text


def post(inputs, model):
    body = {"inputs": inputs}
    if model:
        body["model_id"] = model
    head = {"xi-api-key": audio.env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(API, data=json.dumps(body).encode(), headers=head), timeout=300) as r:
        return json.load(r)


def dialogue(inputs, model):
    """(the answer, the model that made it)"""
    try:
        return post(inputs, model), model
    except urllib.error.HTTPError as err:
        why = err.read().decode(errors="replace")
        if not model or err.code not in (400, 404, 422):
            sys.exit(f"ElevenLabs refused the request ({err.code}): {why}")
        print(f"   {model} was refused for dialogue ({err.code}): {why[:300]}\n   trying again with the ElevenLabs default model")
    try:
        return post(inputs, None), "the ElevenLabs default"
    except urllib.error.HTTPError as err:
        sys.exit(f"ElevenLabs refused the request ({err.code}): {err.read().decode(errors='replace')}")


def line_times(got, count):
    """[(start, end)] of each line of the scene, in seconds, from the voice segments ElevenLabs sent"""
    spans = {}
    for s in got.get("voice_segments") or []:
        i = s["dialogue_input_index"]
        a, b = spans.get(i, (s["start_time_seconds"], s["end_time_seconds"]))
        spans[i] = (min(a, s["start_time_seconds"]), max(b, s["end_time_seconds"]))
    lost = [i + 1 for i in range(count) if i not in spans or spans[i][1] <= spans[i][0]]
    if lost:
        return None, f"no times for line(s) {lost} of the scene"
    times = [spans[i] for i in range(count)]
    if any(times[i + 1][0] < times[i][0] for i in range(count - 1)):
        return None, "the lines came back out of order"
    return times, ""


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def record(L, k, title, lines, model, aside):
    """One scene: ask ElevenLabs, level, cut. Returns the clip numbers it made."""
    v = audio.VOICES[L["course"]]
    media, raw = audio.paths(L)
    os.makedirs(media, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    per, stereo, french = L.get("voice", {}), L["course"] == "eng", L["course"] == "fr"
    inputs = [{"text": voiced(l), "voice_id": per.get(l.get("who"))} for l in lines]
    rawf = os.path.join(raw, f"scene_{k:02d}.mp3")

    got, used = dialogue(inputs, model)
    if os.path.exists(rawf):   # the scene's last take goes aside with the clips cut from it
        os.makedirs(aside, exist_ok=True)
        for f in (rawf, rawf[:-4] + ".json"):
            if os.path.exists(f):
                shutil.move(f, os.path.join(aside, os.path.basename(f)))
    open(rawf, "wb").write(base64.b64decode(got.pop("audio_base64")))
    json.dump({"lines": [l["n"] for l in lines], "inputs": inputs, "model": used, **got}, open(rawf[:-4] + ".json", "w", encoding="utf-8"), ensure_ascii=False)
    times, why = line_times(got, len(lines))
    if not times:
        sys.exit(f"scene {k}: {why}. The recording is kept ({rawf}) but was not cut: the old clips are untouched.")

    # 1. one gain for the whole scene (the same measuring as the line-by-line tool, applied once)
    base = "pan=stereo|c0=c0|c1=c0,aresample=48000" if stereo else "aresample=44100"
    length = audio.duration(rawf)
    end = min(length, max(audio.speech_end(rawf) or length, times[-1][1] + TAIL))
    whole = f"atrim=end={end:.3f},afade=t=out:st={max(0, end - 0.06):.3f}:d=0.06,{base}"
    gain = v["lufs"] - audio.lufs(rawf, whole)
    for _ in range(3):
        finish = f"volume={gain:.2f}dB,alimiter=limit=0.891:level=false"
        loud = audio.lufs(rawf, f"{whole},{finish}")
        if abs(loud - v["lufs"]) < 0.3:
            break
        gain += v["lufs"] - loud
    out = ["-b:a", "320k"] if stereo else ["-ac", "1", "-b:a", "192k"]

    # 2. cut: each line with a little air, never into its neighbours
    cuts = []
    for i, (a, b) in enumerate(times):
        lo = 0.0 if i == 0 else (times[i - 1][1] + a) / 2
        hi = end if i == len(times) - 1 else (b + times[i + 1][0]) / 2
        cuts.append((max(lo, a - LEAD), min(hi, b + TAIL, end)))
    made = []
    for l, (a, b) in zip(lines, cuts):
        n, clip = l["n"], lib.clip_file(L, l["n"])
        old = [(clip, f"{n:02d}.mp3"), (os.path.join(raw, f"{n:02d}.mp3"), f"raw_{n:02d}.mp3"), (os.path.join(raw, f"{n:02d}.json"), f"raw_{n:02d}.json")]
        if any(os.path.exists(f) for f, _ in old):
            os.makedirs(aside, exist_ok=True)
            for f, name in old:
                if os.path.exists(f):
                    shutil.move(f, os.path.join(aside, name))
        fade = max(0.0, b - a - 0.04)
        chain = f"atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.015,afade=t=out:st={fade:.3f}:d=0.04,{base},{finish}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", rawf, "-af", chain, *out, clip], check=True)
        made.append(n)
        print(f"   {n:02d}.mp3  {b - a:5.2f} s  {l.get('who', ''):<2} {voiced(l)}")

    # the times of every character of a line, for `audio.py chunks` (as the line-by-line takes have)
    al = got.get("alignment") or {}
    try:
        for seg_i, (l, (a, _)) in enumerate(zip(lines, cuts)):
            idx = sorted({c for s in got["voice_segments"] if s["dialogue_input_index"] == seg_i for c in range(s["character_start_index"], s["character_end_index"])})
            if al and idx and idx[-1] < len(al["characters"]):
                audio.save_timings(os.path.join(raw, f"{l['n']:02d}.json"), voiced(l), "elevenlabs-scene",
                                   {"characters": [al["characters"][c] for c in idx],
                                    "character_start_times_seconds": [round(al["character_start_times_seconds"][c] - a, 3) for c in idx],
                                    "character_end_times_seconds": [round(al["character_end_times_seconds"][c] - a, 3) for c in idx]})
    except (KeyError, IndexError, TypeError):
        pass   # no character times this time: `chunks` falls back on Whisper

    # 3. the whole scene, leveled the same way, and its subtitles, for the video
    home = os.path.join(REELS, f"{L['course']}-{L['slug']}") if os.path.isdir(REELS) else os.path.join(raw, "video")
    os.makedirs(home, exist_ok=True)
    name = os.path.join(home, f"{L['slug']}{k}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", rawf, "-af", f"{whole},{finish}", *out, name + ".mp3"], check=True)
    with open(name + ".srt", "w", encoding="utf-8", newline="\r\n") as f:
        for i, (l, (a, b)) in enumerate(zip(lines, times), 1):
            f.write(f"{i}\n{stamp(a)} --> {stamp(min(b, end))}\n{shown(l, french)}\n\n")
    print(f"   scene {k} ({title}): {len(made)} clips, {loud:.1f} LUFS, model {used}\n   for the video: {name}.mp3 and .srt")
    return made


def run(L, only):
    todo = [(k, t, ls) for k, t, ls in scenes(L) if not only or k in only]
    if not todo:
        sys.exit("no such scene")
    per = L.get("voice", {})
    for k, t, ls in todo:
        size = sum(len(voiced(l)) for l in ls)
        if size > MAX_CHARS:
            sys.exit(f"scene {k} ({t}) is {size:,} characters: ElevenLabs takes {MAX_CHARS:,} per request. Split the section in two.")
        nobody = sorted({str(l.get("who")) for l in ls if not per.get(l.get("who"))})
        if nobody:
            sys.exit(f'scene {k} ({t}): no voice for {", ".join(nobody)}. Add "voice": {{"E": "<voice id>", ...}} to the lesson file.')
    _, raw = audio.paths(L)
    aside = os.path.join(raw, "_replaced_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S"))
    model = audio.narrator(L)[1]
    made = []
    for k, t, ls in todo:
        print(f"\n=== {L['id']}  scene {k}: {t} ===")
        made += record(L, k, t, ls, model, aside)
    if os.path.isdir(aside):
        print(f"\nThe clips these replace are in {aside}")
    try:
        audio.whisper(L, made)
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"Whisper check skipped ({err}). Run it later: python -E tools\\audio.py check {L['id']}")
    return made


def show(L):
    for k, t, ls in scenes(L):
        print(f"  {k}  {t:<28} {len(ls):>2} lines  {sum(len(voiced(l)) for l in ls):>5,} characters")


def main():
    a = sys.argv[1:]
    asked = not a
    if asked:
        a = [input("Lesson (for example fr/speaking/daccord): ").strip()]
    if not a[0]:
        return
    L = audio.get(a[0])
    show(L)
    if "--list" in a:
        return
    only = [int(x) for x in a[a.index("--only") + 1:] if x.isdigit()] if "--only" in a else []
    if asked:
        only = [int(x) for x in re.findall(r"\d+", input("Scenes to record (Enter = all, or numbers such as 1 3): "))]
        size = sum(len(voiced(l)) for k, _, ls in scenes(L) if not only or k in only for l in ls)
        if input(f"Record about {size:,} characters? The clips of these scenes will be replaced (the old ones are kept aside). (y/n) ").strip().lower() != "y":
            return
    run(L, only)
    print(f"\nListen on the page (preview.bat). Then upload: python -E tools\\audio.py upload {L['id']}")
    if asked and input("Upload now? (y/n) ").strip().lower() == "y":
        audio.upload(audio.get(L["id"]))


if __name__ == "__main__":
    main()
