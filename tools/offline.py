"""Builds the offline single-file copy of lesson pages: one .html with the styles, scripts, fonts,
pictures and audio inside. Open it on the tablet from the file manager ("Open with" a browser).

    python tools/offline.py --changed           every lesson whose copy is missing or out of date
    python tools/offline.py all                 every lesson
    python tools/offline.py fr/expressions/greetings eng/reading/2.7_clean
    python tools/offline.py eng/reading         a whole strand (or a whole course: eng)

Output: <course>/single/<strand>__<slug>.html (not in git).
A game page ("type": "game") gets two things: its clips, small, in <course>/<strand>/<slug>_audio/ beside
the page (which plays them before the online ones), and a one-file copy in <course>/single/ like every other
lesson, with its scripts and clips inside.
Audio comes from media/ (the local copy). English is shrunk to 96 kbps mono (cached in
.build_cache/); French, Japanese and every shadowing page are embedded exactly as recorded.
Clips that are not on disk are left out and reported: those buttons stay silent offline.
"""
import base64, hashlib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, build

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C = lib.ROOT, lib.cfg()
MIME = {".m4a": "audio/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".mp3": "audio/mpeg", ".woff2": "font/woff2"}
BURMESE = re.compile("[က-႟]")


def uri(path, data=None):
    data = data if data is not None else open(path, "rb").read()
    return f"data:{MIME[os.path.splitext(path)[1].lower()]};base64," + base64.b64encode(data).decode()


def small(path):
    """96 kbps mono copy of an English clip, cached; the original if that would not be smaller."""
    cache = os.path.join(ROOT, ".build_cache")
    os.makedirs(cache, exist_ok=True)
    st = os.stat(path)
    out = os.path.join(cache, hashlib.md5(f"v2|{path}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest() + ".mp3")
    if not os.path.exists(out):
        # The English clips are the same voice on both channels. A plain "-ac 1" adds the two together, which made
        # the copy about 3 dB louder than the clip and clipped its peaks; averaging them keeps the level as recorded.
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af", "pan=mono|c0=0.5*c0+0.5*c1", "-b:a", "96k", out])
        if r.returncode:
            return open(path, "rb").read()
    data = open(out, "rb").read()
    return data if len(data) < st.st_size else open(path, "rb").read()


def fonts(css, families):
    """Keeps only the @font-face blocks a page needs and embeds their files."""
    def face(m):
        block = m.group(0)
        fam = re.search(r'font-family:\s*"?([^;"}]+)', block).group(1).strip()
        if fam not in families:
            return ""
        return re.sub(r'url\("?\.\./fonts/([^")]+)"?\)', lambda u: f'url({uri(os.path.join(ROOT, "assets", "fonts", u.group(1)))})', block)
    return re.sub(r"@font-face\s*\{[^}]*\}", face, css)


def one(L):
    page = os.path.join(ROOT, *L["url"].split("/"))
    src = open(page, encoding="utf-8").read()
    here = os.path.dirname(page)
    r = "../" * L["url"].count("/")
    fam = {"Playfair Display", "Roboto", "Space Mono"} if L.get("type") == "cards" else {"Fraunces", "Atkinson Hyperlegible"}
    if BURMESE.search(src):
        fam.add("Noto Sans Myanmar")

    def style(m):
        css = open(os.path.normpath(os.path.join(here, m.group(1))), encoding="utf-8").read()
        return "<style>" + fonts(css, fam) + "</style>"
    src = re.sub(r'<link rel="stylesheet" href="([^"]+)">', style, src)
    src = re.sub(r'<link rel="icon"[^>]*>\n?', "", src)

    embed, missing, full = {}, [], L["course"] != "eng" or L.get("type") == "shadow" or bool(L.get("audio_file"))
    aud = L.get("aud_dir") or ""
    base = aud if aud.startswith("http") else C["media_base"] + aud
    if not lib.pending(L):
        for n, _ in lib.clips(L):
            f = lib.clip_file(L, n)
            if f and os.path.exists(f):
                embed[f"{base}{n:02d}.{L.get('aud_ext', 'mp3')}"] = uri(f, None if full else small(f))
            else:
                missing.append(n)
    ver = "?v=" + L["audio_ver"] if L.get("audio_ver") else ""   # the page asks for the recording and glossary clips with this tag
    if L.get("audio_file"):
        f = lib.find("media/" + L["audio_file"])
        if f:
            embed[C["media_base"] + L["audio_file"] + ver] = uri(f)
        else:
            missing.append(L["audio_file"])
    named = [w for g in L.get("groups", []) for w in g.get("words", []) if w.get("audio")] + [p for s in L.get("slides", []) for p in s.get("spots", []) if p.get("audio")]
    for g in L.get("glossary", []) + [{"audio": x} for x in dict.fromkeys(w["audio"] for w in named)]:   # word lists and hotspot pictures play named files too
        name = g.get("audio") or g["word"]
        name = name if "." in name else name + ".mp3"
        f = lib.find("media/" + L.get("glossary_dir", "") + name)
        if f:
            embed[C["media_base"] + L.get("glossary_dir", "") + name + ver] = uri(f)
        else:
            missing.append(name)
    noimg = 0
    for rel in lib.images(L):
        f = lib.find(rel)
        if f:
            embed[r + rel] = uri(f)
        else:
            noimg += 1

    def script(m):
        code = open(os.path.normpath(os.path.join(here, m.group(1))), encoding="utf-8").read()
        return "<script>" + code.replace("</script", "<\\/script") + "</script>"
    src = re.sub(r'<script(?: defer)? src="[^"]*assets/vendor/[^"]+"></script>
?', "", src)   # GSAP stays online only: motion.js then does nothing
    src = re.sub(r'<script(?: defer)? src="([^"]+)"></script>', script, src)
    src = src.replace("<body ", "<body data-offline ", 1)
    src = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n<script>const EMBED=" + json.dumps(embed) + ";</script>", src, count=1)
    out = os.path.join(ROOT, L["course"], "single", f"{L['strand']}__{L['slug']}.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(src)
    note = []
    if lib.pending(L):
        note.append("no audio yet")
    if missing:
        note.append(f"{len(missing)} clip(s) not on disk")
    if noimg:
        note.append(f"{noimg} picture(s) not on disk")
    print(f"  {L['id']:<46} {os.path.getsize(out) / 1048576:5.1f} MB  {'full-quality audio' if full else '96 kbps audio'}" + ("   <<< " + ", ".join(note) if note else ""))


def game_dir(L):
    return os.path.join(ROOT, L["course"], L["strand"], L["slug"] + "_audio")


def single_file(L):
    return os.path.join(ROOT, L["course"], "single", f"{L['strand']}__{L['slug']}.html")


def game(L):
    """A game page is hand-made, so nothing is embedded in it. Its clips are copied, small (96 kbps mono),
    into <slug>_audio beside the page, and the page plays those first: it then has its voice without internet."""
    dest = game_dir(L)
    os.makedirs(dest, exist_ok=True)
    want, missing = set(), []
    for n, _ in lib.clips(L):
        f = lib.clip_file(L, n)
        if f and os.path.exists(f):
            want.add(f"{n:02d}.mp3")
            open(os.path.join(dest, f"{n:02d}.mp3"), "wb").write(small(f))
        else:
            missing.append(n)
    for old in os.listdir(dest):   # clips the game no longer has
        if old.endswith(".mp3") and old not in want:
            os.remove(os.path.join(dest, old))
    size = sum(os.path.getsize(os.path.join(dest, x)) for x in want)
    print(f"  {L['id']:<46} {size / 1048576:5.1f} MB  {len(want)} clips beside the page, 96 kbps" + (f"   <<< {len(missing)} clip(s) not on disk" if missing else ""))

    # The same game as ONE file, like the other offline lessons: the scripts it loads and its clips are written
    # into the page. The link to Google Fonts is dropped (the device's own fonts are used) and so is the Back button.
    page = os.path.join(ROOT, *L["url"].split("/"))
    src = open(page, encoding="utf-8").read()

    def script(m):
        code = open(os.path.join(os.path.dirname(page), m.group(1)), encoding="utf-8").read()
        return "<script>" + code.replace("</script", "<\\/script") + "</script>"
    src = re.sub(r'<script src="([^":]+)"></script>', script, src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>\n?', "", src)
    src = re.sub(r'\s*<a class="back".*?</a>', "", src, flags=re.S)
    inside = {int(x[:-4]): uri(os.path.join(dest, x)) for x in sorted(want)}
    src = src.replace("<body>", "<body data-offline>\n<script>window.GAME_CLIPS=" + json.dumps(inside) + ";</script>", 1)
    out = single_file(L)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(src)
    print(f"  {L['id']:<46} {os.path.getsize(out) / 1048576:5.1f} MB  one file: {os.path.relpath(out, ROOT)}")


def stale(L):
    if L.get("type") == "game":
        pairs = [(lib.clip_file(L, n), os.path.join(game_dir(L), f"{n:02d}.mp3")) for n, _ in lib.clips(L)]
        one_file, page = single_file(L), os.path.join(ROOT, *L["url"].split("/"))
        if not os.path.exists(one_file) or os.path.getmtime(page) > os.path.getmtime(one_file):
            return True
        return any(f and os.path.exists(f) and (not os.path.exists(o) or os.path.getmtime(f) > os.path.getmtime(o)) for f, o in pairs)
    out = os.path.join(ROOT, L["course"], "single", f"{L['strand']}__{L['slug']}.html")
    if not os.path.exists(out):
        return True
    t = os.path.getmtime(out)
    files = [L["file"]] + [f for f in (lib.clip_file(L, n) for n, _ in lib.clips(L)) if f] + [f for f in (lib.find(x) for x in lib.images(L)) if f]
    return any(os.path.exists(f) and os.path.getmtime(f) > t for f in files)


def main():
    args = [a.replace("\\", "/").strip("/") for a in sys.argv[1:]]
    if not args:
        sys.exit(__doc__)
    build.main()   # the copies are made from freshly built pages
    todo = [L for L in lib.lessons() if L["course"] in C["courses"] and L["strand"] in C["courses"][L["course"]]["strands"]
            and L.get("type") not in ("page", "link") and (L.get("type") != "game" or L.get("clips"))]   # hand-made pages: only a game with recordings has something to copy
    if args == ["--changed"]:
        todo = [L for L in todo if stale(L)]
    elif args != ["all"]:
        todo = [L for L in todo if any(L["id"] == a or L["id"].startswith(a + "/") for a in args)]
    if not todo:
        print("nothing to build")
        return
    for L in todo:
        game(L) if L.get("type") == "game" else one(L)
    build.main()   # so the pages and offline/index.html link to the new copies
    print(f"{len(todo)} offline file(s) written")


if __name__ == "__main__":
    main()
