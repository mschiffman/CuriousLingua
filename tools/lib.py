"""Shared helpers for the site tools: reading site.json and the lesson files, and working out
which audio clips and images each lesson needs. Standard library only."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVEL_ORDER = ["pre-a1", "a1", "a2", "b1", "b2", "c1"]
HAND = ("game", "page")   # hand-made pages: the build lists them but never writes them
SILENT = ("grammar", "timeline", "family")   # generated pages with no recordings: never "audio soon"


def cfg():
    return json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def normalize(L):
    """Numbers the lines / chunks of a lesson 1, 2, 3 ... when the file leaves the numbers out."""
    if L.get("type") == "dialogue":
        if "sections" not in L:
            L["sections"] = [{"lines": L.pop("lines", [])}]
        n = 0
        for sec in L["sections"]:
            for line in sec["lines"]:
                n += 1
                line.setdefault("n", n)
    if L.get("type") == "shadow":
        for i, c in enumerate(L.get("chunks", []), 1):
            c.setdefault("n", i)
    if L.get("type") == "words":
        n = 0
        for g in L.get("groups", []):
            for w in g.get("words", []):
                n += 1
                w.setdefault("n", n)
    if L.get("type") == "text":
        n = 0
        for para in L.get("paragraphs", []):
            for s in para:
                n += 1
                s.setdefault("n", n)
    return L


def lessons():
    """Every lesson in content/, sorted the way the site lists them."""
    out = []
    base = os.path.join(ROOT, "content")
    for dirpath, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), base).replace("\\", "/")
            parts = rel.split("/")
            if len(parts) != 3:
                continue
            L = normalize(json.load(open(os.path.join(dirpath, f), encoding="utf-8")))
            if L.get("retired"):   # a lesson that was renamed: clear away the old file and its pages
                stem = parts[2][:-5]
                for old in (os.path.join(dirpath, f), os.path.join(ROOT, parts[0], parts[1], stem + ".html"),
                            os.path.join(ROOT, parts[0], "single", f"{parts[1]}__{stem}.html")):
                    if os.path.exists(old):
                        os.remove(old)
                        print("  removed", os.path.relpath(old, ROOT))
                continue
            L["course"], L["strand"], L["slug"] = parts[0], parts[1], parts[2][:-5]
            L["id"] = f"{L['course']}/{L['strand']}/{L['slug']}"
            L["url"] = L["id"] + ".html"
            L["file"] = os.path.join(dirpath, f)
            out.append(L)
    out.sort(key=lambda L: (L["course"], L["strand"], L.get("order", 500), natural(L["slug"])))
    return out


def clips(L):
    """[(clip number, text the voice says)] for a lesson, in the order of the NN.mp3 files."""
    t = L.get("type")
    if L.get("audio_file"):   # nothing to make: the lesson plays ranges of one existing recording
        return []
    if t == "cards":
        cards = [c for cat in L.get("categories", []) for c in cat["cards"]]
        return [(i, c[0]) for i, c in enumerate(cards, 1)]
    if t == "reader":
        return sorted({(c[1], c[0]) for p in L.get("pages", []) for s in p["sentences"] for c in s})
    if t == "dialogue":
        return [(l["n"], l.get("say") or l.get("kana") or l.get("hangul") or l.get("text") or l.get("romaji", "")) for sec in L["sections"] for l in sec["lines"]]
    if t == "shadow":   # a chunk with "clip" is a part of that clip (another lesson's take): nothing to record for it
        out = {}
        for c in L.get("chunks", []):
            if c.get("clip"):
                out.setdefault(c["clip"], "")
            else:
                out[c["n"]] = c["text"]
        return sorted(out.items())
    if t == "text":
        return [(s["n"], s["text"]) for para in L.get("paragraphs", []) for s in para]
    if t in ("words", "hotspots"):   # their clips are named files in glossary_dir, made by `audio.py words`: no numbered clips
        return []
    if t in HAND:   # sentences a hand-made page plays: "clips": ["...", "..."] become 01.mp3, 02.mp3 ...
        return [(i, text) for i, text in enumerate(L.get("clips", []), 1)]
    if t == "practice":   # "listen" exercises replay clips of the lesson they belong to
        return sorted({(it["n"], "") for b in L.get("blocks", []) if b.get("kind") == "listen" for it in b["items"]})
    return []


def spoken(text):
    """The words the voice reads: no markup, no bracketed variants, blanks said as a trailing '...'."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s*\([^)]*\)", "", text)
    return " ".join(text.replace("___.", "...").replace("___", "...").split())


def pending(L):
    if L.get("type") in SILENT:
        return False
    if L.get("type") in HAND and not L.get("clips"):   # a hand-made page with nothing to record
        return False
    if L.get("type") in ("words", "hotspots"):   # named files in glossary_dir: pending only while no word has one yet
        items = [w for g in L.get("groups", []) for w in g.get("words", [])] + [p for s in L.get("slides", []) for p in s.get("spots", [])]
        return not any(w.get("audio") for w in items)
    if L.get("audio_file"):   # one recording for the whole text, with a time range per sentence
        return False
    return not L.get("aud_dir") or "pending" in L.get("aud_ext", "")


def images(L):
    """Site-relative paths of the pictures a lesson uses."""
    if L.get("type") == "reader" and L.get("img_dir"):
        ext = L.get("img_ext", "jpg")
        return [f"{L['img_dir']}{p['img']}.{ext}" for p in L.get("pages", []) if p.get("img")]
    if L.get("type") in ("text", "words") and L.get("img"):
        return [L["img"]]
    if L.get("type") == "hotspots":
        return [s["img"] for s in L.get("slides", []) if s.get("img")]
    return []


def find(rel):
    """Finds a file under the site root whatever the letter case of the folders (the audio folders
    online are 'lessons/Expressions/...', on disk 'lessons/expressions/...'). Returns a path or None."""
    cur = ROOT
    for part in rel.replace("\\", "/").strip("/").split("/"):
        nxt = os.path.join(cur, part)
        if not os.path.exists(nxt):
            try:
                m = [x for x in os.listdir(cur) if x.lower() == part.lower()]
            except OSError:
                return None
            if not m:
                return None
            nxt = os.path.join(cur, m[0])
        cur = nxt
    return cur


def media_dir(L):
    """media/<aud_dir> on disk (the local copy of what is on R2). May not exist yet."""
    d = L.get("aud_dir", "")
    if not d or re.match(r"https?:", d):
        return None
    return find("media/" + d) or os.path.join(ROOT, "media", *d.strip("/").split("/"))


def clip_file(L, n):
    d = media_dir(L)
    return os.path.join(d, f"{n:02d}.mp3") if d else None
