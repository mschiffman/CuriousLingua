"""The files make_video needs for a grammar chapter's reel, made from the clips already recorded: no new takes,
no ElevenLabs characters. What grammar_video.bat runs.

    python -E tools/chapter_video.py                                   every chapter whose scene clips are recorded
    python -E tools/chapter_video.py eng/grammar/g001_present_simple   one chapter

It writes, in G:\\My Drive\\_VIDEO\\<course>-<slug>\\ (the folder record_scenes.bat uses for a speaking lesson):

    <slug>1.mp3, <slug>2.mp3 ...   each scene: its lines joined, with a short pause between them
    <slug>1.srt, <slug>2.srt ...   one caption per line, timed to the clips
    <slug>.md                      the wording, a "Slide N" part per scene, and the lesson's "Code: G1"
    <slug>\\                        an empty folder for the pictures: 1.png, 2.png ... one per scene,
                                   tall (9:16) for a reel. The chapter's own pictures are wide, for the page.

Then make_video.bat: tick the parts, "Stitch for ...". The name (g001_...) puts curiouslingua.com/g1 on the video.
Run it again after a new take of a line: the scene is joined again from the clips.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grammar_chapter
import lib

REELS = r"G:\My Drive\_VIDEO"   # the same folder as in tools/scene.py
GAP = 0.45                      # seconds of silence between two lines
TAIL = 0.20                     # and after the last line


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def stamp(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def one(L, home_root):
    ch = L["chapter"]
    number = {(w, t): n for n, (w, t) in enumerate(zip(L.get("clip_who", []), L.get("clips", [])), 1)}
    scenes, missing = [], []
    for s in ch["scenes"]:
        lines = []
        for l in s["lines"]:
            text = grammar_chapter.plain(l["text"])
            n = number.get((grammar_chapter.SPEAKER.get(l["who"], "E"), text))
            f = lib.clip_file(L, n) if n else None
            if not f or not os.path.exists(f):
                missing.append(text)
            lines.append((text, f))
        scenes.append((s["title"], lines))
    if missing:
        print(f"  {L['id']}: {len(missing)} line(s) not recorded yet, nothing written (first: {missing[0]})")
        return False

    home = os.path.join(home_root, f"{L['course']}-{L['slug']}")
    os.makedirs(os.path.join(home, L["slug"]), exist_ok=True)   # the pictures folder
    md = [f"# {L['title']}", ""] + ([f"Code: {str(L['code']).strip().upper()}", ""] if L.get("code") else [])
    total = 0.0
    for k, (title, lines) in enumerate(scenes, 1):
        name = os.path.join(home, f"{L['slug']}{k}")
        cmd, parts, t, cues = ["ffmpeg", "-v", "error", "-y"], [], 0.0, []
        for i, (text, f) in enumerate(lines):
            d = seconds(f)
            cues.append((t, t + d, text))
            pause = TAIL if i == len(lines) - 1 else GAP
            t += d + pause
            cmd += ["-i", f]
            parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad=pad_dur={pause}[a{i}]")
        graph = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(lines))) + f"concat=n={len(lines)}:v=0:a=1[out]"
        subprocess.run(cmd + ["-filter_complex", graph, "-map", "[out]", "-b:a", "192k", name + ".mp3"], check=True)
        with open(name + ".srt", "w", encoding="utf-8", newline="\r\n") as f:
            for i, (a, b, text) in enumerate(cues, 1):
                f.write(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n")
        md += [f"## Slide {k}", ""] + [text for text, _ in lines] + [""]
        total += t
    open(os.path.join(home, L["slug"] + ".md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    have = [p for p in os.listdir(os.path.join(home, L["slug"])) if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    print(f"  {L['id']:<44} {len(scenes)} scenes, {total:4.0f} s  ->  {home}" + ("" if len(have) >= len(scenes) else f"\n      pictures still to add: {L['slug']}\\1.png ... {len(scenes)}.png, tall (9:16)"))
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    root = REELS
    if "--to" in args:   # another folder than _VIDEO
        root = args[args.index("--to") + 1]
        del args[args.index("--to"):args.index("--to") + 2]
    picks = [a.replace("\\", "/").removesuffix(".json") for a in args]
    if not os.path.isdir(root):
        sys.exit(f"{root} is not there: the video folder is expected at {REELS} (or give one with --to)")
    n = sum(one(L, root) for L in lib.lessons() if L.get("chapter") and (not picks or L["id"] in picks))
    print(f"{n} chapter(s). Next: put the tall pictures in each folder, then make_video.bat, tick the parts, Stitch.")
