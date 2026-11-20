"""Makes a lesson file (content/<course>/<strand>/<name>.json) from a .md file, for every strand of the site.

    python -E tools/from_md.py check <file.md>        read it and list what is wrong; writes nothing
    python -E tools/from_md.py make <file.md>         write the lesson file and rebuild the pages
    python -E tools/from_md.py make <file.md> --force     replace the text of a lesson that already exists (level, topic,
                                                          audio wire and anything else you set by hand are kept)
    python -E tools/from_md.py status                 every .md in the .md folder and how far its lesson is
    (make also takes --name --level --topic --images --course --strand, which win over the .md's header)

<file.md> is a path, or a file name in the .md folder (Desktop/story-md; --md <folder> for another one).
lesson_app.bat is the window on top of this tool.

EVERY .md STARTS WITH A HEADER

    # Title of the lesson
    type: story               story | reading | conversation | listening | vocabulary | fundamentals | expressions | pronunciation
    course: fr                fr | eng | jap    (may be left out when the lines are tagged FR:, or EN: + MY:)
    level: a1                 pre-a1 a1 a2 b1 b2 c1   (left out: guessed, and marked "level_provisional")
    topic: Animals            the heading it sits under on the strand page
    name: chien_sans_maison   the lesson's file name (left out: the .md's own name)
    strand: grammar           only to put a lesson in another strand than its type's own (grammar has no type of its own)
    subtitle: ...   intro: ...   register: ...   order: 3        optional

The older story header (page: / slug: / menu: / brand:) still works: `page` is the lesson name unless it is "stories".
Lines starting with // and ``` are ignored.

Tags: the course's own language is FR: (French), EN: (English) or JA: (Japanese, romaji). Any other of
EN: MY: FR: is a translation of the line above it.

1. STORY (picture reader, Reading; with `type: vocabulary` it is a picture word list)          type: story
    ## 1                            one "## N" per picture N.jpg;  "## 9 | New Words" adds a small heading
    FR: Marie habite / dans une petite ville.       " / " cuts the sentence into chunks: one audio clip each
    EN: Marie lives in a small town.                one translation line per sentence
  or one chunk per line:
    EN: One sunny morning,
    EN: a hungry dog
    MY: ...
  `images: <folder>` names the picture folder in img/ytstory (left out: an existing folder named like the .md).

2. READING (a text for adults, Reading)                                                         type: reading
    FR: Qu'est-ce qui est doré comme le miel ?      one line per sentence (one clip each)
    EN: What is golden like honey?
    GLOSS: doré = /dɔʀe/ | golden ; brille = /bʀij/ | shines | briller /bʀije/
    ---                                             a line of dashes (or a "## heading") starts a new paragraph
  Optional header lines: img: img/Fr-read/amber.jpg   img_alt: A piece of amber

3. CONVERSATION (Speaking; `type: listening` puts it in Listening)                              type: conversation
    speakers: C = Client, B = Boulangère            header; lines then start with the speaker's letter
    voice: B = <ElevenLabs voice id>                header, optional: speakers who do not use the course voice
    hidden: yes                                     header, optional: the text starts hidden (listening)

    C: Bonjour madame !
    EN: Hello!
    NOTE: Always open with bonjour.                 optional
    ## At the till                                  optional: a titled section
  Without speakers, tag the lines FR: / EN: / JA:. Japanese: the line is romaji, then KANA: and, if needed, SAY:.

4. VOCABULARY and FUNDAMENTALS (word lists)                              type: vocabulary  /  type: fundamentals
    ## Rooms | Les pièces                           a group (and its small sub-heading)
    cuisine | f | /kɥizin/ | kitchen                word | gender | /IPA/ | meaning   (gender and IPA may be left out)
    NOTE: ...                                       a note under the group
  Japanese: romaji | kana | meaning, and  say=<what the voice reads>  as one more field when needed.

5. EXPRESSIONS (flashcards)                                                                     type: expressions
    ## Everyday agreement | D'accord                a category: English title | title in the other language
    DESC: The basic yes to a plan or an opinion.
    FR: Je suis d'accord.                           a card
    EN: I agree.                                    its meaning
    NOTE: Agreement with an opinion.                optional
    EX: Je suis d'accord avec toi.                  an example, and its translation on the next line
    EN: I agree with you.

6. PRONUNCIATION (shadowing)                                                                    type: pronunciation
    FR: Bonjour !                                   one chunk (one clip) per line
    EN: Hello!

A lesson of any type may end with these sections:
    ## questions                      ## notes                 ## steps                 ## focus   (shadowing)
    Q: Where does Thomas work?        - bosser = travailler    - Listen first.          - The last syllable is stressed.
    - At the station
    * In a café                       the answer starts with *
    WHY: Je bosse dans un café.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
ROOT = lib.ROOT
MD_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "story-md")
YT_DIR = r"G:\My Drive\_YOUTUBE"
OWN = {"fr": "FR", "eng": "EN", "jap": "JA"}
LANG = {"EN": "en", "MY": "my", "FR": "fr"}
LABEL = {"en": "English", "my": "မြန်မာ", "fr": "Français"}
HEADER = ("type course strand name page slug menu brand level topic subtitle intro register order images img img_alt "
          "speakers voice hidden group template review").split()
TYPES = {   # the .md's type -> (lesson type, strand)
    "story": ("reader", "reading"), "reader": ("reader", "reading"), "reading": ("text", "reading"), "text": ("text", "reading"),
    "conversation": ("dialogue", "speaking"), "conversations": ("dialogue", "speaking"), "dialogue": ("dialogue", "speaking"),
    "speaking": ("dialogue", "speaking"), "listening": ("dialogue", "listening"),
    "vocabulary": ("words", "vocabulary"), "vocab": ("words", "vocabulary"), "words": ("words", "vocabulary"),
    "fundamentals": ("words", "fundamentals"), "expressions": ("cards", "expressions"), "expression": ("cards", "expressions"),
    "cards": ("cards", "expressions"), "pronunciation": ("shadow", "pronunciation"), "shadowing": ("shadow", "pronunciation"),
    "shadow": ("shadow", "pronunciation")}
MENU_TOPIC = {"aesop": "Aesop's fables", "science": "Science and nature", "stories": "Fairy tales and stories"}
TOPIC = {"reader": "Stories", "text": "Reading", "dialogue": "Conversations", "words": "Words", "cards": "Everyday expressions", "shadow": "Shadowing practice"}
EXTRA = {"notes": "notes", "questions": "questions", "quiz": "questions", "steps": "steps", "focus": "focus"}
CURLY = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})
TAG = re.compile(r"([A-Za-z][\w-]{0,11})\s*(?:\[[^\]]*\])?\s*:\s*(.*)$")


class Md:
    def __init__(self, path):
        self.path, self.file, self.base = path, os.path.basename(path), os.path.splitext(os.path.basename(path))[0]
        self.title, self.f, self.body, self.extra, self.errors, self.warnings = None, {}, [], {}, [], []
        section, started = None, False
        for i, raw in enumerate(open(path, encoding="utf-8-sig").read().splitlines(), 1):
            line = raw.strip()
            if line.startswith("```") or line.startswith("//"):
                continue
            if not started:
                m = TAG.fullmatch(line)
                if not line:
                    continue
                if line.startswith("# "):
                    self.title = line[2:].strip()
                    continue
                if m and m.group(1).lower() in HEADER:
                    self.f[m.group(1).lower()] = m.group(2).strip()
                    continue
                started = True
            if line.startswith("##"):
                section = EXTRA.get(line.lstrip("#").strip().lower())
                if section:
                    self.extra.setdefault(section, [])
                    continue
            (self.extra[section] if section else self.body).append((i, line))

    def err(self, i, text):
        self.errors.append(f"line {i}: {text}" if i else text)


def tagged(line):
    m = TAG.fullmatch(line)
    return (m.group(1).upper() if m.group(1).upper() in LANG or m.group(1).isupper() else m.group(1), m.group(2).strip()) if m else (None, line)


def heading(line):
    """'## Rooms | Les pièces' -> ['Rooms', 'Les pièces']"""
    return [p.strip() for p in line.lstrip("#").split("|")]


def bullets(d, name):
    return [re.sub(r"^[-*]\s*", "", line) for _, line in d.extra.get(name, []) if line]


def questions(d):
    out = []
    for i, line in d.extra.get("questions", []):
        tag, text = tagged(line)
        if not line:
            continue
        if tag == "Q":
            out.append({"q": text, "options": [], "i": i})
        elif not out:
            d.err(i, "a question starts with 'Q:'")
        elif tag == "WHY":
            out[-1]["why"] = text
        elif line[0] in "-*":
            if line[0] == "*":
                out[-1]["answer"] = len(out[-1]["options"])
            out[-1]["options"].append(line[1:].strip())
        else:
            d.err(i, f"in questions, expected Q:, '- option', '* the answer' or WHY: {line}")
    for q in out:
        i = q.pop("i")
        if len(q["options"]) < 2 or "answer" not in q:
            d.err(i, "a question needs at least two options, one of them starting with * (the answer)")
    return [{k: q[k] for k in ("q", "options", "answer", "why") if k in q} for q in out]


def reader(d, course):
    own, pages, cur, n = OWN[course], [], None, 0
    for i, line in d.body:
        tag, text = tagged(line)
        if not line:
            cur = None
        elif line.startswith("##"):
            m = re.fullmatch(r"##\s*(\d+)\s*(?:\|\s*(.+))?", line)
            cur = None
            if not m:
                d.err(i, f"a picture heading is '## N' or '## N | Heading': {line}")
                continue
            pages.append({"img": int(m.group(1)), "heading": m.group(2), "i": i, "s": []})
        elif not pages:
            d.err(i, f"text before the first '## 1' heading: {line}")
        elif tag == own:
            if cur is None or cur["tr"]:
                cur = {"chunks": [], "tr": {}}
                pages[-1]["s"].append(cur)
            for part in re.split(r"\s+/\s+", text.translate(CURLY)):
                if part:
                    n += 1
                    cur["chunks"].append([part, n])
                    if len(part.split()) > 12:
                        d.warnings.append(f"line {i}: {len(part.split())} words in one chunk, probably a missed split: {part}")
        elif tag in LANG:
            if cur is None:
                d.err(i, f"a {tag}: line with no {own}: line above it")
            else:
                cur["tr"][LANG[tag]] = text
        else:
            d.err(i, f"not a {own}: line, a translation or a '## N' heading: {line}")
    if not pages:
        d.err(0, "no '## 1', '## 2' ... picture headings")
    langs = [k for k in ("my", "en", "fr") if any(k in s["tr"] for p in pages for s in p["s"])]
    out = []
    for k, p in enumerate(pages, 1):
        if p["img"] != k:
            d.err(p["i"], f"picture {p['img']}, expected {k} (pictures run 1, 2, 3 ... in order)")
        if not p["s"]:
            d.err(p["i"], f"picture {p['img']} has no sentences")
        page = {"img": p["img"]}
        if langs:
            page["tr"] = [s["tr"].get(langs[0], "") for s in p["s"]]
            gaps = sum(1 for t in page["tr"] if not t)
            if gaps:
                d.warnings.append(f"line {p['i']}: picture {p['img']} has {gaps} sentence(s) with no translation")
        if p["heading"]:
            page["heading"] = p["heading"]
        page["sentences"] = [s["chunks"] for s in p["s"]]
        out.append(page)
    doc = {"translation": {"lang": langs[0], "label": LABEL[langs[0]]}} if langs else {}
    doc["pages"] = out
    return doc


def pairs(text):
    """'C = Client, B = Boulangère' -> {'C': 'Client', 'B': 'Boulangère'}"""
    return {a.strip(): b.strip() for a, b in (p.split("=", 1) for p in text.split(",") if "=" in p)}


def dialogue(d, course):
    who = pairs(d.f.get("speakers", ""))
    sections, cur, langs = [{"lines": []}], None, []
    text_key = "romaji" if course == "jap" else "text"
    for i, line in d.body:
        tag, text = tagged(line)
        if not line:
            continue
        if line.startswith("##"):
            sections.append({"title": heading(line)[0], "lines": []})
            cur = None
        elif tag in who or tag in (OWN[course], "ROMAJI"):
            cur = {"who": tag} if tag in who else {}
            cur[text_key] = text
            sections[-1]["lines"].append(cur)
        elif cur is None:
            d.err(i, f"expected a line starting with {', '.join(list(who) or [OWN[course]])}: {line}")
        elif tag in LANG:
            cur.setdefault("tr", {})[LANG[tag]] = text
            if LANG[tag] not in langs:
                langs.append(LANG[tag])
        elif tag in ("KANA", "SAY", "NOTE"):
            cur[tag.lower()] = text
        else:
            d.err(i, f"not a speaker's line, a translation, KANA:, SAY: or NOTE: {line}")
    sections = [s for s in sections if s["lines"]]
    if not sections:
        d.err(0, "no lines")
    order = ("who", "text", "romaji", "kana", "tr", "note", "say")
    for s in sections:
        s["lines"] = [{k: l[k] for k in order if k in l} for l in s["lines"]]
    doc = {}
    if who:
        doc["speakers"] = who
    if d.f.get("voice"):
        doc["voice"] = pairs(d.f["voice"])
    if d.f.get("hidden", "").lower() in ("yes", "true", "1"):
        doc["start_hidden"] = True
    if langs:
        doc["support"] = sorted(langs)
    if len(sections) == 1 and "title" not in sections[0]:
        doc["lines"] = sections[0]["lines"]
    else:
        doc["sections"] = sections
    return doc


def words(d, course):
    groups = []
    for i, line in d.body:
        tag, text = tagged(line)
        if not line or line == "---":
            continue
        if line.startswith("##"):
            h = heading(line)
            groups.append({"title": h[0], **({"sub": h[1]} if len(h) > 1 and h[1] else {}), "words": []})
            continue
        if not groups:
            groups.append({"title": "", "words": []})
        if tag == "NOTE":
            groups[-1].setdefault("notes", []).append(text)
            continue
        parts = [p.strip() for p in re.sub(r"^[-*]\s*", "", line).split("|")]
        w, rest = {"fr": parts[0]}, []
        for p in parts[1:]:
            if p.lower().startswith("say="):
                w["say"] = p[4:].strip()
            elif re.fullmatch(r"/.+/", p) or (course == "jap" and "ipa" not in w and re.search("[぀-ヿ一-鿿]", p)):
                w["ipa"] = p
            elif re.fullmatch(r"(m|f|n|mf|m/f)( ?pl)?\.?", p, re.I) and course != "jap":
                w["g"] = p.lower().rstrip(".")
            elif p:
                rest.append(p)
        if not parts[0] or not rest:
            d.err(i, f"a word line is 'word | gender | /IPA/ | meaning' (gender and IPA may be left out): {line}")
            continue
        if len(rest) > 1:
            d.warnings.append(f"line {i}: more than one meaning field, joined with ' | ': {line}")
        w["en"] = " | ".join(rest)
        groups[-1]["words"].append({k: w[k] for k in ("fr", "g", "ipa", "en", "say") if k in w})
    groups = [g for g in groups if g["words"]]
    if not groups:
        d.err(0, "no words")
    return {"groups": [{k: g[k] for k in ("title", "sub", "notes", "words") if k in g} for g in groups]}


def cards(d, course):
    own, other = OWN[course], "my" if course == "eng" else "fr"
    cats, cur, last = [], None, None
    for i, line in d.body:
        tag, text = tagged(line)
        if not line:
            continue
        if line.startswith("##"):
            h = heading(line)
            cats.append({"en": h[0], other: h[1] if len(h) > 1 else "", "desc": "", "cards": []})
            cur = None
        elif not cats:
            d.err(i, f"cards start after a '## Category' heading: {line}")
        elif tag == "DESC":
            cats[-1]["desc"] = text
        elif tag == own:
            cur, last = {"p": text, "m": "", "n": "", "ex": []}, "p"
            cats[-1]["cards"].append(cur)
        elif cur is None:
            d.err(i, f"expected a card ({own}: ...): {line}")
        elif tag == "EX":
            cur["ex"].append([text, ""])
            last = "ex"
        elif tag in LANG:
            if last == "ex":
                cur["ex"][-1][1] = text
            else:
                cur["m"] = text
            last = "p"
        elif tag == "NOTE":
            cur["n"] = text
        else:
            d.err(i, f"not a card, its meaning, NOTE:, EX: or DESC: {line}")
    for c in cats:
        c["cards"] = [[x["p"], x["m"], x["n"], *[t for pair in (x["ex"] or [["", ""]]) for t in pair]] for x in c["cards"]]
    cats = [c for c in cats if c["cards"]]
    if not cats:
        d.err(0, "no cards")
    return {"categories": cats}


def shadow(d, course):
    chunks = []
    for i, line in d.body:
        tag, text = tagged(line)
        if not line or line.startswith("##") or line == "---":
            continue
        if tag == OWN[course]:
            chunks.append({"text": text})
        elif tag in LANG and chunks:
            chunks[-1].setdefault("tr", text)
        else:
            d.err(i, f"not a {OWN[course]}: line or its translation: {line}")
    if not chunks:
        d.err(0, "no chunks")
    return {"chunks": chunks}


def text_lesson(d, course):
    paras, langs = [[]], []
    for i, line in d.body:
        tag, text = tagged(line)
        if not line:
            continue
        if line.startswith("##") or re.fullmatch(r"-{3,}", line):
            paras.append([])
        elif tag == OWN[course]:
            paras[-1].append({"text": text})
        elif not paras[-1]:
            d.err(i, f"expected a sentence ({OWN[course]}: ...): {line}")
        elif tag in LANG:
            paras[-1][-1].setdefault("tr", {})[LANG[tag]] = text
            if LANG[tag] not in langs:
                langs.append(LANG[tag])
        elif tag == "GLOSS":
            for item in text.split(";"):
                if "=" in item:
                    word, val = item.split("=", 1)
                    paras[-1][-1].setdefault("gloss", {})[word.strip()] = [p.strip() for p in val.split("|")]
        else:
            d.err(i, f"not a sentence, a translation or GLOSS: {line}")
    paras = [p for p in paras if p]
    if not paras:
        d.err(0, "no sentences")
    doc = {k: d.f[k] for k in ("img", "img_alt") if d.f.get(k)}
    if langs:
        doc["support"] = sorted(langs)
    doc["paragraphs"] = paras
    return doc


PARSE = {"reader": reader, "dialogue": dialogue, "words": words, "cards": cards, "shadow": shadow, "text": text_lesson}
CONTENT = {"reader": ["pages", "translation"], "dialogue": ["lines", "sections", "speakers", "support"], "words": ["groups"],
           "cards": ["categories"], "shadow": ["chunks"], "text": ["paragraphs", "support"]}


def plan(d, over, C):
    """The lesson a .md describes: (lesson as it would be written, course, strand, name), or None when the .md is not a lesson."""
    f = {**d.f, **{k: v for k, v in over.items() if v}}
    kind = f.get("type", "").lower()
    if "quiz" in kind:
        return None
    tags = {tagged(line)[0] for _, line in d.body}
    numbered = [line for _, line in d.body if line.startswith("##")]
    numbered = bool(numbered) and all(re.fullmatch(r"##\s*\d+\s*(\|.*)?", h) for h in numbered)
    if not kind and numbered:
        kind = "story"
    if kind not in TYPES:
        d.err(0, f"the header needs 'type:' (story, reading, conversation, listening, vocabulary, fundamentals, expressions or pronunciation)" + (f", not '{kind}'" if kind else ""))
        return None
    typ, strand = TYPES[kind]
    if typ == "words" and numbered and tags & set(OWN.values()):   # picture words: a reader in the vocabulary strand
        typ = "reader"
    course = f.get("course", "").lower()
    course = {"french": "fr", "english": "eng", "en": "eng", "japanese": "jap", "ja": "jap"}.get(course, course)
    if not course:
        course = "fr" if "FR" in tags else "jap" if tags & {"JA", "KANA", "ROMAJI"} else "eng" if "EN" in tags and ("MY" in tags or typ == "reader") else ""
    if course not in C["courses"]:
        d.err(0, "the header needs 'course: fr', 'course: eng' or 'course: jap'" + (f", not '{course}'" if course else ""))
        return None
    strands = C["courses"][course]["strands"]
    strand = f.get("strand", "").lower() or strand
    if strand not in strands:
        d.err(0, f"{C['courses'][course]['name']} has no '{strand}' strand (it has: {', '.join(strands)}). Set 'strand:' in the header")
    page = f.get("page", "")
    name = re.sub(r"[^A-Za-z0-9_.]+", "_", f.get("name") or (page if page and page != "stories" else d.base)).strip("_")
    if not d.title:
        d.err(0, "no '# Title' line")
    doc = {"title": d.title or name}
    for k in ("subtitle",):
        if f.get(k):
            doc[k] = f[k]
    levels = C["courses"][course]["levels"]
    level = f.get("level", "").lower()
    if level and level not in levels:
        d.err(0, f"level '{level}' is not a level of this course ({', '.join(levels)})")
    if not level:
        m = re.search(r"(?<![a-z0-9])(pre-a1|a1|a2|b1|b2|c1)(?![a-z0-9])", f"{f.get('slug', '')} {f.get('menu', '')} {name}".lower().replace("_", " "))
        level = m.group(1) if m and m.group(1) in levels else ""
    doc["level"] = level or ("a2" if "a2" in levels else levels[0])
    if not level:
        doc["level_provisional"] = True
    doc["topic"] = f.get("topic") or (MENU_TOPIC.get(f.get("menu", "")) if course == "eng" else None) or TOPIC[typ]
    doc["type"] = typ
    for k in ("register", "intro"):
        if f.get(k):
            doc[k] = f[k]
    if f.get("order", "").isdigit():
        doc["order"] = int(f["order"])
    doc["source_md"] = d.file
    wire = f"{course}/{strand}/{name}/"
    if typ == "reader":
        cands = [c for c in (f.get("images"), f.get("slug"), d.base, name) if c]
        folder = next((c for c in cands if os.path.isdir(os.path.join(ROOT, "img", "ytstory", c))), None) \
            or next((c for c in cands if os.path.isdir(os.path.join(YT_DIR, c))), None) or f.get("images") or d.base
        doc.update({"img_dir": f"img/ytstory/{folder}/", "img_ext": "jpg"})
    if typ == "words":
        doc["glossary_dir"] = wire
    else:
        doc.update({"aud_dir": wire, "aud_ext": "mp3?v=pending"})
    doc.update(PARSE[typ](d, course))
    q = questions(d)
    if q:
        doc["questions"] = q
    for k in ("notes", "steps", "focus"):
        if bullets(d, k):
            doc[k] = bullets(d, k)
    return doc, course, strand, name


def as_lesson(doc, course, strand, name):
    L = lib.normalize(json.loads(json.dumps(doc)))
    L.update({"course": course, "strand": strand, "slug": name, "id": f"{course}/{strand}/{name}", "file": None})
    return L


def find_lesson(d, got, lessons):
    """The lesson a .md belongs to, if it was made already (by this tool, or imported from the old site)."""
    for L in lessons:
        if L.get("source_md") == d.file:
            return L
    if not got:
        return None
    doc, course, strand, name = got
    by_id = {L["id"]: L for L in lessons}
    if f"{course}/{strand}/{name}" in by_id:
        return by_id[f"{course}/{strand}/{name}"]
    if doc["type"] == "reader":
        same = [L for L in lessons if L["course"] == course and L.get("type") == "reader"]
        for L in same:
            if L["slug"] == d.f.get("page"):
                return L
        for L in same:
            if L.get("img_dir", "").strip("/").split("/")[-1] in (d.f.get("slug"), d.base):
                return L
    return None


def word_items(L):
    return [w for g in L.get("groups", []) for w in g.get("words", [])] + [p for s in L.get("slides", []) for p in s.get("spots", [])]


def state(L):
    """What a lesson has and what it still needs: clips, pictures, upload, offline copy."""
    out = {"id": L["id"], "kind": L.get("type"), "level": L.get("level", ""), "topic": L.get("topic", "")}
    if L.get("type") in ("words", "hotspots"):
        gd = L.get("glossary_dir", "")
        mdir = (lib.find("media/" + gd) if gd else None) or os.path.join(ROOT, "media", *gd.strip("/").split("/"))
        items = word_items(L)
        miss = [(i, w) for i, w in enumerate(items, 1) if not (w.get("audio") and os.path.exists(os.path.join(mdir, w["audio"])))]
        out.update({"audio": "words", "total": len(items), "missing": [i for i, _ in miss], "media": mdir,
                    "texts": {str(i): lib.spoken(w.get("say") or w["fr"]) for i, w in miss}, "tag": L.get("audio_ver", ""),
                    "pending": not L.get("audio_ver")})
    else:
        cl = lib.clips(L)
        own = bool(cl) and not L.get("aud_shared") and not L.get("audio_file") and all(t for _, t in cl)
        miss = [n for n, _ in cl if not os.path.exists(lib.clip_file(L, n) or "")] if own else []
        m = re.search(r"\?v=(.*)$", L.get("aud_ext", ""))
        out.update({"audio": "clips" if own else "none", "total": len(cl) if own else 0, "missing": miss, "media": lib.media_dir(L) or "",
                    "texts": {str(n): lib.spoken(t) for n, t in cl if n in miss}, "tag": m.group(1) if m else "", "pending": own and lib.pending(L)})
    out["chars"] = sum(len(t) for t in out["texts"].values())
    if L.get("type") == "reader" and out["audio"] == "clips" and out["missing"]:   # a new story is also read page by page (p01.mp3 ...)
        mdir = lib.media_dir(L) or ""
        out["chars"] += sum(len(" ".join(lib.spoken(c[0]) for s in p["sentences"] for c in s)) for k, p in enumerate(L.get("pages", []), 1)
                            if not os.path.exists(os.path.join(mdir, f"p{k:02d}.mp3")))
    imgs = lib.images(L)
    gone = [x for x in imgs if not lib.find(x)]
    out["pictures"] = {"total": len(imgs), "missing": len(gone), "dir": L.get("img_dir", ""), "ext": L.get("img_ext", "jpg"),
                       "numbers": [p["img"] for p in L.get("pages", []) if p.get("img")] if L.get("type") == "reader" else [],
                       "missing_names": [os.path.basename(x) for x in gone]}
    single = os.path.join(ROOT, L["course"], "single", f"{L['strand']}__{L['slug']}.html")
    out["single"] = single
    out["single_exists"] = os.path.exists(single)
    out["single_fresh"] = out["single_exists"] and (not L.get("file") or os.path.getmtime(single) >= os.path.getmtime(L["file"]))
    return out


def load(arg, md_dir):
    path = arg if os.path.exists(arg) else os.path.join(md_dir, arg if arg.lower().endswith(".md") else arg + ".md")
    if not os.path.exists(path):
        sys.exit(f"no such file: {arg} (looked in {md_dir} too)")
    return Md(path)


def status(md_dir, as_json):
    C, lessons, rows = lib.cfg(), lib.lessons(), []
    for name in sorted(os.listdir(md_dir), key=str.lower) if os.path.isdir(md_dir) else []:
        if not name.lower().endswith(".md"):
            continue
        d = Md(os.path.join(md_dir, name))
        got = plan(d, {}, C)
        if not got and "quiz" in d.f.get("type", "").lower():   # quiz files belong to the old site's quiz tools
            continue
        L = find_lesson(d, got, lessons)
        row = {"md": name, "path": d.path, "title": d.title or "", "type": d.f.get("type", "story" if got else "?").lower(),
               "exists": bool(L), "problems": d.errors, "warnings": d.warnings, "course": got[1] if got else "", "strand": got[2] if got else "",
               "name": got[3] if got else d.base}
        if L or got:
            row.update(state(L or as_lesson(*got)))
            row["lesson_file"] = L["file"] if L else os.path.join(ROOT, "content", got[1], got[2], got[3] + ".json")
            if L:
                row.update({"course": L["course"], "strand": L["strand"], "name": L["slug"]})
            row["levels"] = C["courses"][row["course"]]["levels"]
            row["topics"] = sorted({x.get("topic") for x in lessons if x["course"] == row["course"] and x["strand"] == row["strand"] and x.get("topic")})
        rows.append(row)
    if as_json:
        sys.stdout.write(json.dumps({"md_dir": md_dir, "rows": rows}))   # ASCII only: read by lesson_app.bat
        return
    for r in rows:
        if r["problems"]:
            print(f"{r['md']:<32} {len(r['problems'])} problem(s): {r['problems'][0]}")
        else:
            pic = r["pictures"]
            print(f"{r['md']:<32} {r['id']:<40} {'made' if r['exists'] else 'NOT MADE':<9} clips {r['total'] - len(r['missing'])}/{r['total']}"
                  f"  pictures {pic['total'] - pic['missing']}/{pic['total']}  {'pending' if r['pending'] else r['tag']}")
    print(f"{len(rows)} lesson .md file(s) in {md_dir}")


def report(d):
    for w in d.warnings:
        print("warning:", w)
    if d.errors:
        print(f"{d.file}: {len(d.errors)} problem(s)")
        for e in d.errors:
            print("  ", e)
        sys.exit(1)


def make(d, over, force, write=True):
    C = lib.cfg()
    got = plan(d, over, C)
    report(d)
    if not got:
        sys.exit(f"{d.file} is a quiz file, not a lesson")
    doc, course, strand, name = got
    lessons = lib.lessons()
    old = find_lesson(d, got, lessons)
    new = as_lesson(*got)
    st = state(new)
    print(f"{d.file}: {doc['type']} lesson {new['id']}, level {doc['level']}{' (a guess)' if doc.get('level_provisional') else ''}, topic '{doc['topic']}', "
          + (f"{st['total']} words" if st["audio"] == "words" else f"{st['total']} clips") + (f", {st['pictures']['total']} pictures in {doc['img_dir']}" if doc.get("img_dir") else "") + ": OK")
    if not write:
        if old:
            print(f"the lesson is already made: {os.path.relpath(old['file'], ROOT)}")
        return
    if old and not force:
        sys.exit(f"{os.path.relpath(old['file'], ROOT)} is already there (--force replaces its text)")
    dest = os.path.join(ROOT, "content", course, strand, name + ".json")
    if old:   # keep what was set by hand or by the audio tool; take the text from the .md
        dest = old["file"]
        kept = json.load(open(dest, encoding="utf-8"))
        before = dict(lib.clips(old))
        if doc["type"] == "words":   # words keep the clips they already have
            names = {w["fr"]: w["audio"] for w in word_items(kept) if w.get("audio")}
            for w in word_items(doc):
                if w["fr"] in names:
                    w["audio"] = names[w["fr"]]
        for k in ["title", "source_md", "questions", "notes", "steps", "focus"] + CONTENT[doc["type"]] + [k for k in d.f if k in doc] + [k for k, v in over.items() if v and k in doc]:
            if k in doc:
                kept[k] = doc[k]
            elif k in ("lines", "sections", "translation"):
                kept.pop(k, None)
        if "level" in d.f or over.get("level"):
            kept.pop("level_provisional", None)
        doc = kept
        after = dict(lib.clips(as_lesson(doc, old["course"], old["strand"], old["slug"])))
        changed = sorted(n for n in set(before) | set(after) if lib.spoken(before.get(n, "")) != lib.spoken(after.get(n, "")))
        if changed and before:
            print(f"clips whose text changed: {' '.join(map(str, changed))}. Make new takes of them (and of any clip that no longer exists).")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print(("replaced the text of " if old else "wrote ") + os.path.relpath(dest, ROOT))
    import build
    build.main()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Make a lesson file from a .md", epilog="The .md formats: open tools/from_md.py and read its first lines.")
    ap.add_argument("cmd", choices=["status", "check", "make"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--md", default=MD_DIR, help="the folder of .md files")
    ap.add_argument("--yt", default=YT_DIR, help="the folder the original PNGs are kept in")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--force", action="store_true")
    for k in ("name", "level", "topic", "images", "course", "strand"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    YT_DIR = a.yt
    if a.cmd == "status":
        status(a.md, a.json)
    elif not a.file:
        ap.error("which .md file?")
    else:
        make(load(a.file, a.md), {k: getattr(a, k) for k in ("name", "level", "topic", "images", "course", "strand")}, a.force, write=a.cmd == "make")
