"""Status report: what exists, what is missing. Prints a summary and writes _reports/status.md.

    python tools/check.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C = lib.ROOT, lib.cfg()
have_media, have_img = os.path.isdir(os.path.join(ROOT, "media")), os.path.isdir(os.path.join(ROOT, "img"))
out = ["# Site status", ""]
all_lessons = lib.lessons()
for k, c in C["courses"].items():
    items = [L for L in all_lessons if L["course"] == k]
    out += [f"## {c['name']}: {len(items)} lessons", "", "| Level | " + " | ".join(C["strands"][s][0] for s in c["strands"]) + " |", "|---|" + "---|" * len(c["strands"])]
    for code in c["levels"]:
        out.append(f"| {code.upper()} | " + " | ".join(str(sum(1 for L in items if L["strand"] == s and L.get("level") == code) or "·") for s in c["strands"]) + " |")
    out.append("")
    pend, noclip, noimg, prov, review, notr, noquiz = [], [], [], [], [], [], []
    for L in items:
        cl = lib.clips(L)
        if lib.pending(L):
            pend.append(f"- `{L['id']}`: {len(cl)} clips, {sum(len(lib.spoken(t)) for _, t in cl):,} characters")
        elif have_media:
            miss = [n for n, _ in cl if not os.path.exists(lib.clip_file(L, n) or "")]
            if miss:
                noclip.append(f"- `{L['id']}`: {len(miss)} of {len(cl)} clips not in media/ ({', '.join(map(str, miss[:8]))}{' ...' if len(miss) > 8 else ''})")
        if have_img:
            mi = [x for x in lib.images(L) if not lib.find(x)]
            if mi:
                noimg.append(f"- `{L['id']}`: {len(mi)} of {len(lib.images(L))} pictures missing, expected in `{L.get('img_dir') or ', '.join(mi)}`")   # a text lesson has one `img`, no `img_dir`
        if L.get("level_provisional"):
            prov.append(L["id"])
        if L.get("review"):
            review.append(f"- `{L['id']}`: {L['review']}")
        if L.get("type") == "dialogue":
            want = L.get("support", [])
            gaps = sum(1 for sec in L["sections"] for l in sec["lines"] for w in want if not (l.get("tr") or {}).get(w))
            if gaps:
                notr.append(f"- `{L['id']}`: {gaps} translation line(s) missing")
        if not (L.get("quiz") or L.get("questions") or L.get("type") in ("game", "hotspots", "page", "link")):   # a game and a hotspot page are their own quiz; a hand-made page has none
            noquiz.append(L["id"])
    for title, rows in (("Audio to record (pending)", pend), ("Clips wired but not on this computer", noclip), ("Pictures missing", noimg),
                        ("To review before publishing", review), ("Translations missing", notr)):
        if rows:
            out += [f"### {title}", ""] + rows + [""]
    if prov:
        out += [f"### Level is my guess, not checked: {len(prov)} lessons", "", "Set `level` in the lesson file and delete `level_provisional`.", "", ", ".join(f"`{x}`" for x in prov), ""]
    if noquiz:
        out += [f"### No quiz yet: {len(noquiz)} lessons", "", ", ".join(f"`{x}`" for x in noquiz), ""]
    print(f"{c['name']:<9} {len(items):>4} lessons | audio pending {len(pend):>3} | clips not on disk {len(noclip):>3} | pictures missing {len(noimg):>3} | to review {len(review):>3} | level unchecked {len(prov):>3} | no quiz {len(noquiz):>3}")
if not have_media:
    out += ["", "*media/ is not here yet, so local clips were not checked.*"]
    print("media/ is not here yet: local clips not checked")
if not have_img:
    out += ["", "*img/ is not here yet, so pictures were not checked.*"]
    print("img/ is not here yet: pictures not checked")
os.makedirs(os.path.join(ROOT, "_reports"), exist_ok=True)
open(os.path.join(ROOT, "_reports", "status.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("full report: _reports\\status.md")
