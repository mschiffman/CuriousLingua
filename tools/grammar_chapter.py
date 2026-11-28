"""Writes the page of each grammar chapter: four scenes, Notice, the rule, common mistakes, practice, Speak, quiz.

    python -E tools/grammar_chapter.py                              every chapter
    python -E tools/grammar_chapter.py eng/grammar/g001_present_simple

A chapter is a hand-made page in the build's sense ("type": "game"): the build lists it and never writes it.
This tool writes it, from the lesson file's "chapter" block and tools/grammar_chapter.html:

    content/<course>/grammar/<slug>.json   ->   <course>/grammar/<slug>.html

It also keeps the lesson's "clips" and "clip_who" lists in step with the chapter: every scene line, every word of
"sounds" and of the "hear" exercises, every "speak" line. A clip is known by who says it and what is said, and
keeps its number for good: new clips are added at the end, and a clip no longer used keeps its place, so
recordings already made stay right. The audio tool records them like any game's clips (2_audio.bat), each in its
speaker's voice ("voice": {"E": ..., "L": ...}); 3_offline.bat makes the one-file copy.

Run it again after editing a chapter, and after an audio upload (the page carries the lesson's "aud_ext").
Pictures are optional: img/grammar/<course>/<slug>/1.jpg ... one per scene, written into the page so the offline copy has them.
Standard library only.
"""
import base64, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C = lib.ROOT, lib.cfg()
SPEAKER = {"Emma": "E", "Lucas": "L"}   # the speaker keys of the lesson's "voice" line
FONTS = [("Noto Sans Myanmar", "noto-sans-myanmar-myanmar", "U+1000-109F,U+A9E0-A9FF,U+AA60-AA7F"),
         ("Noto Sans Devanagari", "noto-sans-devanagari-devanagari", "U+0900-097F,U+A8E0-A8FF,U+1CD0-1CFF,U+200C-200D,U+20B9,U+25CC")]
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2"}


def uri(path):
    return f"data:{MIME[os.path.splitext(path)[1].lower()]};base64," + base64.b64encode(open(path, "rb").read()).decode()


def slug(s):
    return re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", s.lower()))


def plain(s):
    return s.replace("[[", "").replace("]]", "")


def fonts(langs):
    out = []
    for family, name, rng in FONTS:
        if (family.endswith("Myanmar") and "my" not in langs) or (family.endswith("Devanagari") and "hi" not in langs):
            continue
        for w in (400, 700):
            f = os.path.join(ROOT, "assets", "fonts", f"{name}-{w}-normal.woff2")
            if os.path.exists(f):
                out.append(f"@font-face{{font-family:'{family}';font-weight:{w};font-display:swap;src:url({uri(f)}) format('woff2');unicode-range:{rng}}}")
            else:
                print(f"   font missing: assets/fonts/{os.path.basename(f)} (the device's own font is used)")
    return "\n".join(out)


def wanted(ch):
    """[(key the page asks for, speaker key, text)] in page order."""
    rows = []
    for si, s in enumerate(ch["scenes"], 1):
        for li, l in enumerate(s["lines"], 1):
            rows.append((f"s{si}_{li:02d}", SPEAKER.get(l["who"], "E"), plain(l["text"])))
    for w in ch.get("sounds", {}).get("items", []):
        rows.append(("w_" + slug(w["word"]), "E", w["word"]))
    for p in ch.get("practice", []):
        if p["type"] == "hear":
            rows += [("w_" + slug(it["say"]), "E", it["say"]) for it in p["items"]]
    rows += [(f"p_{i:02d}", "E", plain(s)) for i, s in enumerate(ch.get("speak", []), 1)]
    return rows


def one(path):
    doc = json.load(open(path, encoding="utf-8"))
    ch = doc.get("chapter")
    if not ch:
        return False
    rel = os.path.relpath(path, os.path.join(ROOT, "content")).replace("\\", "/")[:-5]
    course, strand, name = rel.split("/")

    # clips: numbered once, never renumbered
    clips, who = list(doc.get("clips", [])), list(doc.get("clip_who", []))
    who += ["E"] * (len(clips) - len(who))
    number = {(w, t): n for n, (w, t) in enumerate(zip(who, clips), 1)}
    keys, added = {}, 0
    for key, w, text in wanted(ch):
        if (w, text) not in number:
            clips.append(text); who.append(w); number[(w, text)] = len(clips); added += 1
        keys[key] = number[(w, text)]
    if clips != doc.get("clips") or who != doc.get("clip_who"):
        doc["clips"], doc["clip_who"] = clips, who
        json.dump(doc, open(path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
        if added and "pending" not in doc.get("aud_ext", "pending"):
            print(f"   {rel}: {added} new clip(s) to record (2_audio.bat)")

    img = {}
    for si in range(1, len(ch["scenes"]) + 1):
        for ext in (".jpg", ".webp", ".png"):
            f = os.path.join(ROOT, "img", strand, course, name, f"{si}{ext}")
            if os.path.exists(f):
                img[f"s{si}"] = uri(f)
                break

    code = str(doc.get("code") or "").strip()
    L = dict(ch, code=code, title=doc["title"], level=C["levels"].get(doc.get("level"), doc.get("level") or ""))
    base = C["media_base"].rstrip("/") + "/" + doc["aud_dir"].strip("/") + "/"
    page = (open(os.path.join(ROOT, "tools", "grammar_chapter.html"), encoding="utf-8").read()
            .replace("__TITLE__", f"{doc['title']} | {C['site_name']}")
            .replace("__FONTS__", fonts(ch["langs"]))
            .replace("/*__DATA__*/null", json.dumps(L, ensure_ascii=False).replace("</", "<\\/"))
            .replace("/*__KEYS__*/{}", json.dumps(keys))
            .replace('/*__CLIPS__*/{local:"",base:"",ext:"mp3?v=pending"}', json.dumps({"local": name + "_audio/", "base": base, "ext": doc.get("aud_ext", "mp3?v=pending"),
                                                                                              "single": f"../single/{strand}__{name}.html",   # the Download button: the one-file copy made by 3_offline.bat
                                                                                              "file": re.sub(r"[^A-Za-z0-9]+", "_", f"{code} {doc['title']}").strip("_") + ".html"}))
            .replace("/*__IMG__*/{}", json.dumps(img)))
    out = os.path.join(ROOT, course, strand, name + ".html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    if page != old:
        open(out, "w", encoding="utf-8", newline="\n").write(page)
    print(f"  {rel:<44} {len(page.encode('utf-8')) / 1024:5.0f} KB  {len(clips)} clips  {len(img)}/{len(ch['scenes'])} pictures" + ("" if page != old else "   (no change)"))
    return True


if __name__ == "__main__":
    picks = [a.replace("\\", "/").removesuffix(".json") for a in sys.argv[1:]]
    n = 0
    for dirpath, _, files in os.walk(os.path.join(ROOT, "content")):
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, os.path.join(ROOT, "content")).replace("\\", "/")[:-5]
            if f.endswith(".json") and (not picks or rel in picks):
                n += one(p)
    print(f"{n} chapter(s). Next: preview.bat to look, 2_audio.bat to record, 3_offline.bat for the one-file copies.")
