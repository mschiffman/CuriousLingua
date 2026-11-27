"""Makes the printable transcript of a dialogue: one PDF, <course>/<strand>/<slug>.pdf, beside the lesson page.

    python tools/transcript.py --changed          every speaking lesson whose PDF is missing or out of date
    python tools/transcript.py all                every speaking lesson
    python tools/transcript.py fr/speaking/f013_disbelief
    python tools/transcript.py fr/speaking        a whole strand (or a whole course: fr)

The PDF is printed by Microsoft Edge (or Chrome), which is already on the computer: a browser is the only thing that
sets Burmese, Japanese and Korean correctly. Nothing is opened on screen. The page it prints is built here, from the
lesson file: title, number, level and heading, the short address with a QR code, then every scene with its lines and
their translation, and the lesson's notes. The notes of single lines and the introduction are left out, so that a
dialogue fits on one sheet, printed on both sides, whenever it can.

The QR code needs the small package segno (pip install segno). Without it the PDF is made with the address alone.
A lesson page shows its "Transcript (PDF)" button when the PDF is there: this tool rebuilds the pages at the end.
Set TRANSCRIPT_BROWSER to the path of another Chromium browser to use that one.
"""
import html, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, build

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C = lib.ROOT, lib.cfg()
e = html.escape
STRANDS = ("speaking",)      # the strands that get transcripts
DOMAIN = "curiouslingua.com"
TONE = ["#B45309", "#0E7490", "#9D174D", "#047857", "#6D28D9"]   # one colour per speaker, as on the lesson page
LANGS = {"en": "English", "my": "Burmese", "fr": "French", "es": "Spanish"}


def browser():
    """The Edge or Chrome that prints the PDFs."""
    places = [os.environ.get("TRANSCRIPT_BROWSER", "")]
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LocalAppData")):
        if base:
            places += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"), os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    places += [shutil.which(x) or "" for x in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser")]
    return next((p for p in places if p and os.path.exists(p)), None)


def pdf_file(L):
    return os.path.join(ROOT, L["course"], L["strand"], L["slug"] + ".pdf")


def stale(L):
    out = pdf_file(L)
    return not os.path.exists(out) or os.path.getmtime(out) < max(os.path.getmtime(L["file"]), os.path.getmtime(os.path.abspath(__file__)))


def qr_svg(url):
    try:
        import segno
    except ImportError:
        return ""
    return segno.make(url, error="m").svg_inline(scale=3, border=0, dark="#1E2330", omitsize=True)


def css_text(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def page(L):
    """The transcript as one HTML page, laid out for A4."""
    c = C["courses"][L["course"]]
    code = str(L.get("code") or "").strip().upper()
    url = f"{DOMAIN}/{code.lower()}" if build.code_of(L) else f"{DOMAIN}/{L['url']}"
    lines = [l for sec in L["sections"] for l in sec["lines"]]
    tr = next((k for k in list(L.get("support", ())) + ["en", "my"] if any((l.get("tr") or {}).get(k) for l in lines)), None)   # the translation shown
    names = L.get("speakers", {})
    who = {k: i for i, k in enumerate(names or sorted({l.get("who", "") for l in lines}))}
    body = ""
    for sec in L["sections"]:
        rows = ""
        for l in sec["lines"]:
            k = l.get("who", "")
            nat = l.get("kana") or l.get("hangul")
            native = f'<span class="native">{e(nat)}</span>' if nat else ""
            rows += (f'<div class="row" style="--tone:{TONE[who.get(k, 0) % len(TONE)]}"><div class="who">{e(names.get(k, k))}</div>'
                     f'<div class="say" lang="{c["lang"]}">{e(l.get("text") or l.get("romaji") or l.get("rom") or "")}{native}</div>'
                     + (f'<div class="tr" lang="{tr}">{e((l.get("tr") or {}).get(tr, ""))}</div>' if tr else "") + "</div>")
        body += (f'<h2>{e(sec["title"])}</h2>' if sec.get("title") else '<div class="gap"></div>') + rows
    notes = "".join(f"<li>{e(n)}</li>" for n in L.get("notes", ()))
    fonts = Path(ROOT, "assets", "fonts").as_uri() + "/"
    qr = qr_svg("https://" + url)
    chips = (f'<span class="code">{e(code)}</span>' if code else "") + f'<span>{e(build.lv(L.get("level")))}</span>' + (f'<span>{e(L["topic"])}</span>' if L.get("topic") else "")
    foot = " · ".join(x for x in (code, L.get("title", ""), url) if x)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(code)} {e(L.get("title", ""))}</title><style>
@font-face{{font-family:Fraunces;font-weight:600;src:url({fonts}fraunces-latin-600-normal.woff2)}}
@font-face{{font-family:Fraunces;font-weight:600;src:url({fonts}fraunces-latin-ext-600-normal.woff2);unicode-range:u+0100-02ba,u+1e00-1eff}}
@font-face{{font-family:Fraunces;font-weight:400;font-style:italic;src:url({fonts}fraunces-latin-400-italic.woff2)}}
@font-face{{font-family:Atkinson;font-weight:400;src:url({fonts}atkinson-hyperlegible-latin-400-normal.woff2)}}
@font-face{{font-family:Atkinson;font-weight:400;src:url({fonts}atkinson-hyperlegible-latin-ext-400-normal.woff2);unicode-range:u+0100-02ba,u+1e00-1eff}}
@font-face{{font-family:Atkinson;font-weight:700;src:url({fonts}atkinson-hyperlegible-latin-700-normal.woff2)}}
@font-face{{font-family:Atkinson;font-weight:700;src:url({fonts}atkinson-hyperlegible-latin-ext-700-normal.woff2);unicode-range:u+0100-02ba,u+1e00-1eff}}
@font-face{{font-family:"Noto Sans Myanmar";font-weight:400;src:url({fonts}noto-sans-myanmar-myanmar-400-normal.woff2)}}
@font-face{{font-family:"Noto Sans Myanmar";font-weight:700;src:url({fonts}noto-sans-myanmar-myanmar-700-normal.woff2)}}
@page{{size:A4;margin:13mm 16mm 15mm;
  @bottom-left{{content:{css_text(foot)};font:7pt Atkinson,Arial,sans-serif;color:#6B7280}}
  @bottom-right{{content:counter(page) " / " counter(pages);font:7pt Atkinson,Arial,sans-serif;color:#6B7280}}}}
*{{box-sizing:border-box}} body{{margin:0;font:10.5pt/1.45 Atkinson,"Noto Sans Myanmar","Yu Gothic","Malgun Gothic",sans-serif;color:#1E2330;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
header{{display:flex;justify-content:space-between;gap:10mm;align-items:flex-start;padding-bottom:5mm;border-bottom:1.2pt solid #1E2330}}
.kicker{{font-size:7.5pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#2B4ACB}}
h1{{font:600 30pt/1.05 Fraunces,"Noto Sans Myanmar","Yu Gothic","Malgun Gothic",serif;margin:2.5mm 0 1.5mm;letter-spacing:-.01em}}
.sub{{font:italic 400 13pt/1.3 Fraunces,"Noto Sans Myanmar","Yu Gothic","Malgun Gothic",serif;color:#4B5563;margin:0}}
.chips{{margin-top:3.5mm;display:flex;gap:2mm}} .chips span{{font-size:7.5pt;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border:.8pt solid #C9C0B0;border-radius:99px;padding:.6mm 2.6mm}}
.chips .code{{background:#1E2330;border-color:#1E2330;color:#fff}}
.qr{{flex:none;width:46mm;text-align:right}} .qr svg{{width:24mm;height:24mm}} .qr b{{display:block;margin-top:1.5mm;font-size:9.5pt}} .qr span{{display:block;font-size:7.5pt;color:#4B5563;line-height:1.3}}
h2{{font:600 14pt/1.2 Fraunces,"Noto Sans Myanmar","Yu Gothic","Malgun Gothic",serif;margin:5mm 0 1.8mm;break-after:avoid}} .gap{{height:5mm}}
.row{{display:grid;grid-template-columns:15mm 1fr{" 1fr" if tr else ""};column-gap:5mm;padding:.8mm 0 .8mm 3mm;border-left:2.2pt solid var(--tone);margin-bottom:.8mm;break-inside:avoid}}
.who{{font-size:7.5pt;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--tone);padding-top:.7mm}}
.say{{font-size:11pt}} .native{{display:block;font-size:10pt;color:#374151;margin-top:.3mm}} .tr{{color:#4B5563;font-size:9.5pt;padding-top:.4mm}}
.notes{{margin-top:5mm;padding:3mm 5mm;border:.8pt solid #C9C0B0;border-radius:3mm;break-inside:avoid}} .notes h2{{margin:0 0 2mm;font-size:13pt}} .notes ul{{margin:0;padding-left:4.5mm;font-size:9pt;color:#374151}} .notes li{{margin-bottom:.8mm}}
</style></head><body>
<header><div><div class="kicker">{e(c["name"])} &middot; {e(C["strands"][L["strand"]][0])} &middot; Transcript{f" with {LANGS.get(tr, tr)}" if tr else ""}</div>
<h1 lang="{c["lang"]}">{e(L.get("title", L["slug"]))}</h1>{f'<p class="sub">{e(L["subtitle"])}</p>' if L.get("subtitle") else ""}
<div class="chips">{chips}</div></div>
<div class="qr">{qr}<b>{e(url) if build.code_of(L) else e(DOMAIN)}</b><span>Listen to every line and take the quiz. Free, no account.</span></div></header>
{body}
{f'<div class="notes"><h2>Notes</h2><ul>{notes}</ul></div>' if notes else ""}
</body></html>'''


def one(L, exe, work):
    src = os.path.join(work, L["slug"] + ".html")
    out = pdf_file(L)
    tmp = os.path.join(work, L["slug"] + ".pdf")   # printed here first: a failed print never replaces a good PDF
    with open(src, "w", encoding="utf-8") as f:
        f.write(page(L))
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--no-pdf-header-footer", "--print-to-pdf-no-header",
           "--virtual-time-budget=5000", f"--user-data-dir={os.path.join(work, 'profile')}", f"--print-to-pdf={tmp}", Path(src).as_uri()]
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except subprocess.TimeoutExpired:
        pass
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 2000:
        print(f"  {L['id']}: NOT MADE (the browser wrote no PDF)")
        return False
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copyfile(tmp, out)
    print(f"  {L['id']}: {os.path.getsize(out) // 1024} KB")
    return True


def main():
    args = [a.replace("\\", "/").strip("/") for a in sys.argv[1:]]
    if not args:
        sys.exit(__doc__)
    exe = browser()
    if not exe:
        sys.exit("No Microsoft Edge or Chrome found. Set TRANSCRIPT_BROWSER to the path of msedge.exe or chrome.exe.")
    todo = [L for L in lib.lessons() if L["course"] in C["courses"] and L["strand"] in STRANDS and L.get("type") == "dialogue" and not L.get("supplement_of")]
    if args == ["--changed"]:
        todo = [L for L in todo if stale(L)]
    elif args != ["all"]:
        todo = [L for L in todo if any(L["id"] == a or L["id"].startswith(a + "/") for a in args)]
    if not todo:
        print("nothing to make: every transcript is up to date")
        return
    if not qr_svg("https://" + DOMAIN):
        print("  (no QR codes: the package segno is not installed. To add them:  pip install segno  and run this again with: all)")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work:   # the browser may still hold its profile folder for a moment
        done = sum(one(L, exe, work) for L in todo)
    build.main()   # so each lesson page shows the button of its new transcript
    print(f"{done} of {len(todo)} transcript(s) written")


if __name__ == "__main__":
    main()
