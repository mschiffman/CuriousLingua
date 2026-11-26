"""Pitch curves of a lesson's recorded clips, beside the same lines read by AivisSpeech. What pitch.bat runs.

    python -E tools/pitch.py                              asks for the lesson
    python -E tools/pitch.py jap/speaking/hello_goodbye   every line of the lesson
    python -E tools/pitch.py <lesson> --only 4 12         only clips 4 and 12
    python -E tools/pitch.py <lesson> --ref "コハク/ノーマル"  another AivisSpeech voice as the reference
    python -E tools/pitch.py <lesson> --no-ref            only the recorded clips, no AivisSpeech

For each line it draws the pitch of the lesson's clip (media/<aud_dir>/NN.mp3, the ElevenLabs take) and, when
AivisSpeech is open, the pitch of the same text read by AivisSpeech, which takes its accents from a pronunciation
dictionary. Both curves are in semitones around the speaker's own middle pitch, so a man and a woman can be compared,
and both are stretched to the same width, so only the shape counts, not the speed.

The report also prints the accent AivisSpeech expects, mora by mora:  ア＼メ  falls after ア,  アメ￣  stays up.
"match" says how alike the two shapes are (1.00 = the same). A low figure means: listen to this line. It does not
say which of the two is right, and it is a rough figure: a question, a surprise or a stage direction changes the
melody of a sentence without any accent being wrong.

The report is _reports/pitch/<course>-<slug>/index.html, with both recordings to play for every line.
Nothing is recorded with ElevenLabs and no lesson file is changed.

Needs: pip install praat-parselmouth matplotlib      and ffmpeg on the PATH (as the audio tools do).
The reference needs AivisSpeech to be open (its engine answers on http://127.0.0.1:10101)."""
import html
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
try:
    import numpy as np
    import parselmouth
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as err:
    sys.exit(f"{err}\nInstall what this tool needs:  pip install praat-parselmouth matplotlib")

ENGINE = os.environ.get("AIVISSPEECH_URL", "http://127.0.0.1:10101")
DEFAULT_REF = "阿井田 茂/Calm"    # the AivisSpeech voice used as the reference when it is installed (else the first one)
FLOOR, CEILING = 60, 500          # Hz: the range in which a voice's pitch is looked for
POINTS = 80                       # both curves are compared at this many points
CLOSE, FAR = 0.80, 0.50           # match >= CLOSE: alike; < FAR: listen


def get(lid):
    lid = lid.replace("\\", "/").strip("/")
    for L in lib.lessons():
        if L["id"] == lid:
            return L
    sys.exit(f"no lesson {lid} (expected course/strand/slug)")


def lines(L):
    """[(clip number, who, what the page shows, what the voice reads)]"""
    if L.get("type") != "dialogue":
        return [(n, "", text, lib.spoken(text)) for n, text in lib.clips(L)]
    out = []
    for sec in L["sections"]:
        for l in sec["lines"]:
            shown = l.get("romaji") or l.get("rom") or l.get("text") or l.get("kana") or ""
            said = l.get("say") or l.get("kana") or l.get("hangul") or l.get("text") or l.get("romaji", "")
            out.append((l["n"], L.get("speakers", {}).get(l.get("who"), l.get("who", "")), lib.spoken(shown), lib.spoken(said)))
    return out


# ---- pitch -----------------------------------------------------------------------------------------------------

def contour(path):
    """(times, semitones around the clip's middle pitch) of the voiced frames of a sound file; ([], []) if none."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "22050", wav], check=True)
        pitch = parselmouth.Sound(wav).to_pitch_ac(time_step=0.01, pitch_floor=FLOOR, pitch_ceiling=CEILING)
    hz, t = pitch.selected_array["frequency"], pitch.xs()
    keep = hz > 0
    if keep.sum() < 3:
        return np.array([]), np.array([])
    return t[keep], 12 * np.log2(hz[keep] / np.median(hz[keep]))


def shape(t, st):
    """the curve at POINTS evenly spaced moments between its first and last voiced frame (gaps bridged)"""
    return np.interp(np.linspace(t[0], t[-1], POINTS), t, st)


def match(a, b):
    """How alike two curves are, -1..1: their correlation once each moment of one is paired with the moment of the
    other it resembles most (dynamic time warping, within a band), so a slower syllable does not count as a difference."""
    n, band = len(a), max(6, len(a) // 5)
    cost = np.full((n + 1, n + 1), np.inf)
    cost[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(max(1, i - band), min(n, i + band) + 1):
            cost[i, j] = (a[i - 1] - b[j - 1]) ** 2 + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
    i, j, pa, pb = n, n, [], []
    while i > 0 and j > 0:
        pa.append(a[i - 1])
        pb.append(b[j - 1])
        step = int(np.argmin([cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1]]))
        i, j = (i - 1, j - 1) if step == 0 else (i - 1, j) if step == 1 else (i, j - 1)
    pa, pb = np.array(pa), np.array(pb)
    if pa.std() < 1e-6 or pb.std() < 1e-6:
        return 0.0
    return float(np.corrcoef(pa, pb)[0, 1])


# ---- AivisSpeech -----------------------------------------------------------------------------------------------

def call(path, params=None, body=None, method="GET"):
    url = ENGINE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def reference(wanted):
    """(style id, "name (style)") of the AivisSpeech voice to use, or (None, why not)"""
    try:
        speakers = json.loads(call("/speakers"))
    except (urllib.error.URLError, OSError, ValueError) as err:
        return None, f"AivisSpeech did not answer on {ENGINE} ({err}). Open AivisSpeech and run this again for the reference."
    styles = [(st["id"], sp["name"], st["name"]) for sp in speakers for st in sp.get("styles", [])]
    if not styles:
        return None, "AivisSpeech has no voice installed"
    name, _, style = wanted.partition("/")
    for sid, n, s in styles:
        if name.strip() in n and (not style or style.strip().lower() == s.lower()):
            return sid, f"{n} ({s})"
    if wanted != DEFAULT_REF:
        sys.exit(f'AivisSpeech has no voice "{wanted}". Installed: ' + ", ".join(f"{n}/{s}" for _, n, s in styles))
    return styles[0][0], f"{styles[0][1]} ({styles[0][2]})"


def accent(query):
    """The accent AivisSpeech expects, phrase by phrase: ア＼メ falls after ア; アメ￣ never falls."""
    out = []
    for ph in query.get("accent_phrases", []):
        moras, k = [m["text"] for m in ph["moras"]], ph.get("accent", 0)
        if not moras:
            continue
        out.append("".join(moras[:k]) + "＼" + "".join(moras[k:]) if 0 < k < len(moras) else "".join(moras) + "￣")
        if ph.get("is_interrogative"):
            out[-1] += "？"
    return "　".join(out)


def read_aloud(text, sid, dest):
    """AivisSpeech reads `text` into `dest`; returns the accent it used"""
    query = json.loads(call("/audio_query", {"text": text, "speaker": sid}, method="POST"))
    open(dest, "wb").write(call("/synthesis", {"speaker": sid}, body=query, method="POST"))
    return accent(query)


# ---- the report ------------------------------------------------------------------------------------------------

def draw(dest, mine, ref):
    fig, ax = plt.subplots(figsize=(5.2, 1.7), dpi=110)
    for (t, st), style, label in ((mine, dict(color="#1f6feb", lw=2.2), "clip"), (ref, dict(color="#d9480f", lw=1.6, ls="--"), "AivisSpeech")):
        if len(t):
            x = (t - t[0]) / max(t[-1] - t[0], 1e-6)
            gap = np.diff(t) > 0.035     # no line across a silence or a voiceless consonant
            xs, ys = np.insert(x, np.where(gap)[0] + 1, np.nan), np.insert(st, np.where(gap)[0] + 1, np.nan)
            ax.plot(xs, ys, label=label, **style)
    ax.axhline(0, color="#999", lw=0.6)
    ax.set_ylim(-9, 9)
    ax.set_xlim(-0.02, 1.02)
    ax.set_xticks([])
    ax.set_yticks([-6, 0, 6])
    ax.tick_params(labelsize=7)
    ax.set_ylabel("semitones", fontsize=7)
    ax.legend(fontsize=7, loc="upper right", frameon=False, ncol=2)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    fig.tight_layout(pad=0.4)
    fig.savefig(dest)
    plt.close(fig)


PAGE = """<!doctype html><meta charset="utf-8"><title>Pitch: {id}</title>
<style>body{{font:15px/1.45 system-ui,"Yu Gothic UI","Meiryo",sans-serif;margin:24px;color:#222;max-width:1150px}}
h1{{font-size:20px;margin:0 0 4px}} p{{margin:4px 0;color:#555}} table{{border-collapse:collapse;margin-top:14px;width:100%}}
td,th{{border-top:1px solid #ddd;padding:8px 10px;vertical-align:top;text-align:left}} th{{font-size:12px;color:#666}}
.n{{color:#888}} .ja{{font-size:17px}} .acc{{font-size:16px;color:#d9480f;letter-spacing:1px}} audio{{height:30px;width:210px;display:block;margin:2px 0}}
.s{{font-weight:600;padding:2px 8px;border-radius:10px;white-space:nowrap}} .ok{{background:#e6f4ea;color:#1e7b34}} .mid{{background:#fff4d6;color:#8a6100}}
.far{{background:#fde7e4;color:#b3261e}} small{{color:#777}}</style>
<h1>Pitch check: {id}</h1>
<p>Blue: the lesson's clip. Orange dashes: the same line read by AivisSpeech ({ref}). Semitones around each speaker's middle pitch; both stretched to the same width.</p>
<p>Accent: ＼ marks where the pitch falls; ￣ means it stays up. <b>match</b> compares the two shapes: a low figure means listen, not that the clip is wrong.</p>
{note}<table><tr><th>#</th><th>Line</th><th>Pitch</th><th>match</th><th>Listen</th></tr>
{rows}</table>"""


def run(L, only, wanted, with_ref):
    todo = [x for x in lines(L) if not only or x[0] in only]
    if not todo:
        sys.exit("no such clip")
    home = os.path.join(lib.ROOT, "_reports", "pitch", f"{L['course']}-{L['slug']}")
    os.makedirs(home, exist_ok=True)
    sid, ref_name = (None, "not used")
    if with_ref and L["course"] != "jap":
        print("AivisSpeech reads Japanese only: this lesson gets the clips' curves without a reference.")
    elif with_ref:
        sid, ref_name = reference(wanted)
        print(f"Reference: {ref_name}" if sid is not None else ref_name)
    note = "" if sid is not None else f"<p><b>No reference in this report.</b> {html.escape(ref_name)}</p>"
    rows, flagged = [], []
    for n, who, shown, said in todo:
        clip = lib.clip_file(L, n)
        if not clip or not os.path.exists(clip):
            print(f"  {n:02d}  no clip yet")
            rows.append(f'<tr><td class="n">{n:02d}</td><td>{html.escape(shown)}</td><td colspan="3"><small>no clip yet</small></td></tr>')
            continue
        mine = contour(clip)
        ref, acc, wav = (np.array([]), np.array([])), "", ""
        if sid is not None and said:
            wav = f"ref_{n:02d}.wav"
            try:
                acc = read_aloud(said, sid, os.path.join(home, wav))
                ref = contour(os.path.join(home, wav))
            except (urllib.error.URLError, OSError, ValueError, subprocess.CalledProcessError) as err:
                print(f"  {n:02d}  AivisSpeech could not read this line ({err})")
                wav = ""
        score = match(shape(*mine), shape(*ref)) if len(mine[0]) and len(ref[0]) else None
        draw(os.path.join(home, f"{n:02d}.png"), mine, ref)
        kind = "" if score is None else "ok" if score >= CLOSE else "mid" if score >= FAR else "far"
        if kind == "far":
            flagged.append(n)
        print(f"  {n:02d}  {'' if score is None else format(score, '5.2f')}  {'<<< listen' if kind == 'far' else '          '}  {shown}")
        rel = os.path.relpath(clip, home).replace("\\", "/")
        badge = "" if score is None else '<span class="s %s">%.2f</span>' % (kind, score)
        rows.append(
            f'<tr><td class="n">{n:02d}</td>'
            f'<td><b>{html.escape(who)}</b><br>{html.escape(shown)}<br><span class="ja">{html.escape(said)}</span>'
            + (f'<br><span class="acc">{html.escape(acc)}</span>' if acc else "") + "</td>"
            f'<td><img src="{n:02d}.png" width="480" alt=""></td>'
            f"<td>{badge}</td>"
            f'<td><small>clip</small><audio controls preload="none" src="{html.escape(rel)}"></audio>'
            + (f'<small>AivisSpeech</small><audio controls preload="none" src="{wav}"></audio>' if wav else "") + "</td></tr>")
    out = os.path.join(home, "index.html")
    open(out, "w", encoding="utf-8").write(PAGE.format(id=L["id"], ref=html.escape(ref_name), note=note, rows="\n".join(rows)))
    if sid is not None:
        print("\nLines to listen to: " + (", ".join(f"{n:02d}" for n in flagged) if flagged else "none below " + format(FAR, ".2f")))
    print(f"Report: {out}")
    return out


def main():
    a = sys.argv[1:]
    lesson = next((x for x in a if "/" in x and not x.startswith("-") and (a.index(x) == 0 or a[a.index(x) - 1] != "--ref")), "")
    if not lesson:
        lesson = input("Lesson (for example jap/speaking/hello_goodbye): ").strip()
    if not lesson:
        return
    only = []
    if "--only" in a:
        for x in a[a.index("--only") + 1:]:
            if not x.isdigit():
                break
            only.append(int(x))
    wanted = a[a.index("--ref") + 1] if "--ref" in a and a.index("--ref") + 1 < len(a) else DEFAULT_REF
    out = run(get(lesson), only, wanted, "--no-ref" not in a)
    if "--open" in a and hasattr(os, "startfile"):
        os.startfile(out)


if __name__ == "__main__":
    main()
