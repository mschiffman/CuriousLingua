"""Builds the whole site from content/ and site.json.

    python tools/build.py

Writes index.html, <course>/index.html, <course>/level/<level>.html, <course>/<strand>/index.html,
one page per lesson and assets/data/catalog.json. Every page is generated:
edit the lesson files in content/, never the .html. Standard library only.
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
ROOT, C = lib.ROOT, lib.cfg()
e = html.escape


def ver(rel):
    """A short tag of a file's content. Pages load site.js and site.css as "site.js?v=<tag>": when the file changes,
    so does its address, and no browser or CDN goes on serving a saved copy of the old one."""
    import hashlib
    return hashlib.md5(open(os.path.join(ROOT, *rel.split("/")), "rb").read()).hexdigest()[:8]


FRESH = {f'assets/{x}"': f'assets/{x}?v={ver("assets/" + x)}"' for x in ("js/site.js", "css/site.css")}
TYPE = {"cards": "Flashcards", "reader": "Picture reader", "dialogue": "Dialogue", "shadow": "Shadowing", "text": "Reading text", "practice": "Practice", "game": "Game", "words": "Word list", "hotspots": "Picture hotspots", "page": "Page", "link": "Link", "grammar": "Grammar notes", "timeline": "Interactive timeline", "family": "Family tree"}
ICON_PLAY = '<svg viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>'
ICON_LOOP = '<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></svg>'
ICON_TR = '<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="11" height="11" rx="2"/><path d="M6.5 11l2-5 2 5M7.2 9.5h2.6"/><rect x="10" y="10" width="11" height="11" rx="2" fill="currentColor" stroke="none"/><path d="M13 14h5M15.5 13v1c0 2-1 3.500-2.500 4.200M14.200 16c.8 1.200 2 2 3.300 2.200" stroke="#fff" stroke-width="1.300"/></svg>'
ICON_IMG = '<svg viewBox="0 0 24 24" class="h-10 w-10" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M21 16l-5-5-8 8"/></svg>'


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def write(rel, text):
    path = os.path.join(ROOT, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def up(rel):
    return "../" * rel.count("/")


def lv(code):
    return code.upper().replace("PRE-A1", "Pre-A1") if code else "?"


# ------------------------------------------------------------------ page frame
# Motion (assets/js/motion.js): this head script hides [data-reveal] / [data-split] until motion.js shows them,
# and shows them again by itself if motion.js has not run after 3 s. Nothing is hidden for reduced motion, or on slow
# or data-saver connections, where GSAP could take seconds to arrive (the text then simply shows at once).
# Those visitors get <html class="lite">, which also leaves out the home page globe (it needs Three.js, ~600 KB).
MOTION_HEAD = ('<script>(function(d){var c=navigator.connection;if(matchMedia("(prefers-reduced-motion: reduce)").matches'
               '||(c&&(c.saveData||/2g|3g/.test(c.effectiveType||"")))){d.classList.add("lite");return}d.classList.add("motion");'
               'setTimeout(function(){if(!window.__motion)d.classList.remove("motion")},3000)})(document.documentElement)</script>\n')
# GSAP sits in assets/vendor/: tools/offline.py leaves that folder out of the single-file lessons (motion.js then does nothing).
MOTION_TAIL = ('<script defer src="{r}assets/vendor/gsap.min.js"></script>\n<script defer src="{r}assets/vendor/ScrollTrigger.min.js"></script>\n'
               '<script defer src="{r}assets/js/motion.js"></script>')


def hero_canvas(which):
    """The 3D letters behind a title (assets/js/hero.js): which = a course key, or "all"."""
    return f'<canvas class="hero-canvas" data-hero="{which}" aria-hidden="true"></canvas>'


def frame(rel, title, body, course=None, tail="", cls="site", head="", foot=True):
    r = up(rel)
    nav = "".join(
        f'<a href="{r}{k}/index.html" data-course="{k}" class="rounded-lg px-2.5 py-1.5 font-bold hover:bg-accent/10 hover:text-accent'
        f'{" bg-accent/10 text-accent" if k == course else ""}">{e(c["name"])}</a>' for k, c in C["courses"].items())
    sub = ""
    if course:
        cc = C["courses"][course]
        sub = '<div class="hidden border-t border-line sm:block"><div class="wrap flex gap-1 overflow-x-auto py-1.5 text-sm">' + "".join(
            f'<a href="{r}{course}/{s}/index.html" class="whitespace-nowrap rounded-lg px-2.5 py-1 text-muted hover:bg-accent/10 hover:text-accent">{e(C["strands"][s][0])}</a>'
            for s in cc["strands"]) + "</div></div>"
    item = 'class="block rounded-lg px-3 py-2 hover:bg-accent/10 hover:text-accent"'
    menu = "".join(f'<a {item} data-course="{k}" href="{r}{k}/index.html"><b>{e(c["name"])}</b></a>' for k, c in C["courses"].items())
    if course:
        menu += '<div class="rule my-2"></div>' + "".join(
            f'<a {item} href="{r}{course}/{s}/index.html">{e(C["strands"][s][0])}</a>' for s in C["courses"][course]["strands"])
    header = f'''<header class="sticky top-0 z-30 shrink-0 border-b border-line bg-paper/95 backdrop-blur" data-nav>
<div class="wrap flex h-12 items-center gap-2 sm:h-14">
<a href="{r}index.html" class="mr-2 font-display text-xl font-semibold tracking-tight">{e(C["site_name"])}</a>
<nav class="hidden items-center gap-0.5 text-sm sm:flex" aria-label="Courses">{nav}</nav>
<details class="relative ml-auto sm:hidden">
<summary class="flex h-9 w-9 cursor-pointer list-none items-center justify-center rounded-lg border border-line bg-card [&::-webkit-details-marker]:hidden" aria-label="Menu">
<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></summary>
<nav class="absolute right-0 top-11 z-40 max-h-[75dvh] w-64 overflow-y-auto rounded-2xl border border-line bg-card p-2 text-base shadow-lg" aria-label="Menu">{menu}</nav>
</details>
</div>{sub}</header>'''
    off_url = C["courses"][course].get("offline_url") if course else None   # where this course's offline copies are handed out (Google Drive)
    offline = f'<a class="hover:text-accent" href="{e(off_url)}" target="_blank" rel="noopener">Offline lessons (Google Drive)</a>' if off_url else ""
    footer = f'''<footer class="mt-16 border-t border-line" data-nav><div class="wrap flex flex-wrap items-center gap-x-6 gap-y-2 py-8 text-sm text-muted">
<span class="font-display text-base font-semibold text-ink">{e(C["site_name"])}</span>
<span>Free for everyone. No account, no paywall.</span>{offline}</div></footer>'''
    if "site" not in cls.split():
        header = footer = ""
    if not foot:
        footer = ""
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="icon" href="{r}assets/img/favicon.svg">
<link rel="stylesheet" href="{r}assets/css/site.css">
{MOTION_HEAD}{head}</head>
<body class="{cls}"{f' data-course="{course}"' if course else ""}>
{header}
{body}
{footer}
{tail}
{MOTION_TAIL.replace("{r}", r)}
</body>
</html>
'''
    for old, new in FRESH.items():
        page = page.replace(old, new)
    return page


def tile(L, rel, show_level=True):
    r = up(rel)
    chips = [f'<span class="chip">{TYPE.get(L.get("type"), "Lesson")}{" + quiz" if L.get("quiz") or L.get("questions") else ""}</span>']
    if lib.pending(L):
        chips.append('<span class="chip">audio soon</span>')
    sub = L.get("subtitle", "")
    return f'''<a class="tile" data-reveal href="{r}{L["url"]}" data-lesson="{L["id"]}">
<div class="flex items-start justify-between gap-2"><h3 class="text-lg font-semibold leading-snug">{e(L.get("title", L["slug"]))}</h3>
{f'<span class="chip chip-accent">{lv(L.get("level"))}</span>' if show_level else ""}</div>
{f'<p class="mt-1 text-sm text-muted">{e(sub)}</p>' if sub else ""}
<div class="mt-3 flex flex-wrap gap-1.5">{"".join(chips)}</div></a>'''


def grid(items):
    return f'<div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{"".join(items)}</div>'


def soon(text):
    return f'<p class="mt-4 rounded-2xl border-2 border-dashed border-line p-5 text-sm text-muted">{e(text)}</p>'


# ------------------------------------------------------------------ lesson shells
READER = '''<main class="flex min-h-0 flex-1 flex-col" x-data="reader">
<div class="wrap flex shrink-0 items-center gap-2 py-2">
<a class="btn px-3 py-1.5" href="__BACK__" aria-label="Back to the list" data-nav>&larr;</a>
<h1 class="min-w-0 flex-1 truncate text-lg font-semibold sm:text-2xl">__TITLE__</h1>
<span class="chip chip-accent hidden sm:inline-flex">__LEVEL__</span>
<button class="btn px-3 py-1.5" :class="rate < 1 && 'btn-on'" @click="slow()">Slow</button>
<button class="btn px-3 py-1.5" x-show="hasTr" :class="tr && 'btn-on'" @click="tr = !tr" :lang="trLang" x-text="trLabel"></button>
<span class="chip" x-text="(i + 1) + ' / ' + pages.length"></span>
</div>
<div class="wrap flex min-h-0 flex-1 flex-col gap-3 pb-2 md:flex-row md:gap-6">
<div class="shrink-0 md:w-1/2">
<img x-show="!broken[i]" :src="img(page)" :alt="page.alt || ('Picture ' + (i + 1))" @error="broken[i] = true" class="mx-auto max-h-[40dvh] w-auto max-w-full rounded-2xl border border-line bg-card object-contain md:max-h-full">
<div x-show="broken[i]" x-cloak class="ph mx-auto max-h-[40dvh] md:max-h-full">__IMG__<span x-text="page.alt || ('Picture ' + (i + 1) + ' goes here')"></span></div>
</div>
<div class="scrollpane min-h-0 flex-1 space-y-4 pr-3" x-ref="pane">
<template x-for="(s, si) in page.sentences" :key="i + '-' + si"><div>
<p class="text-2xl font-bold leading-snug sm:text-3xl"><template x-for="c in s" :key="c[1]"><button class="chunk mr-1 scroll-my-8" :class="playing === c[1] && 'playing'" @click="say(c[1])" x-text="c[0]"></button></template></p>
<p x-show="tr && page.tr && page.tr[si]" :lang="trLang" class="mt-1 px-1.5 text-lg text-accent" x-text="page.tr ? page.tr[si] : ''"></p>
</div></template>
<p x-show="pending" x-cloak class="text-sm text-muted">The audio for this lesson is not recorded yet.</p>
<div x-show="i === pages.length - 1" x-cloak class="space-y-4 pb-2 pt-4">__END__</div>
</div>
</div>
<div class="shrink-0 border-t border-line bg-paper py-2"><div class="wrap flex items-center justify-center gap-3">
<button class="btn" @click="go(-1)" :disabled="i === 0" :class="i === 0 && 'opacity-40'" aria-label="Previous page">&larr;</button>
<button class="btn btn-primary px-6" :class="pending && 'opacity-40'" :disabled="pending" @click="playPage()">__PLAY__<span x-text="busy ? 'Stop' : 'Play page'"></span></button>
<button class="btn" :disabled="!(playing || busy)" :class="[P.held && 'btn-on', !(playing || busy) && 'opacity-40']" @click="togglePause()" x-text="P.held ? 'Resume' : 'Pause'"></button>
<button class="btn" @click="go(1)" :disabled="i === pages.length - 1" :class="i === pages.length - 1 && 'opacity-40'" aria-label="Next page">&rarr;</button>
</div></div>
</main>'''

LINES = '''<section x-data="lines" class="mt-6">
<div class="flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-card p-3">
<button class="btn btn-primary" @click="playAll()">__PLAY__<span x-text="busy ? 'Stop' : 'Play all'"></span></button>
<button class="btn" :disabled="!(playing || busy)" :class="[P.held && 'btn-on', !(playing || busy) && 'opacity-40']" @click="togglePause()" x-text="P.held ? 'Resume' : 'Pause'"></button>
<button class="btn" :class="rate < 1 && 'btn-on'" @click="slow()">Slow</button>
<button class="btn" :class="hide && 'btn-on'" @click="hide = !hide; shown = {}">Hide text</button>
<span class="mx-1 hidden h-6 w-px bg-line sm:block"></span>
<template x-for="k in langs" :key="k"><button class="btn" :class="trLang === k && 'btn-on'" @click="trLang = trLang === k ? '' : k" :lang="k" x-text="names[k] || k"></button></template>
<template x-if="hasScript"><span class="flex items-center gap-2"><span class="mx-1 hidden h-6 w-px bg-line sm:block"></span>
<button class="btn" :class="script === 'romaji' && 'btn-on'" @click="script = 'romaji'">__ROMAN__</button>
<button class="btn" :class="script === 'kana' && 'btn-on'" @click="script = 'kana'">__NATIVE__</button>
<button class="btn" :class="script === 'both' && 'btn-on'" @click="script = 'both'">Both</button></span></template>
</div>
<div x-show="roles.length > 1" class="mt-3 flex flex-wrap items-center gap-2 text-sm">
<span class="font-bold text-muted">Role play: I am</span>
<template x-for="(k, i) in roles" :key="k"><button class="btn py-1.5" :class="role === k && 'btn-on'" @click="role = role === k ? '' : k; shown = {}"><span class="h-3 w-3 rounded-full border" :class="'dot-' + (i % 4)"></span><span x-text="speakers[k]"></span></button></template>
<span x-show="role" class="text-muted">Press Play all. Say your lines in the pauses.</span>
</div>
<template x-for="(sec, si) in sections" :key="si"><div class="mt-6">
<h2 x-show="sec.title" class="text-2xl font-semibold" x-text="sec.title"></h2>
<p x-show="sec.desc" class="mt-1 text-muted" x-text="sec.desc"></p>
<ol class="mt-3 space-y-3">
<template x-for="l in sec.lines" :key="l.n"><li class="rounded-2xl border-l-4 p-3 sm:p-4" :class="[tone(l), playing === l.n && 'ring-2 ring-accent/60']">
<template x-if="!pending"><audio controls preload="metadata" class="h-10 w-full max-w-sm" :data-clip="l.n" :src="clip(l.n)"></audio></template>
<div x-show="pending" x-cloak class="inline-flex h-10 items-center gap-3 rounded-full bg-white/70 px-4 text-sm text-muted">__PLAY__<span class="tabular-nums">0:00</span><span>audio not recorded yet</span></div>
<template x-if="!veiled(l)"><div class="mt-2">
<p class="text-lg leading-relaxed" lang="__LANG__"><span x-text="main(l)"></span>
<button x-show="hasTr(l)" class="ml-1 inline-flex h-7 w-7 items-center justify-center rounded-md align-middle text-ink/70 hover:bg-white/70 hover:text-accent" :class="trOpen[l.n] && 'bg-white/80 text-accent'" @click="trOpen[l.n] = !trOpen[l.n]" aria-label="Translation" title="Translation">__TR__</button></p>
<p x-show="sub(l)" class="text-base" lang="__SLANG__" x-text="sub(l)"></p>
<template x-for="k in langs" :key="k"><p x-show="(trLang === k || trOpen[l.n]) && l.tr && l.tr[k]" :lang="k" class="mt-1 text-base text-ink/70" x-text="l.tr ? l.tr[k] : ''"></p></template>
<p x-show="l.note" class="mt-1 text-sm italic text-ink/60" x-text="l.note"></p>
</div></template>
<template x-if="veiled(l)"><button class="mt-2 block text-left text-base text-ink/60 underline decoration-dotted" @click="shown[l.n] = true" x-text="role === l.who ? 'Your turn. Tap to see the line.' : 'Tap to show the text'"></button></template>
</li></template>
</ol></div></template>
<p x-show="pending" x-cloak class="mt-4 text-sm text-muted">The audio for this lesson is not recorded yet.</p>
</section>'''

TEXT = '''<section x-data="text" class="mt-6">
<div class="sticky top-14 z-20 flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-card/95 p-2 shadow-sm backdrop-blur sm:top-28">
<button x-show="!hasFile" class="btn btn-primary" :disabled="pending" :class="pending && 'opacity-40'" @click="playAll()">__PLAY__<span x-text="busy ? 'Stop' : 'Play all'"></span></button>
<button x-show="!hasFile" class="btn" :disabled="!(playing || busy)" :class="[P.held && 'btn-on', !(playing || busy) && 'opacity-40']" @click="togglePause()" x-text="P.held ? 'Resume' : 'Pause'"></button>
<template x-if="hasFile"><div class="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-1">
<button class="play" :class="on && 'playing'" @click="filePlay()" aria-label="Play" title="Play">__PLAY__</button>
<button class="play" @click="filePause()" aria-label="Pause" title="Pause"><svg viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true"><path d="M7 5h4v14H7zM13 5h4v14h-4z" fill="currentColor"/></svg></button>
<button class="play" @click="fileStop()" aria-label="Stop" title="Stop"><svg viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true"><path d="M7 7h10v10H7z" fill="currentColor"/></svg></button>
<input type="range" class="seek min-w-[8rem] flex-1" min="0" :max="dur || 1" step="0.1" :value="pos" @input="seek($event.target.value)" aria-label="Position in the recording">
<span class="w-24 text-right text-sm tabular-nums text-muted" x-text="clock(pos) + ' / ' + clock(dur)"></span>
</div></template>
<button class="btn" :class="rate < 1 && 'btn-on'" @click="slow()">Slow</button>
<template x-for="k in langs" :key="k"><button class="btn" :class="trLang === k && 'btn-on'" @click="trLang = trLang === k ? '' : k" :lang="k" x-text="names[k] || k"></button></template>
</div>
<div class="mt-6 grid items-start gap-8 md:grid-cols-5">
<div class="space-y-6 md:col-span-3">
<template x-for="(p, pi) in paras" :key="pi"><div>
<p class="text-xl leading-loose sm:text-2xl sm:leading-loose" lang="__LANG__"><template x-for="s in p" :key="s.n"><span class="cursor-pointer rounded-lg px-0.5 py-1 transition hover:bg-accent/10" :class="playing === s.n && 'bg-accent/20'" @click="say(s.n)"><template x-for="(part, k) in s.parts" :key="k"><span><template x-if="part.g"><button class="gloss" :class="word && word.t === part.t && 'text-accent'" @click.stop="pick(part)" x-text="part.t"></button></template><template x-if="!part.g"><span x-text="part.t"></span></template></span></template><span> </span></span></template></p>
<p x-show="trLang" x-cloak :lang="trLang" class="mt-2 border-l-4 border-accent/30 pl-3 text-muted" x-text="line(p)"></p>
</div></template>
<p x-show="pending" x-cloak class="text-sm text-muted">The audio for this lesson is not recorded yet.</p>
</div>
<aside class="space-y-4 md:sticky md:top-48 md:col-span-2">
<img x-show="hero && !broken" :src="hero" alt="__ALT__" @error="broken = true" class="w-full rounded-2xl border border-line bg-card">
<div x-show="!hero || broken" x-cloak class="ph">__IMG__<span>__ALT__</span></div>
<p x-show="!word" class="hidden rounded-2xl border-2 border-dashed border-line p-4 text-sm text-muted md:block">Tap an underlined word to see how it is said and what it means.</p>
<div x-show="word" x-cloak class="fixed inset-x-3 bottom-3 z-30 rounded-2xl border border-accent bg-card p-4 shadow-lg md:static md:shadow-none">
<div class="flex items-start gap-3">
<button x-show="word && word.audio" class="play small" @click="hear(word.audio)" aria-label="Hear the word">__PLAY__</button>
<div class="min-w-0 flex-1">
<p class="font-display text-2xl font-semibold text-accent" lang="__LANG__" x-text="word ? word.t : ''"></p>
<p class="text-muted" x-text="word ? word.ipa : ''"></p>
<p class="mt-1 text-lg font-bold" x-text="word ? word.en : ''"></p>
<p x-show="word && word.base" class="text-sm text-muted">from <span class="font-bold" lang="__LANG__" x-text="word ? word.base : ''"></span></p>
</div><button class="btn px-3 py-1.5 md:hidden" @click="word = null" aria-label="Close">&times;</button></div>
</div>
</aside>
</div>
<section x-show="glossary.length" class="mt-10 rounded-2xl border border-line bg-card p-5">
<h2 class="text-xl font-semibold">Glossary <span class="font-body text-base font-normal text-muted">tap a word to hear it</span></h2>
<div class="mt-4 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
<template x-for="g in glossary" :key="g.word"><button class="flex items-center gap-3 border-b border-line py-2 text-left hover:text-accent" @click="hear(g.audio || g.word)">
<span class="play small pointer-events-none">__PLAY__</span><span class="font-bold" lang="__LANG__" x-text="g.word"></span><span class="ml-auto text-muted" x-text="g.en"></span></button></template>
</div></section>
<details x-show="!glossary.length" class="mt-10 rounded-2xl border border-line bg-card p-5">
<summary class="cursor-pointer font-display text-xl font-semibold">Word list <span class="text-base font-normal text-muted" x-text="'(' + words.length + ')'"></span></summary>
<dl class="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">
<template x-for="w in words" :key="w.t"><div class="flex flex-wrap items-baseline gap-x-2 border-b border-line py-1.5"><dt class="font-bold" lang="__LANG__" x-text="w.base ? w.base.split(' /')[0] : w.t"></dt><dd class="text-sm text-muted" x-text="w.base ? '/' + (w.base.split(' /')[1] || '') : w.ipa"></dd><dd class="ml-auto" x-text="w.en"></dd></div></template>
</dl></details>
</section>'''

PRACTICE = '''<section x-data="practice" class="mt-6 space-y-8">
<template x-for="(b, bi) in blocks" :key="bi"><div class="rounded-2xl border border-line bg-card p-5 sm:p-6">
<h2 x-show="b.title" class="text-2xl font-semibold" x-text="b.title"></h2>
<p x-show="b.intro" class="mt-1 text-muted" x-text="b.intro"></p>
<template x-if="b.audio && (b.kind !== 'open' || b.shown)"><div class="mt-4 space-y-2">
<template x-for="(a, k) in tracks(b)" :key="k"><div class="flex flex-wrap items-center gap-3"><span x-show="a.label" class="chip" x-text="a.label"></span><audio controls preload="none" class="min-w-0 flex-1" :src="url(a.src)"></audio></div></template>
</div></template>
<details x-show="b.transcript" class="mt-3 rounded-xl border border-line p-3"><summary class="cursor-pointer font-bold">Transcript</summary><p class="mt-2 whitespace-pre-line text-lg" lang="__LANG__" x-text="b.transcript"></p></details>

<template x-if="b.kind === 'picture'"><div class="mt-4" x-data="{ left: null, t: null }">
<div class="relative"><img :src="pic(b.src)" :alt="b.alt || ''" class="w-full rounded-2xl border border-line bg-card" :class="left === 0 && 'invisible'">
<p x-show="left === 0" x-cloak class="ph absolute inset-0">Time is up. Answer the questions below without looking.</p></div>
<div class="mt-3 flex flex-wrap items-center gap-3">
<button class="btn btn-primary" x-show="left === null" @click="left = b.seconds || 30; t = setInterval(() => { if (--left <= 0) { left = 0; clearInterval(t); } }, 1000)" x-text="'Start: ' + (b.seconds || 30) + ' seconds'"></button>
<span x-show="left > 0" x-cloak class="font-display text-3xl font-semibold text-accent" x-text="left"></span>
<button class="btn" x-show="left !== null" x-cloak @click="clearInterval(t); left = null">Show the picture again</button>
</div></div></template>

<template x-if="b.kind === 'video'"><div>
<video x-show="!offline" controls preload="metadata" playsinline class="mt-4 w-full rounded-2xl bg-ink" :src="url(b.src)"></video>
<p x-show="offline" x-cloak class="ph mt-4">The video is not included in the offline copy. It needs an internet connection.</p>
<p x-show="b.caption" class="mt-3 text-center text-muted" x-text="b.caption"></p>
</div></template>

<template x-if="b.kind === 'slides'"><div class="mt-2" x-data="{ k: 0 }" @keydown.left.window="!$event.target.matches('input, textarea') && (k = Math.max(0, k - 1))" @keydown.right.window="!$event.target.matches('input, textarea') && (k = Math.min(b.items.length - 1, k + 1))">
<img :src="pic(b.items[k])" :alt="'Slide ' + (k + 1)" class="w-full rounded-2xl border border-line bg-card">
<div class="mt-3 flex items-center justify-center gap-3">
<button class="btn" :disabled="k === 0" :class="k === 0 && 'opacity-40'" @click="k--" aria-label="Previous slide">&larr;</button>
<span class="chip" x-text="(k + 1) + ' / ' + b.items.length"></span>
<button class="btn" :disabled="k === b.items.length - 1" :class="k === b.items.length - 1 && 'opacity-40'" @click="k++" aria-label="Next slide">&rarr;</button>
</div></div></template>

<template x-if="b.kind === 'truefalse'"><ol class="mt-4 space-y-3">
<template x-for="(it, i) in b.items" :key="i"><li class="item flex flex-wrap items-center gap-3 rounded-xl border border-line p-3" :class="mark(b, i)">
<span class="min-w-0 flex-1 text-lg" lang="__LANG__" x-text="(i + 1) + '. ' + it.q"></span>
<span class="flex gap-2"><button class="btn px-4 py-1.5" :class="b.ans[i] === true && 'btn-on'" @click="set(b, i, true)">Vrai</button>
<button class="btn px-4 py-1.5" :class="b.ans[i] === false && 'btn-on'" @click="set(b, i, false)">Faux</button></span>
</li></template></ol></template>

<template x-if="b.kind === 'listen'"><ol class="mt-4 space-y-5">
<template x-for="(it, i) in b.items" :key="i"><li class="item rounded-xl border border-line p-3" :class="mark(b, i)">
<div class="flex items-center gap-3"><button class="play small" :class="[pending && 'pending', heard === it.n && 'playing']" :disabled="pending" @click="hear(it.n)" aria-label="Play the line">__PLAY__</button>
<p class="text-lg font-bold" lang="__LANG__" x-text="(i + 1) + '. ' + it.q"></p></div>
<div class="mt-2 flex flex-wrap gap-2"><template x-for="(o, k) in it.options" :key="k"><button class="btn text-base" lang="__LANG__" :class="b.ans[i] === k && 'btn-on'" @click="set(b, i, k)" x-text="o"></button></template></div>
<p x-show="b.checked && it.why" x-cloak class="mt-2 text-muted" x-text="it.why"></p>
</li></template></ol></template>

<template x-if="b.kind === 'choice'"><ol class="mt-4 space-y-5">
<template x-for="(it, i) in b.items" :key="i"><li class="item rounded-xl border border-line p-3" :class="mark(b, i)">
<p class="text-lg font-bold" lang="__LANG__" x-text="(i + 1) + '. ' + it.q"></p>
<div class="mt-2 flex flex-wrap gap-2"><template x-for="(o, k) in it.options" :key="k"><button class="btn text-base" lang="__LANG__" :class="b.ans[i] === k && 'btn-on'" @click="set(b, i, k)" x-text="o"></button></template></div>
<p x-show="b.checked && it.why" x-cloak class="mt-2 text-muted" x-text="it.why"></p>
</li></template></ol></template>

<template x-if="b.kind === 'cloze'"><ol class="mt-4 space-y-3">
<template x-for="(it, i) in b.items" :key="i"><li class="item rounded-xl border border-line p-3" :class="mark(b, i)">
<p class="text-lg leading-loose" lang="__LANG__"><button x-show="it.n" class="play small mr-2 align-middle" :class="heard === it.n && 'playing'" @click="hear(it.n)" aria-label="Listen">__PLAY__</button><span x-text="(i + 1) + '. ' + (it.before || '')"></span>
<input type="text" class="blank" autocomplete="off" autocapitalize="off" spellcheck="false" :size="Math.max(7, it.answer.length + 2)" :value="b.ans[i] || ''" @input="set(b, i, $event.target.value)" :aria-label="'Blank ' + (i + 1)"><span x-text="it.after || ''"></span></p>
<p x-show="it.tr" class="text-muted" x-text="it.tr"></p>
</li></template></ol></template>

<template x-if="b.kind === 'open'"><ol class="mt-4 space-y-5">
<template x-for="(it, i) in b.items" :key="i"><li>
<p class="text-lg font-bold" lang="__LANG__" x-text="(i + 1) + '. ' + it.q"></p>
<textarea rows="3" class="mt-2 w-full rounded-xl border border-line bg-paper p-3 text-lg" lang="__LANG__" :aria-label="'Answer ' + (i + 1)"></textarea>
<p x-show="b.shown" x-cloak class="mt-2 rounded-xl bg-accent/10 p-3" lang="__LANG__"><span class="font-bold">Model answer: </span><span x-text="it.model"></span></p>
</li></template></ol></template>

<template x-if="b.kind === 'order'"><ol class="mt-4 space-y-2">
<template x-for="(it, i) in b.ans" :key="it.k"><li class="item flex items-center gap-3 rounded-xl border border-line p-2 pl-3" :class="mark(b, i)">
<span class="font-display text-xl font-semibold text-accent" x-text="i + 1"></span>
<span class="min-w-0 flex-1 text-lg" lang="__LANG__" x-text="it.text"></span>
<button class="btn px-3 py-1.5" :disabled="i === 0" :class="i === 0 && 'opacity-30'" @click="move(b, i, -1)" aria-label="Move up">&uarr;</button>
<button class="btn px-3 py-1.5" :disabled="i === b.ans.length - 1" :class="i === b.ans.length - 1 && 'opacity-30'" @click="move(b, i, 1)" aria-label="Move down">&darr;</button>
</li></template></ol></template>

<p x-show="b.note" class="mt-4 text-sm text-muted" x-text="b.note"></p>
<div x-show="!['video', 'slides', 'picture'].includes(b.kind)" class="mt-5 flex flex-wrap items-center gap-2">
<button x-show="b.kind !== 'open'" class="btn btn-primary" @click="check(b)">Check</button>
<button class="btn" @click="reveal(b)">Show answers</button>
<button class="btn" @click="reset(b)">Reset</button>
<span x-show="b.checked && b.kind !== 'open'" x-cloak class="ml-2 text-lg font-bold" :class="score(b) === total(b) ? 'text-good' : 'text-bad'" x-text="score(b) + ' / ' + total(b)"></span>
</div>
</div></template>
</section>'''

SHADOW = '''<section x-data="shadow" class="mt-6">
<div class="rounded-2xl border border-line bg-card p-4">
<p class="text-sm font-bold uppercase tracking-wide text-muted">Three passes</p>
<div class="mt-2 flex flex-wrap gap-2">
<button class="btn" :class="mode === 1 && 'btn-on'" @click="mode = 1">1 &middot; Listen and read</button>
<button class="btn" :class="mode === 2 && 'btn-on'" @click="mode = 2">2 &middot; Shadow with the text</button>
<button class="btn" :class="mode === 3 && 'btn-on'" @click="mode = 3">3 &middot; Shadow without the text</button>
</div>
<p class="mt-3 text-muted" x-show="mode === 1">Play it through. Follow the words with your eyes.</p>
<p class="mt-3 text-muted" x-show="mode === 2" x-cloak>Speak along with the voice, a split second behind it. Copy the rhythm before the words.</p>
<p class="mt-3 text-muted" x-show="mode === 3" x-cloak>Same again, from your ear only. Loop any chunk that trips you.</p>
<div class="mt-4 flex flex-wrap gap-2">
<button class="btn btn-primary" :disabled="pending" :class="pending && 'opacity-40'" @click="playAll()">__PLAY__<span x-text="busy && !loop ? 'Stop' : 'Play through'"></span></button>
<button class="btn" :disabled="pending" :class="pending && 'opacity-40'" @click="echo()">Listen, then repeat</button>
<button class="btn" :disabled="!(playing || busy)" :class="[P.held && 'btn-on', !(playing || busy) && 'opacity-40']" @click="togglePause()" x-text="P.held ? 'Resume' : 'Pause'"></button>
<button class="btn" :class="rate < 1 && 'btn-on'" @click="slow()">Slow</button>
</div></div>
<ol class="mt-5 space-y-3">
<template x-for="c in chunks" :key="c.n"><li class="flex items-center gap-3 rounded-2xl border bg-card p-3 sm:p-4" :class="playing === c.n ? 'border-accent shadow-md' : 'border-line'">
<button class="play small" :class="[pending && 'pending', playing === c.n && 'playing']" :disabled="pending" @click="loop = 0; say(c.n)" aria-label="Play">__PLAY__</button>
<div class="min-w-0 flex-1">
<p class="text-xl font-bold leading-snug" lang="__LANG__" x-show="!noText" x-text="c.text"></p>
<p class="text-xl text-muted" x-show="noText" x-cloak>&bull; &bull; &bull;</p>
<p class="mt-0.5 text-muted" x-show="c.tr && !noText" x-text="c.tr"></p>
</div>
<button class="btn px-3" :class="loop === c.n && 'btn-on'" :disabled="pending" @click="repeat(c)" aria-label="Loop this chunk" title="Loop this chunk">__LOOP__</button>
</li></template>
</ol>
<p x-show="pending" x-cloak class="mt-4 text-sm text-muted">The audio for this lesson is not recorded yet.</p>
</section>'''

QUIZ = '''<section x-data="quiz" x-show="qs.length" class="mt-12 rounded-2xl border border-line bg-card p-5 sm:p-6">
<h2 class="text-2xl font-semibold">Check what stuck</h2>
<div x-show="!over" class="mt-4">
<p class="chip" x-text="'Question ' + (i + 1) + ' of ' + qs.length"></p>
<p class="mt-3 text-xl font-bold" x-text="q.q"></p>
<div class="mt-4 grid gap-2">
<template x-for="(o, k) in q.options" :key="i + '-' + k"><button class="btn justify-start text-left text-base" :class="pick !== null && k === q.answer ? '!border-good !bg-good/10 !text-good' : (pick === k ? '!border-bad !bg-bad/10 !text-bad' : '')" @click="choose(k)" x-text="o"></button></template>
</div>
<p x-show="pick !== null && q.why" class="mt-4 rounded-xl bg-paper p-3 text-muted" x-text="q.why"></p>
<button x-show="pick !== null" class="btn btn-primary mt-4" @click="next()" x-text="i + 1 >= qs.length ? 'See my score' : 'Next question'"></button>
</div>
<div x-show="over" x-cloak class="mt-4">
<p class="font-display text-4xl font-semibold text-accent" x-text="score + ' / ' + qs.length"></p>
<button class="btn mt-4" @click="again()">Try again</button>
</div></section>'''

CARDS_BLOBS = '''<div class="pointer-events-none fixed left-0 top-0 z-0 h-full w-full overflow-hidden">
<div class="absolute left-[-80px] top-[-80px] h-96 w-96 rounded-full" style="background:radial-gradient(circle,rgba(26,110,245,.18) 0%,transparent 70%)"></div>
<div class="absolute bottom-[-60px] right-[-60px] h-80 w-80 rounded-full" style="background:radial-gradient(circle,rgba(0,200,255,.14) 0%,transparent 70%)"></div>
<div class="absolute right-1/4 top-1/2 h-64 w-64 rounded-full" style="background:radial-gradient(circle,rgba(26,110,245,.08) 0%,transparent 70%)"></div></div>'''


UI = {"fr": {"LISTEN": "&Eacute;coutez et choisissez.", "BRAVO": "Bravo !", "FIND": "Trouvez&nbsp;:", "FIRST": "du premier coup"},
      "en": {"LISTEN": "Listen and choose.", "BRAVO": "Well done!", "FIND": "Find:", "FIRST": "on the first try"}}
# Courses taught through romanization: the two script buttons of a dialogue, and the language tag of the native line.
SCRIPT = {"ja": ("Romaji", "かな", "ja"), "ko": ("Romanized", "한글", "ko")}

# A themed word list: tap a word to hear it; hide one language to test yourself.
WORDS = """<section x-data="words" class="mt-6">
<img x-show="hero" x-cloak :src="hero" :alt="alt" class="wl-hero">
<div class="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-card p-2">
<button class="btn" x-show="!quiz" :class="hideEn && 'btn-on'" @click="hideEn = !hideEn" x-text="hideEn ? 'Show English' : 'Hide English'"></button>
<button class="btn" x-show="!quiz" :class="hideFr && 'btn-on'" @click="hideFr = !hideFr" x-text="hideFr ? 'Show the words' : 'Hide the words'"></button>
<button class="btn" x-show="pool().length > 3" :class="quiz && 'btn-on'" @click="quiz ? stopQuiz() : startQuiz()" x-text="quiz ? 'Back to the list' : 'Quiz'"></button>
<span class="text-sm text-muted" x-show="!quiz">Tap a word to hear it.</span>
</div>

<div x-show="quiz" x-cloak class="mt-4 rounded-2xl border border-line bg-card p-4">
<div x-show="q">
<div class="flex flex-wrap items-center gap-3">
<button class="play" @click="q && hear(q.w)" aria-label="Hear it again">__PLAY__</button>
<p class="text-xl text-muted">__UI_LISTEN__</p>
<span class="ml-auto text-sm font-bold text-muted" x-text="asked + ' / ' + total"></span>
</div>
<div class="wl-opts mt-4"><template x-for="o in (q ? q.opts : [])" :key="o.n"><button class="btn" :class="optClass(o)" @click="choose(o)" x-text="label(o)" :lang="show === 'fr' ? '__LANG__' : null"></button></template></div>
</div>
<div x-show="!q" class="flex flex-wrap items-center gap-3">
<p class="text-xl font-semibold" x-text="'__UI_BRAVO__ ' + score + ' / ' + total"></p><span class="ml-auto"></span>
<button class="btn btn-primary" @click="startQuiz()">Again</button><button class="btn" @click="stopQuiz()">Back to the list</button>
</div>
</div>

<div x-show="!quiz">
<template x-for="(g, gi) in groups" :key="gi"><section class="mt-8">
<div class="flex flex-wrap items-center gap-3" x-show="g.title">
<button x-show="g.audio" class="play small" @click="hearName(g.audio)" aria-label="Hear the heading">__PLAY__</button>
<h2 class="text-2xl font-semibold" lang="__LANG__" x-text="g.title"></h2><span class="wl-ipa" x-show="g.ipa" x-text="g.ipa"></span>
</div>
<p class="mt-1 text-muted" x-show="g.sub" x-text="g.sub"></p>
<template x-for="(t, ti) in (g.notes || [])" :key="ti"><p class="wl-note" x-text="t"></p></template>
<div class="wl-grid mt-3">
<template x-for="w in g.words" :key="w.n"><button class="wl-row" :class="said === w.n && 'wl-on'" @click="hear(w)">
<span class="play small pointer-events-none">__PLAY__</span>
<span class="wl-fr"><span class="font-bold" lang="__LANG__" x-show="!hideFr" x-text="w.fr"></span><span x-show="hideFr" x-cloak class="text-muted">&bull; &bull; &bull;</span>
<span x-show="w.g" class="wl-g" x-text="w.g"></span><span class="wl-ipa" x-show="w.ipa && !hideFr" x-text="w.ipa"></span></span>
<span class="wl-en" x-show="w.en && !hideEn" x-text="w.en"></span><span x-show="w.en && hideEn" x-cloak class="wl-en">&bull; &bull; &bull;</span>
</button></template>
</div></section></template>
</div>
</section>"""

# Pictures with dots. Explore: tap a dot to see and hear the word. Quiz: a word is asked, tap where it is.
HOTSPOTS = """<section x-data="hotspots" class="mt-6">
<div class="flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-card p-2">
<button class="btn" :class="mode === 'explore' && 'btn-on'" @click="setMode('explore')">Explore</button>
<button class="btn" :class="mode === 'quiz' && 'btn-on'" @click="setMode('quiz')">Quiz</button>
<span class="ml-auto"></span>
<button class="btn px-3" :disabled="i === 0" :class="i === 0 && 'opacity-40'" @click="go(i - 1)" aria-label="Previous picture">&larr;</button>
<span class="text-sm font-bold text-muted" x-text="(i + 1) + ' / ' + slides.length"></span>
<button class="btn px-3" :disabled="i === slides.length - 1" :class="i === slides.length - 1 && 'opacity-40'" @click="go(i + 1)" aria-label="Next picture">&rarr;</button>
</div>
<div class="hs-thumbs mt-3"><template x-for="(s, k) in slides" :key="k"><button class="hs-thumb" :class="k === i && 'hs-thumb-on'" @click="go(k)" :aria-label="'Picture ' + (k + 1)"><img :src="src(s.img)" alt=""></button></template></div>

<div x-show="mode === 'quiz'" x-cloak class="mt-4 rounded-2xl border border-line bg-card p-4" style="min-height:4.75rem">
<div x-show="target" class="flex flex-wrap items-center gap-3">
<button class="play small" @click="hear(target)" aria-label="Hear the word">__PLAY__</button>
<p class="text-xl"><span class="text-muted">__UI_FIND__</span> <b lang="__LANG__" x-show="!listen" x-text="target && target.fr"></b><span x-show="listen" x-cloak class="text-muted">&bull; &bull; &bull;</span></p>
<span class="ml-auto text-sm font-bold text-muted" x-text="done.length + ' / ' + slide.spots.length"></span>
<button class="btn py-1.5" :class="listen && 'btn-on'" @click="listen = !listen">Listen only</button>
</div>
<div x-show="!target" x-cloak class="flex flex-wrap items-center gap-3">
<p class="text-xl font-semibold" x-text="'__UI_BRAVO__ ' + first + ' / ' + slide.spots.length + ' __UI_FIRST__'"></p>
<span class="ml-auto"></span>
<button class="btn" @click="startQuiz()">Again</button>
<button class="btn btn-primary" x-show="i < slides.length - 1" @click="go(i + 1)">Next picture &rarr;</button>
</div>
<p x-show="last" x-cloak class="mt-2 text-sm text-muted"><span class="font-bold text-good">&#10003;</span> <b lang="__LANG__" x-text="last && last.fr"></b> <span x-text="last && last.en ? ' = ' + last.en : ''"></span></p>
</div>

<div class="hs-stage mt-4"><img :src="src(slide.img)" :alt="slide.alt || ''">
<template x-for="(p, k) in slide.spots" :key="i + '-' + k"><button class="hs-dot" :class="dotClass(k)" :style="'left:' + p.x + '%;top:' + p.y + '%'" @click="tap(k)" :aria-label="mode === 'quiz' ? 'Dot ' + (k + 1) : p.fr"></button></template>
</div>

<div x-show="mode === 'explore'" class="mt-4 rounded-2xl border border-line bg-card p-4" style="min-height:4.75rem">
<div x-show="pick" x-cloak class="flex flex-wrap items-center gap-3">
<button class="play small" @click="hear(pick)" aria-label="Hear the word">__PLAY__</button>
<p class="text-2xl font-bold" lang="__LANG__" x-text="pick && pick.fr"></p><span x-show="pick && pick.g" class="wl-g" x-text="pick && pick.g"></span><span class="text-muted" x-text="pick && pick.ipa"></span>
<span class="ml-auto text-xl text-muted" x-text="pick && pick.en"></span>
</div>
<p x-show="!pick" class="text-muted">Tap a dot on the picture to see and hear the word.</p>
</div>
</section>"""

# The few styles those two pages need beyond the site's own (kept here so the compiled site.css does not have to be rebuilt).
PICTURE_CSS = """<style>
.wl-hero{display:block;width:100%;max-height:24rem;object-fit:contain;border:1px solid #E4DCCF;border-radius:1rem;background:#fff}
.wl-grid{display:grid;gap:.5rem;grid-template-columns:repeat(auto-fill,minmax(min(100%,22rem),1fr))}
.wl-row{display:flex;align-items:center;gap:.75rem;text-align:left;border:1px solid #E4DCCF;background:#fff;border-radius:1rem;padding:.6rem .8rem;transition:border-color .15s}
.wl-row:hover,.wl-on{border-color:rgb(var(--accent))}
.wl-fr{flex:1;min-width:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .5rem;font-size:1.15rem}
.wl-g{font-size:.7rem;font-weight:700;text-transform:uppercase;line-height:1.5;color:rgb(var(--accent));border:1px solid rgb(var(--accent)/.3);background:rgb(var(--accent)/.1);border-radius:999px;padding:0 .45rem}
.wl-ipa{font-size:.9rem;color:#5B6475}
.wl-en{color:#5B6475;text-align:right;max-width:45%}
.wl-note{margin-top:.6rem;border-left:3px solid rgb(var(--accent)/.5);background:rgb(var(--accent)/.06);border-radius:.5rem;padding:.5rem .75rem;font-size:.95rem}
.wl-opts{display:grid;gap:.6rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr))}
.wl-opts .btn{min-height:3.25rem;font-size:1rem;white-space:normal}
.wl-wrong{border-color:#B3261E;color:#B3261E}
.hs-stage{position:relative;border-radius:1rem;overflow:hidden;border:1px solid #E4DCCF;background:#fff;line-height:0}
.hs-stage img{width:100%;height:auto;display:block}
.hs-dot{position:absolute;width:2.25rem;height:2.25rem;margin:-1.125rem 0 0 -1.125rem;padding:0;border:0;border-radius:999px;background:rgb(255 255 255/.6);cursor:pointer;display:grid;place-items:center;transition:transform .15s,background .15s}
.hs-dot::after{content:"";width:.7rem;height:.7rem;border-radius:999px;background:#D7372C;box-shadow:0 0 0 2px #fff}
.hs-dot:hover{transform:scale(1.15)}
.hs-on{background:rgb(var(--accent)/.4)}.hs-on::after{background:rgb(var(--accent))}
.hs-good{background:rgb(27 117 80/.4)}.hs-good::after{background:#1B7550}
.hs-bad{background:rgb(179 38 30/.5);animation:hs-shake .3s}
@keyframes hs-shake{25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.hs-thumbs{display:flex;gap:.5rem;overflow-x:auto;padding-bottom:.25rem}
.hs-thumb{flex:none;width:5.5rem;padding:0;border:2px solid #E4DCCF;border-radius:.6rem;overflow:hidden;background:#fff;line-height:0;cursor:pointer}
.hs-thumb img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.hs-thumb-on{border-color:rgb(var(--accent))}
@media (max-width:480px){.hs-dot{width:1.75rem;height:1.75rem;margin:-.875rem 0 0 -.875rem}.wl-en{max-width:40%}}
@media (prefers-reduced-motion:reduce){.hs-bad{animation:none}.hs-dot,.wl-row{transition:none}}
</style>
"""


# ------------------------------------------------------------------ grammar notes and the tense timeline
def inline(s):
    """The light markup of the lesson files -> HTML: **the form to notice**, *italic*, `code`, line breaks."""
    s = e(str(s), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r'<b class="font-bold text-accent">\1</b>', s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r'<code class="rounded bg-accent/10 px-1 font-bold">\1</code>', s)
    return s.replace("\n", "<br>")


EDGES = ["border-l-amber-400", "border-l-sky-400", "border-l-rose-400", "border-l-emerald-400", "border-l-violet-400"]


def grammar_block(b, lang, edge=""):
    out = f'<div class="rounded-2xl border border-line bg-card p-5{" border-l-4 " + edge if edge else ""}">'
    if b.get("label") or b.get("title"):
        out += '<div class="flex flex-wrap items-center gap-2">'
        if b.get("label"):
            out += f'<span class="chip chip-accent">{inline(b["label"])}</span>'
        if b.get("title"):
            out += f'<h3 class="text-lg font-semibold leading-snug">{inline(b["title"])}</h3>'
        out += "</div>"
    if b.get("formula"):
        out += f'<p class="mt-3 rounded-xl bg-accent/5 px-4 py-3 text-lg font-bold leading-relaxed" lang="{lang}">{inline(b["formula"])}</p>'
    if b.get("text"):
        out += f'<p class="mt-3 text-lg">{inline(b["text"])}</p>'
    if b.get("points"):
        out += '<ul class="mt-3 list-disc space-y-1.5 pl-5">' + "".join(f"<li>{inline(x)}</li>" for x in b["points"]) + "</ul>"
    if b.get("examples"):
        out += '<ul class="mt-3 space-y-2.5">' + "".join(
            f'<li><p class="text-lg leading-snug" lang="{lang}">{inline(x["fr"])}</p>' + (f'<p class="text-muted">{inline(x["en"])}</p>' if x.get("en") else "") + "</li>"
            for x in b["examples"]) + "</ul>"
    if b.get("table"):
        cell = "border-b border-line py-2 pr-4 align-top"
        out += '<div class="mt-3 overflow-x-auto"><table class="w-full text-left">'
        if b["table"].get("head"):
            out += "<thead><tr>" + "".join(f'<th class="{cell} text-sm uppercase tracking-wide text-muted">{inline(h)}</th>' for h in b["table"]["head"]) + "</tr></thead>"
        out += "<tbody>" + "".join("<tr>" + "".join(f'<td class="{cell}{" font-bold" if k == 0 else ""}">{inline(c)}</td>' for k, c in enumerate(row)) + "</tr>" for row in b["table"]["rows"]) + "</tbody></table></div>"
    if b.get("note"):
        out += f'<p class="mt-3 rounded-r-xl border-l-4 border-accent/50 bg-accent/5 px-4 py-2 text-sm">{inline(b["note"])}</p>'
    return out + "</div>"


def grammar_shell(L, lang):
    """A grammar lesson: "sections", each a list of "blocks" (label, title, formula, text, points, examples, table, note)."""
    secs = L.get("sections", [])
    out = '<nav class="mt-6 flex flex-wrap gap-2" aria-label="On this page" data-nav>' + "".join(
        f'<a class="btn py-1.5 text-sm" href="#s{i}">{inline(s.get("title", ""))}</a>' for i, s in enumerate(secs, 1) if s.get("title")) + "</nav>"
    for i, s in enumerate(secs, 1):
        blocks = s.get("blocks", [])
        wide = len(blocks) > 1
        cards = "".join(grammar_block(b, lang, EDGES[k % len(EDGES)] if i == 1 else "") for k, b in enumerate(blocks))
        out += f'<section id="s{i}" class="mt-10 scroll-mt-28"><h2 class="text-2xl font-semibold">{inline(s.get("title", ""))}</h2><div class="mt-4 grid gap-4{" lg:grid-cols-2" if wide else ""}">{cards}</div></section>'
    return out


TIMELINE = """<section x-data="timeline" class="mt-6" @keydown.left.window="$event.target.tagName !== 'INPUT' && go(-1)" @keydown.right.window="$event.target.tagName !== 'INPUT' && go(1)">
<div class="rounded-2xl border border-line bg-card p-4 sm:p-6">
<div class="flex flex-wrap items-center gap-2">
<span class="text-sm font-bold uppercase tracking-wide text-muted">Verb</span>
<template x-for="v in verbs" :key="v"><button class="btn py-1.5" :class="verb === v && 'btn-on'" @click="verb = v" lang="__LANG__" x-text="v"></button></template>
</div>

<div class="relative mt-4 h-72 select-none">
<span class="absolute left-0 top-0 text-xs font-bold uppercase tracking-widest text-muted">&larr; past</span>
<span class="absolute right-0 top-0 text-xs font-bold uppercase tracking-widest text-muted">future &rarr;</span>
<div class="absolute top-1/2 border-t-2 border-dashed border-muted/60" style="left:5%;width:15%"></div>
<div class="absolute top-1/2 -mt-px h-0.5 bg-ink" style="left:20%;right:4%"></div>
<div class="absolute w-0.5 bg-ink/70" style="left:55%;top:calc(50% - 12px);height:24px"></div>
<template x-for="t in tenses.filter((t) => t.stem)" :key="'s' + t.key"><div class="absolute border-l-2 border-dashed border-muted/60" :style="stem(t)"></div></template>
<template x-for="t in tenses.filter((t) => t.span)" :key="'b' + t.key"><button class="absolute h-2 rounded-full transition-colors" :class="cur.key === t.key ? 'bg-accent' : 'bg-accent/25 hover:bg-accent/50'" :style="span(t)" @click="pick(t.key)" :aria-label="t.name" tabindex="-1"></button></template>
<template x-for="(t, k) in tenses" :key="t.key"><button class="absolute z-10 grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full" :style="pos(t)" @click="i = k" :aria-label="t.name" :aria-current="k === i">
<span class="block h-4 w-4 rounded-full border-2 border-accent transition-transform" :class="[t.mood ? 'bg-card' : 'bg-accent', k === i && 'scale-125']"></span></button></template>
<template x-for="(t, k) in tenses" :key="'l' + t.key"><button class="absolute hidden -translate-x-1/2 whitespace-nowrap rounded-lg px-1.5 text-sm font-bold transition-colors sm:block lg:text-base" :class="k === i ? 'text-accent' : 'text-muted hover:text-ink'" :style="label(t)" @click="i = k" lang="__LANG__" x-text="t.name" tabindex="-1"></button></template>
<div class="pointer-events-none absolute h-11 w-11 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-accent bg-accent/15 transition-all duration-500 ease-out" :style="pos(cur)"></div>
</div>

<input type="range" class="seek w-full" min="0" :max="tenses.length - 1" step="1" x-model.number="i" aria-label="Move along the timeline" :aria-valuetext="cur.name">
<div class="flex items-center gap-2">
<button class="btn px-3 py-1.5" @click="go(-1)" :disabled="i === 0" :class="i === 0 && 'opacity-40'" aria-label="Previous tense">&larr;</button>
<p class="flex-1 text-center text-sm text-muted">Drag the slider, tap a point, or use the arrow keys.</p>
<button class="btn px-3 py-1.5" @click="go(1)" :disabled="i === tenses.length - 1" :class="i === tenses.length - 1 && 'opacity-40'" aria-label="Next tense">&rarr;</button>
</div>
</div>

<div class="mt-5 rounded-2xl border border-line bg-card p-5 sm:p-6" aria-live="polite">
<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
<h2 class="text-3xl font-semibold text-accent" lang="__LANG__" x-text="cur.name"></h2>
<span class="chip" x-text="cur.en"></span>
<span class="chip chip-accent" x-show="cur.mood" x-cloak>a mood, not a moment</span>
</div>
<p class="mt-1 text-muted" x-text="cur.hint"></p>
<p class="mt-5 font-display text-4xl font-semibold tracking-tight sm:text-5xl" lang="__LANG__" x-text="form"></p>
<p class="mt-1 text-lg text-muted" x-text="gloss"></p>
<div class="mt-6 grid gap-6 md:grid-cols-2">
<div>
<h3 class="text-sm font-bold uppercase tracking-wide text-muted">When to use it</h3>
<p class="mt-1 text-lg" x-text="cur.use"></p>
<h3 class="mt-4 text-sm font-bold uppercase tracking-wide text-muted">How it is built</h3>
<p class="mt-1 rounded-xl bg-accent/5 px-4 py-3 font-bold" x-html="fmt(cur.structure)"></p>
</div>
<div>
<h3 class="text-sm font-bold uppercase tracking-wide text-muted">Examples</h3>
<ul class="mt-1 space-y-2.5"><template x-for="(x, k) in cur.examples" :key="cur.key + k"><li><p class="text-lg leading-snug" lang="__LANG__" x-html="fmt(x.fr)"></p><p class="text-muted" x-text="x.en"></p></li></template></ul>
</div>
</div>
<a x-show="cur.lesson" class="btn btn-primary mt-6" :href="cur.lesson + '.html'" data-nav><span>Open the lesson:&nbsp;</span><span lang="__LANG__" x-text="cur.name"></span><span>&nbsp;&rarr;</span></a>
</div>
<img x-show="picture" x-cloak :src="picture" :alt="pictureAlt" class="mt-8 w-full rounded-2xl border border-line bg-card">
</section>"""

# A family tree seen by whoever is "moi": tap a person to see what they are for moi, tap again to become them.
# The slider names the family a ring at a time ("stages"); Quiz asks for a relative and you tap the person.
FAMILY = """<section x-data="family" class="mt-6">
<div class="rounded-2xl border border-line bg-card p-4 sm:p-6">
<div class="flex flex-wrap items-center gap-2">
<p class="text-lg"><span class="text-muted">&laquo;&nbsp;Moi&nbsp;&raquo;&nbsp;:</span> <b x-text="meP.name"></b></p>
<button class="btn py-1.5" x-show="!quiz && me !== start" x-cloak @click="become(start)">&larr; <span x-text="startName"></span></button>
<span class="ml-auto"></span>
<button class="btn py-1.5" x-show="!quiz" :class="hide && 'btn-on'" @click="hide = !hide" x-text="hide ? 'Show the words' : 'Hide the words'"></button>
<button class="btn py-1.5" :class="quiz && 'btn-on'" @click="quiz ? stopQuiz() : startQuiz()" x-text="quiz ? 'Back to the tree' : 'Quiz'"></button>
</div>

<input type="range" class="seek mt-4 w-full" min="1" :max="stages.length" step="1" x-model.number="stage" aria-label="How much of the family to name" :aria-valuetext="cur.en">
<div class="flex items-center gap-2">
<button class="btn px-3 py-1.5" @click="stage--" :disabled="stage === 1" :class="stage === 1 && 'opacity-40'" aria-label="Less of the family">&larr;</button>
<p class="flex-1 text-center"><b lang="__LANG__" x-text="cur.fr"></b><br><span class="text-sm text-muted" x-text="stage + ' / ' + stages.length + ' · ' + cur.en"></span></p>
<button class="btn px-3 py-1.5" @click="stage++" :disabled="stage === stages.length" :class="stage === stages.length && 'opacity-40'" aria-label="More of the family">&rarr;</button>
</div>

<div x-show="quiz" x-cloak class="ft-ask mt-4">
<div x-show="q" class="flex flex-wrap items-center gap-3">
<p class="text-xl"><span class="text-muted">__UI_FIND__</span> <b lang="__LANG__" x-text="q && q.text"></b></p>
<span class="ml-auto text-sm font-bold text-muted" x-text="asked + ' / ' + total"></span>
</div>
<div x-show="!q" x-cloak class="flex flex-wrap items-center gap-3">
<p class="text-xl font-semibold" x-text="'__UI_BRAVO__ ' + first + ' / ' + total + ' __UI_FIRST__'"></p>
<span class="ml-auto"></span>
<button class="btn btn-primary" @click="startQuiz()">Again</button><button class="btn" @click="stopQuiz()">Back to the tree</button>
</div>
<p x-show="last" x-cloak class="mt-2 text-sm text-muted"><span class="font-bold text-good">&#10003;</span> <b x-text="last && last.name"></b> <span lang="__LANG__" x-text="last && '= ' + last.text"></span> <span x-text="last && '(' + last.en + ')'"></span></p>
</div>

<div class="ft-scroll mt-4" x-ref="scroll"><div class="ft-stage" :style="'height:' + height + 'px'">
<template x-for="(l, k) in lines" :key="k"><div class="ft-line" :style="l"></div></template>
<template x-for="p in people" :key="p.id"><button class="ft-card" :class="cardClass(p)" :style="pos(p)" @click="tap(p)" :aria-current="p.id === me">
<span class="ft-name" x-text="p.name"></span><span class="ft-word" lang="__LANG__" x-text="word(p)"></span>
</button></template>
</div></div>
<div class="mt-2 flex flex-wrap items-center gap-2"><span class="ft-key ft-km">masculin&nbsp;: mon</span><span class="ft-key ft-kf">f&eacute;minin&nbsp;: ma</span>
<span class="text-sm text-muted" x-show="!quiz">Tap a person to see the word. Tap again to become that person.</span></div>
</div>

<div x-show="!quiz" class="mt-5 rounded-2xl border border-line bg-card p-5 sm:p-6" style="min-height:11rem" aria-live="polite">
<template x-if="!info"><p class="text-muted">Tap someone in the tree: you will see who that person is for <b x-text="meP.name"></b>, and who <b x-text="meP.name"></b> is for them.</p></template>
<template x-if="info && info.t"><div>
<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
<button class="play small" x-show="info.t.audio" @click="hear(info.t)" aria-label="Hear the word">__PLAY__</button>
<h2 class="text-3xl font-semibold" :class="'ft-t' + info.p.g" lang="__LANG__" x-text="info.mine"></h2>
<span class="chip" x-text="info.p.g === 'f' ? 'féminin' : 'masculin'"></span>
<span class="text-muted" x-text="info.t.ipa"></span>
<span class="ml-auto text-xl text-muted" x-text="info.en"></span>
</div>
<p class="mt-4 text-lg leading-snug" lang="__LANG__" x-text="info.fr1"></p><p class="text-muted" x-text="info.en1"></p>
<p class="mt-3 text-lg leading-snug" lang="__LANG__" x-text="info.fr2"></p><p class="text-muted" x-text="info.en2"></p>
</div></template>
<template x-if="info && !info.t"><div>
<h2 class="text-xl font-semibold" x-text="info.p.name"></h2>
<p class="mt-1 text-muted">French has no single word for what <b x-text="info.p.name"></b> is for <b x-text="meP.name"></b>. People say it in full, one link at a time.</p>
</div></template>
<template x-if="info"><button class="btn btn-primary mt-6" @click="become(info.p.id)"><span lang="__LANG__" x-text="'Je suis ' + info.p.name"></span><span>&nbsp;&rarr;</span></button></template>
</div>
</section>"""

# Its own few styles (kept here so the compiled site.css does not have to be rebuilt). Blue = a masculine word, pink = a feminine one.
FAMILY_CSS = """<style>
.ft-scroll{overflow-x:auto;padding:.5rem 0}
.ft-stage{position:relative;min-width:42rem}
.ft-line{position:absolute;background:#CFC5B4;border-radius:2px}
.ft-card{position:absolute;z-index:1;width:14%;height:88px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.2rem;padding:.3rem .2rem;border:2px solid #E4DCCF;border-radius:1rem;background:#fff;text-align:center;line-height:1.15;cursor:pointer;transition:border-color .15s,background .2s,box-shadow .15s,color .2s}
.ft-card:hover{border-color:rgb(var(--accent))}
.ft-name{font-weight:700;font-size:1.05rem}
.ft-word{font-size:.82rem;font-weight:700}
.ft-word:empty{display:none}
.ft-m{border-color:#BAE6FD;background:#F0F9FF}.ft-m .ft-word,.ft-tm{color:#0369A1}
.ft-f{border-color:#FBCFE8;background:#FDF2F8}.ft-f .ft-word,.ft-tf{color:#BE185D}
.ft-dim{color:#5B6475;background:#FAF7F2;border-style:dashed}
.ft-me,.ft-me:hover{background:rgb(var(--accent));border-color:rgb(var(--accent));color:#fff;box-shadow:0 4px 14px rgb(var(--accent)/.35)}
.ft-sel{border-color:rgb(var(--accent));box-shadow:0 0 0 4px rgb(var(--accent)/.25)}
.ft-good{border-color:#1B7550;box-shadow:0 0 0 4px rgb(27 117 80/.2)}
.ft-bad{border-color:#B3261E;animation:ft-shake .3s}
@keyframes ft-shake{25%{transform:translateX(calc(-50% - 5px))}75%{transform:translateX(calc(-50% + 5px))}}
.ft-key{font-size:.72rem;font-weight:700;line-height:1.6;border-radius:999px;padding:0 .55rem;border:1px solid}
.ft-km{color:#0369A1;border-color:#BAE6FD;background:#F0F9FF}.ft-kf{color:#BE185D;border-color:#FBCFE8;background:#FDF2F8}
.ft-ask{border:1px solid #E4DCCF;background:#FAF7F2;border-radius:1rem;padding:1rem;min-height:4.75rem}
@media (prefers-reduced-motion:reduce){.ft-bad{animation:none}.ft-card{transition:none}}
</style>
"""


def crumbs(L, r):
    c = C["courses"][L["course"]]
    return (f'<nav class="flex flex-wrap items-center gap-1.5 text-sm text-muted" aria-label="Breadcrumb" data-nav>'
            f'<a class="hover:text-accent" href="{r}{L["course"]}/index.html">{e(c["name"])}</a><span>/</span>'
            f'<a class="hover:text-accent" href="{r}{L["course"]}/{L["strand"]}/index.html">{e(C["strands"][L["strand"]][0])}</a></nav>')


def data_script(L, r):
    keep = {k: v for k, v in L.items() if k not in ("file", "legacy", "url", "id", "categories", "quiz", "quizTags", "_supp", "_rel")}
    return f'<script>window.ROOT={js(r)};window.MEDIA_BASE={js(C["media_base"])};window.LESSON={js(keep)};</script>'


def related_label(x):
    """Vocabulary: Au marché. What a link to a related lesson says when there is no room for a tile."""
    return f'{C["strands"][x["strand"]][0]}: {x.get("title", x["slug"])}'


def lesson_page(L, prev, nxt, has_offline, parent=None, supplements=()):
    rel, r = L["url"], up(L["url"])
    related = L.get("_rel", ())   # the lessons this one names in "related", and the ones that name it
    course = C["courses"][L["course"]]
    title = L.get("title", L["slug"])
    pager = '<div class="mt-12 flex flex-wrap items-center gap-3" data-nav>'
    pager += f'<a class="btn" href="{r}{prev["url"]}">&larr; {e(prev.get("title", ""))}</a>' if prev else ""
    pager += f'<a class="btn ml-auto" href="{r}{nxt["url"]}">{e(nxt.get("title", ""))} &rarr;</a>' if nxt else ""
    pager += "</div>"
    off = ""   # offline copies are handed out on a Google Drive shared drive: the site offers no downloads

    if L.get("type") == "cards":   # the expression-page design, kept as it was
        aud = L.get("aud_dir") or ""
        aud = aud if aud.startswith("http") else C["media_base"] + aud
        n = sum(len(c["cards"]) for c in L["categories"])
        strand = C["strands"][L["strand"]][0]
        link = 'style="color:rgba(255,255,255,.7)" class="hover:underline"'
        goes = ""   # the lessons this page is paired with ("related")
        if related:
            mono = "font-family:'Space Mono',monospace"
            goes = (f'<p class="mt-8 text-xs uppercase tracking-widest" style="color:rgba(255,255,255,.4);{mono}">Goes with</p>'
                    f'<p class="mt-3 flex flex-wrap justify-center gap-6 text-xs uppercase tracking-widest" style="{mono}" data-nav>'
                    + "".join(f'<a {link} href="{r}{x["url"]}">{e(related_label(x))}</a>' for x in related) + "</p>")
        body = f'''{CARDS_BLOBS}
<div class="relative z-10 flex flex-wrap items-center gap-2 px-6 pt-5 text-xs uppercase tracking-widest" style="font-family:'Space Mono',monospace;color:rgba(255,255,255,.4)" data-nav>
<a {link} href="{r}index.html">{e(C["site_name"])}</a><span>/</span>
<a {link} href="{r}{L["course"]}/index.html">{e(course["name"])}</a><span>/</span>
<a {link} href="{r}{L["course"]}/{L["strand"]}/index.html">{e(strand)}</a>
</div>
<div class="relative z-10 w-full px-6 py-12">
<div class="mb-14 text-center">
<div class="mb-3 flex items-center justify-center gap-4"><span class="badge">{e(strand.upper())}</span><span class="badge">{lv(L.get("level")).upper()}</span></div>
<h1 class="header-glow mb-2 text-5xl font-bold tracking-tight sm:text-7xl" style="font-family:'Playfair Display',serif;font-style:italic;color:white;letter-spacing:-.02em">{e(title)}</h1>
<p class="mb-4 text-2xl" style="color:var(--cyan);opacity:.85;font-family:'Playfair Display','Noto Sans Myanmar',serif">{e(L.get("subtitle", ""))}</p>
<div class="header-line mx-auto w-64"></div>
<p class="mt-4 text-sm uppercase tracking-widest" style="color:rgba(255,255,255,.4);font-family:'Roboto',sans-serif">Expression Flashcards</p>
</div>
<div id="cards"></div>
<div class="mt-14 text-center"><div class="header-line mx-auto mb-5 w-48"></div>
<p class="text-xs uppercase tracking-widest" style="color:rgba(255,255,255,.25);font-family:'Space Mono',monospace"><span id="count">{n}</span> expressions &middot; {e(title)}</p>
<p class="mt-6 flex flex-wrap justify-center gap-6 text-xs uppercase tracking-widest" style="font-family:'Space Mono',monospace" data-nav>
{f'<a {link} href="{r}{prev["url"]}">&larr; {e(prev.get("title", ""))}</a>' if prev else ""}
{f'<a {link} href="{r}{nxt["url"]}">{e(nxt.get("title", ""))} &rarr;</a>' if nxt else ""}</p>{goes}
</div></div>'''
        data = f'const AUD_DIR={js(aud)};const AUD_EXT={js(L.get("aud_ext", "mp3?v=pending"))};const categories={js(L["categories"])};'
        if L.get("quiz"):
            data += f'const quiz={js(L["quiz"])};'
        if L.get("quizTags"):
            data += f'const quizTags={js(L["quizTags"])};'
        tail = f'<script>{data}</script>\n<script src="{r}assets/js/expression-flash.js"></script>\n'
        if L.get("quiz"):
            tail += f'<script src="{r}assets/js/expression-quiz.js"></script>\n'
        tail += f'<script src="{r}assets/js/site.js"></script>\n<script src="{r}assets/js/alpine.min.js"></script>'
        head = f'<link rel="stylesheet" href="{r}assets/css/cards.css">\n<link rel="stylesheet" href="{r}assets/css/expression-quiz.css">\n'
        return frame(rel, f"{title} | {course['name']}", body, L["course"], tail, cls="bg-grid relative min-h-screen", head=head)

    if L.get("type") == "reader":   # one screen: the picture stays put, the text scrolls beside or under it
        end = f'''<div class="flex flex-wrap items-center gap-3" x-data="progress('{L["id"]}')" data-nav>
<button class="btn" :class="on && 'btn-on'" @click="toggle()" x-text="on ? '\\u2713 Done' : 'Mark as done'"></button>{off}
{"".join(f'<a class="btn" href="{r}{x["url"]}">{e(x.get("label", "Practice"))}</a>' for x in supplements)}{"".join(f'<a class="btn" href="{r}{x["url"]}">{e(related_label(x))}</a>' for x in related)}
{f'<a class="btn" href="{r}{nxt["url"]}">Next: {e(nxt.get("title", ""))} &rarr;</a>' if nxt else ""}</div>'''   # a reader has no room for the Supplemental section: its practice pages are buttons at the end
        if L.get("questions"):
            end = QUIZ.replace("mt-12 ", "") + end
        body = (READER.replace("__END__", end).replace("__PLAY__", ICON_PLAY).replace("__IMG__", ICON_IMG).replace("__TITLE__", e(title))
                .replace("__LEVEL__", lv(L.get("level"))).replace("__BACK__", f'{r}{L["course"]}/{L["strand"]}/index.html'))
        tail = f'{data_script(L, r)}\n<script src="{r}assets/js/site.js"></script>\n<script defer src="{r}assets/js/alpine.min.js"></script>'
        return frame(rel, f"{title} | {course['name']}", body, L["course"], tail, cls="site flex h-dvh flex-col overflow-hidden", foot=False)

    shell = {"dialogue": LINES, "shadow": SHADOW, "practice": PRACTICE, "text": TEXT.replace("__ALT__", e(L.get("img_alt", "Picture goes here")))}.get(L.get("type"))
    shell = {"words": WORDS, "hotspots": HOTSPOTS, "timeline": TIMELINE, "family": FAMILY}.get(L.get("type"), shell)
    if L.get("type") == "grammar":
        shell = grammar_shell(L, course["lang"])
    if shell is None:
        shell = soon("This lesson is being written.")
    for key, word in UI.get(course["lang"], UI["en"]).items():
        shell = shell.replace("__UI_" + key + "__", word)
    roman, native, slang = SCRIPT.get(course["lang"], SCRIPT["ja"])
    shell = shell.replace("__ROMAN__", roman).replace("__NATIVE__", native).replace("__SLANG__", slang)
    if L.get("type") == "words" and lib.pending(L):   # no clips yet: do not promise sound
        shell = shell.replace("Tap a word to hear it.", "The audio for this lesson is not recorded yet.")
    shell = shell.replace("__PLAY__", ICON_PLAY).replace("__LOOP__", ICON_LOOP).replace("__IMG__", ICON_IMG).replace("__LANG__", course["lang"]).replace("__TR__", ICON_TR)
    chips = f'<span class="chip chip-accent">{lv(L.get("level") or (parent or {}).get("level"))}</span>'
    for k in ("topic", "register"):
        if L.get(k):
            chips += f'<span class="chip">{e(L[k])}</span>'
    extra, steps = "", ""
    if L.get("steps"):
        steps = '<section class="mt-6 rounded-2xl border border-line bg-card p-5"><h2 class="text-xl font-semibold">How to use this lesson</h2><ol class="mt-2 list-decimal space-y-1 pl-5 text-muted">' + "".join(f"<li>{e(x)}</li>" for x in L["steps"]) + "</ol></section>"
    if L.get("focus"):
        extra += '<section class="mt-8 rounded-2xl border border-line bg-card p-5"><h2 class="text-xl font-semibold">Listen for</h2><ul class="mt-2 list-disc space-y-1 pl-5 text-muted">' + "".join(f"<li>{e(x)}</li>" for x in L["focus"]) + "</ul></section>"
    if L.get("notes"):
        extra += '<section class="mt-8 rounded-2xl border border-line bg-card p-5"><h2 class="text-xl font-semibold">Notes</h2><ul class="mt-2 list-disc space-y-1 pl-5 text-muted">' + "".join(f"<li>{e(x)}</li>" for x in L["notes"]) + "</ul></section>"
    supp = ""
    if supplements:
        supp = '<section class="mt-12" data-nav><h2 class="text-2xl font-semibold">Supplemental section</h2><p class="mt-1 text-muted">More practice with this text.</p>' + grid([
            f'''<a class="tile" data-reveal {f'href="{e(x["href"])}" target="_blank" rel="noopener"' if x.get("type") == "link" else f'href="{r}{x["url"]}"'} data-lesson="{x["id"]}"><h3 class="text-lg font-semibold leading-snug">{e(x.get("title", x["slug"]))}</h3>
{f'<p class="mt-1 text-sm text-muted">{e(x["subtitle"])}</p>' if x.get("subtitle") else ""}
<div class="mt-3"><span class="chip">{e(x.get("label", "Practice"))}</span></div></a>''' for x in supplements]) + "</section>"
    back = f'<a class="btn mt-4 py-1.5" data-nav href="{r}{parent["url"]}">&larr; {e(parent.get("title", ""))}</a>' if parent else ""
    body = f'''<main class="wrap py-6 sm:py-10">
{crumbs(L, r)}
{back}
<div class="mt-4 flex flex-wrap items-center gap-2" data-reveal>{chips}</div>
<h1 class="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl" data-reveal>{e(title)}</h1>
{f'<p class="mt-2 text-xl text-muted" data-reveal>{e(L["subtitle"])}</p>' if L.get("subtitle") else ""}
{f'<p class="mt-3 max-w-2xl text-muted" data-reveal>{inline(L["intro"]) if L.get("type") in lib.SILENT else e(L["intro"])}</p>' if L.get("intro") else ""}
{steps}
{shell}
{(QUIZ if L.get("questions") else "") + extra if L.get("start_hidden") else extra + (QUIZ if L.get("questions") else "")}
{supp}{('<section class="mt-12" data-nav><h2 class="text-2xl font-semibold">Goes with this lesson</h2><p class="mt-1 text-muted">The same words and situations, in other lessons.</p>' + grid([tile(x, rel).replace('<span class="chip">', f'<span class="chip">{e(C["strands"][x["strand"]][0])}</span><span class="chip">', 1) for x in related]) + "</section>") if related else ""}
<div class="mt-10 flex flex-wrap items-center gap-3" x-data="progress('{L["id"]}')" data-nav>
<button class="btn" :class="on && 'btn-on'" @click="toggle()" x-text="on ? '\u2713 Done' : 'Mark as done'"></button>{off}</div>
{pager}
</main>'''
    tail = f'{data_script(L, r)}\n<script src="{r}assets/js/site.js"></script>\n<script defer src="{r}assets/js/alpine.min.js"></script>'
    return frame(rel, f"{title} | {course['name']}", body, L["course"], tail, head=PICTURE_CSS if L.get("type") in ("words", "hotspots") else FAMILY_CSS if L.get("type") == "family" else "")


# ------------------------------------------------------------------ index pages
def strand_text(k, s):
    """The line under a strand's name: the course's own ("strand_text" in site.json) or the shared one."""
    return C["courses"][k].get("strand_text", {}).get(s, C["strands"][s][1])


def course_home(k, items):
    c, rel = C["courses"][k], f"{k}/index.html"
    levels = ""
    for code in c["levels"]:
        n = sum(1 for L in items if L.get("level") == code)
        levels += f'''<a class="tile" data-reveal href="level/{code}.html"><div class="flex items-baseline justify-between"><span class="font-display text-3xl font-semibold text-accent">{lv(code)}</span>
<span class="text-sm text-muted">{f"<span data-count={n}>{n}</span> lesson{'' if n == 1 else 's'}" if n else "soon"}</span></div>
<p class="mt-1 font-bold">{e(C["levels"][code])}</p><p class="mt-1 text-sm text-muted">{e(c["can"][code])}</p></a>'''
    strands = ""
    for s in c["strands"]:
        n = sum(1 for L in items if L["strand"] == s)
        strands += f'''<a class="tile" data-reveal href="{s}/index.html"><div class="flex items-baseline justify-between"><h3 class="text-xl font-semibold">{e(C["strands"][s][0])}</h3>
<span class="text-sm text-muted">{f'<span data-count="{n}">{n}</span>' if n else "soon"}</span></div><p class="mt-1 text-sm text-muted">{e(strand_text(k, s))}</p></a>'''
    body = f'''<main>
<section class="hero border-b border-line bg-accent/5">{hero_canvas(k)}<div class="wrap py-12 sm:py-16">
<p class="flex flex-wrap gap-2" data-reveal><span class="chip chip-accent">{e(c["for"])}</span><span class="chip">{e(c["range"])}</span></p>
<h1 class="mt-4 text-5xl font-semibold tracking-tight sm:text-6xl" data-split>{e(c["name"])} <span class="font-display italic text-accent" lang="{c.get("native_lang", c["lang"])}">{e(c["native"])}</span></h1>
<p class="mt-4 max-w-2xl text-xl text-muted" data-reveal>{e(c["tagline"])}</p>
<div class="mt-6 flex flex-wrap gap-3" data-reveal><a class="btn btn-primary" href="#levels">Start where you are</a><a class="btn" href="#skills">Pick a skill</a>{f'<a class="btn" href="{e(c["offline_url"])}" target="_blank" rel="noopener">Offline lessons</a>' if c.get("offline_url") else ""}</div>
{'<p class="mt-3 max-w-2xl text-sm text-muted">No internet? Every lesson is also one file you can download from Google Drive and open on a tablet or computer, with its pictures and sound inside.</p>' if c.get("offline_url") else ""}
</div></section>
<section id="levels" class="wrap scroll-mt-28 py-12"><h2 class="text-3xl font-semibold" data-reveal>Start where you are</h2>
<p class="mt-1 text-muted" data-reveal>Not sure of your level? Pick the one whose lessons look just slightly too hard.</p>{grid([levels])}</section>
<section id="skills" class="wrap scroll-mt-28 pb-4"><h2 class="text-3xl font-semibold" data-reveal>Or pick a skill</h2>{grid([strands])}</section>
</main>'''
    write(rel, frame(rel, f"{c['name']} | {C['site_name']}", body, k, f'<script src="../assets/js/site.js"></script>'))


def level_page(k, code, items):
    c, rel = C["courses"][k], f"{k}/level/{code}.html"
    body = f'''<main class="wrap py-8 sm:py-12">
<nav class="text-sm text-muted" data-nav><a class="hover:text-accent" href="../index.html">{e(c["name"])}</a> / Levels</nav>
<h1 class="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl" data-split><span class="text-accent">{lv(code)}</span> &middot; {e(C["levels"][code])}</h1>
<p class="mt-2 max-w-2xl text-xl text-muted" data-reveal>{e(c["can"][code])}</p>
<div class="mt-4 flex flex-wrap gap-2">{"".join(f'<a class="btn py-1.5{" btn-on" if x == code else ""}" href="{x}.html">{lv(x)}</a>' for x in c["levels"])}</div>'''
    for s in c["strands"]:
        ls = [L for L in items if L["strand"] == s and L.get("level") == code]
        body += f'<section class="mt-10"><h2 class="text-2xl font-semibold" data-reveal>{e(C["strands"][s][0])}</h2>'
        body += grid([tile(L, rel, False) for L in ls]) if ls else soon(f"{C['strands'][s][0]} lessons for {lv(code)} are not written yet.")
        body += "</section>"
    write(rel, frame(rel, f"{lv(code)} | {c['name']}", body + "</main>", k, '<script src="../../assets/js/site.js"></script>'))


def strand_page(k, s, items):
    c, rel = C["courses"][k], f"{k}/{s}/index.html"
    ls = [L for L in items if L["strand"] == s]
    body = f'''<main class="wrap py-8 sm:py-12">
<nav class="text-sm text-muted" data-nav><a class="hover:text-accent" href="../index.html">{e(c["name"])}</a></nav>
<h1 class="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl" data-split>{e(C["strands"][s][0])}</h1>
<p class="mt-2 text-xl text-muted" data-reveal>{e(strand_text(k, s))}</p>'''
    topics = []
    for L in ls:
        t = L.get("topic") or "Lessons"
        if t not in topics:
            topics.append(t)
    for t in topics:
        group = sorted([L for L in ls if (L.get("topic") or "Lessons") == t],
                       key=lambda L: (lib.LEVEL_ORDER.index(L["level"]) if L.get("level") in lib.LEVEL_ORDER else 9, L.get("order", 500), lib.natural(L["slug"])))
        body += f'<section class="mt-10"><h2 class="text-2xl font-semibold" data-reveal>{e(t)}</h2>{grid([tile(L, rel) for L in group])}</section>'
    if not ls:
        body += soon("These lessons are not written yet.")
    write(rel, frame(rel, f"{C['strands'][s][0]} | {c['name']}", body + "</main>", k, '<script src="../../assets/js/site.js"></script>'))


# Home page: words for the moving band under the hero, and the four steps of a lesson
GREETINGS = [("fr", "fr", "Bonjour"), ("eng", "en", "Hello"), ("jap", "ja", "こんにちは"), ("kor", "ko", "안녕하세요"), ("eng", "my", "မင်္ဂလာပါ"),
             ("fr", "fr", "Merci"), ("eng", "en", "Thank you"), ("jap", "ja", "ありがとう"), ("kor", "ko", "감사합니다"), ("fr", "fr", "À bientôt")]
STEPS = [("Listen", "Hear it first. Read it after.", '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="1.5"/><rect x="17" y="14" width="4" height="6" rx="1.5"/>'),
         ("Read", "Read it, and tap any part to hear it again.", '<path d="M12 6.5C10 5 7 4.5 4 5v13c3-.5 6 0 8 1.5 2-1.5 5-2 8-1.5V5c-3-.5-6 0-8 1.5z"/><path d="M12 6.5V19.5"/>'),
         ("Speak", "Say it out loud, with the recording and then alone.", '<path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-7l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/><path d="M8 11h.01M12 11h.01M16 11h.01"/>'),
         ("Check", "A short quiz shows what stuck.", '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>')]
ARROW = '<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def home(all_lessons):
    """The home page. The hero is the globe (assets/js/globe.js, tools/globe.py): a dark band the canvas fills.
    data-globe-slot is the square the globe sits in; each .globe-pin is the label that follows a country;
    anything with data-globe-link turns the globe to that course's country when pointed at."""
    courses = C["courses"]
    nat = lambda c: f'lang="{c.get("native_lang", c["lang"])}"'
    total = sum(1 for L in all_lessons if L["course"] in courses)
    tiles = ""
    for k, c in courses.items():
        n = sum(1 for L in all_lessons if L["course"] == k)
        tiles += f'''<a class="tile course-tile p-7" data-reveal data-course="{k}" data-globe-link="{k}" href="{k}/index.html">
<span class="go">{ARROW}</span>
<p class="font-display text-4xl font-semibold italic text-accent" {nat(c)}>{e(c["native"])}</p>
<h3 class="mt-3 text-2xl font-semibold">{e(c["name"])}</h3>
<p class="mt-2 flex flex-wrap gap-1.5"><span class="chip chip-accent">{e(c["for"])}</span><span class="chip">{e(c["range"])}</span></p>
<p class="mt-3 text-muted">{e(c["tagline"])}</p>
<p class="mt-4 text-sm font-bold text-accent"><span data-count="{n}">{n}</span> lesson{"" if n == 1 else "s"}</p></a>'''
    pill = lambda k, c: f'<a class="lang-pill" data-globe-link="{k}" data-course="{k}" href="{k}/index.html"><b {nat(c)}>{e(c["native"])}</b><span>{e(c["name"])}</span></a>'
    pills = "".join(pill(k, c) for k, c in courses.items())
    pins = "".join(f'<a class="globe-pin" data-globe="{k}" data-course="{k}" href="{k}/index.html" tabindex="-1" aria-hidden="true"><b {nat(c)}>{e(c["native"])}</b><span>{e(c["name"])}</span></a>'
                   for k, c in courses.items())
    words = "".join(f'<span data-course="{k}" lang="{lang}">{e(w)}</span>' for k, lang, w in GREETINGS)
    steps = "".join(f'''<li class="how-step" data-reveal><span class="how-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icon}</svg></span>
<p class="how-n">Step {i}</p><h3 class="text-xl font-semibold">{name}</h3><p class="mt-1 text-muted">{e(text)}</p></li>''' for i, (name, text, icon) in enumerate(STEPS, 1))
    body = f'''<main>
<section class="space" data-globe-root>
<canvas data-hero="globe" aria-hidden="true"></canvas>
<div class="wrap space-grid">
<div class="space-copy">
<p class="eyebrow" data-reveal><i></i>Free for everyone &middot; No account</p>
<h1 data-split>Learn a language by ear, by eye and <em>out loud.</em></h1>
<p class="space-lead" data-reveal>Free lessons with real audio. Read, listen, speak, and check what stuck.</p>
<div class="space-langs" data-reveal>{pills}</div>
</div>
<div class="globe-slot" data-globe-slot><p class="globe-hint" aria-hidden="true">Drag to spin &middot; pick a country</p></div>
</div>
{pins}
<a class="space-cue" href="#courses" aria-label="See the courses"><i></i></a>
</section>
<div class="marquee" aria-hidden="true"><div class="marquee-track">{words}{words}</div></div>
<section id="courses" class="wrap scroll-mt-20 pb-6 pt-10 sm:pt-14">
<p class="kicker" data-reveal>The courses</p>
<h2 class="mt-2 max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl" data-reveal>{len(courses)} languages, <span class="text-accent"><span data-count="{total}">{total}</span> lessons</span>, all free.</h2>
<div class="mt-8 grid gap-5 {"md:grid-cols-3" if len(courses) % 3 == 0 else "md:grid-cols-2"}">{tiles}</div>
</section>
<section class="wrap py-14 sm:py-20">
<p class="kicker" data-reveal>How a lesson works</p>
<h2 class="mt-2 max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl" data-reveal>Ears first. Then eyes. Then your own voice.</h2>
<div class="how"><div class="how-line"><i data-draw></i></div><ol class="how-steps">{steps}</ol></div>
</section>
<section class="wrap pb-4"><div class="outro" data-reveal>
<h2 class="text-3xl font-semibold tracking-tight sm:text-4xl">Pick a language and press play.</h2>
<p class="mt-2 text-white/70">No sign-up. Every lesson is open.</p>
<div class="space-langs">{pills}</div>
</div></section>
</main>'''
    write("index.html", frame("index.html", C["site_name"], body, cls="site home"))


def offline_index(all_lessons, have):
    rel = "offline/index.html"
    body = '''<main class="wrap py-8 sm:py-12"><h1 class="text-4xl font-semibold tracking-tight sm:text-5xl">Offline lessons</h1>
<p class="mt-2 max-w-2xl text-xl text-muted">Each file is one complete lesson: text, pictures, audio and fonts inside. Download it, then open it with a browser from your file manager. No internet needed.</p>'''
    for k, c in C["courses"].items():
        ls = [L for L in all_lessons if L["course"] == k and L["id"] in have]
        body += f'<section class="mt-10" data-course="{k}"><h2 class="text-2xl font-semibold">{e(c["name"])}</h2>'
        if ls:
            body += '<ul class="mt-3 divide-y divide-line rounded-2xl border border-line bg-card">' + "".join(
                f'<li class="flex items-center gap-3 px-4 py-3"><span class="chip chip-accent">{lv(L.get("level"))}</span><span class="flex-1 font-bold">{e(L.get("title", L["slug"]))}</span>'
                f'<span class="text-sm text-muted">{have[L["id"]] / 1048576:.1f} MB</span><a class="btn py-1.5" download href="../{k}/single/{L["strand"]}__{L["slug"]}.html">Download</a></li>' for L in ls) + "</ul>"
        else:
            body += soon("No offline files built yet. Run 3_offline.bat.")
        body += "</section>"
    write(rel, frame(rel, f"Offline lessons | {C['site_name']}", body + "</main>"))


def main():
    all_lessons = lib.lessons()
    have = {}
    for L in all_lessons:
        p = os.path.join(ROOT, L["course"], "single", f"{L['strand']}__{L['slug']}.html")
        if os.path.exists(p):
            have[L["id"]] = os.path.getsize(p)
    catalog = []
    extras = [L for L in all_lessons if L.get("supplement_of")]      # pages that hang under another lesson
    all_lessons = [L for L in all_lessons if not L.get("supplement_of")]
    for X in extras:
        pid = f"{X['course']}/{X['strand']}/{X['supplement_of']}"
        parent = next((L for L in all_lessons if L["id"] == pid), None)
        if parent is None:
            print(f"  {X['id']}: supplement_of points to a lesson that does not exist ({pid})")
            continue
        parent.setdefault("_supp", []).append(X)
        if X.get("type") == "link":   # a supplement kept somewhere else ("href"): its tile opens that address
            continue
        if X.get("type") in lib.HAND:   # a hand-made supplement (a mind map page): linked from its lesson, never generated
            if not os.path.exists(os.path.join(ROOT, X["url"])):
                print(f"  {X['id']}: page {X['url']} is missing")
            continue
        write(X["url"], lesson_page(X, None, None, X["id"] in have, parent=parent))
    by_id = {L["id"]: L for L in all_lessons}
    for L in all_lessons:   # "related": ["fr/vocabulary/marche", ...] links two lessons, and each shows the other
        for rid in L.get("related", ()):
            X = by_id.get(rid.strip("/")) or by_id.get(f'{L["course"]}/{rid.strip("/")}')
            if X is None or X is L:
                print(f"  {L['id']}: related names a lesson that does not exist ({rid})")
                continue
            for a, b in ((L, X), (X, L)):
                if b not in a.setdefault("_rel", []):
                    a["_rel"].append(b)
    for k, c in C["courses"].items():
        items = [L for L in all_lessons if L["course"] == k]
        for s in c["strands"]:
            ls = [L for L in items if L["strand"] == s]
            for i, L in enumerate(ls):
                if L.get("type") in lib.HAND:   # a hand-made page that already sits at L["url"]: listed, never generated
                    if not os.path.exists(os.path.join(ROOT, L["url"])):
                        print(f"  {L['id']}: game page {L['url']} is missing")
                else:
                    write(L["url"], lesson_page(L, ls[i - 1] if i else None, ls[i + 1] if i + 1 < len(ls) else None, L["id"] in have, supplements=L.get("_supp", ())))
                catalog.append({"id": L["id"], "url": L["url"], "course": k, "strand": s, "level": L.get("level"), "level_provisional": bool(L.get("level_provisional")),
                                "topic": L.get("topic"), "type": L.get("type"), "title": L.get("title"), "clips": len(lib.clips(L)), "images": len(lib.images(L)),
                                "audio": "pending" if lib.pending(L) else "wired", "quiz": bool(L.get("quiz") or L.get("questions"))})
            strand_page(k, s, items)
        stray = [L["id"] for L in items if L["strand"] not in c["strands"]]
        if stray:
            print("  not built (strand not in site.json):", ", ".join(stray))
        for code in c["levels"]:
            level_page(k, code, items)
        course_home(k, items)
    home(all_lessons)
    old = os.path.join(ROOT, "offline", "index.html")   # the site no longer has a downloads page (see lesson_page)
    if os.path.exists(old):
        os.remove(old)
        print("  removed offline/index.html")
    write("assets/data/catalog.json", json.dumps(catalog, ensure_ascii=False, indent=1) + "\n")
    print(f"built {len(catalog)} lesson pages and {len(extras)} supplement pages, {len(have)} with an offline copy")


if __name__ == "__main__":
    main()
