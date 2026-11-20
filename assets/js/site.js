/* Shared lesson engine (Alpine.js components). A lesson page defines, before this file:
     window.LESSON     the lesson's JSON (content/<course>/<strand>/<slug>.json)
     window.MEDIA_BASE where the audio lives online (site.json: media_base)
     window.ROOT       relative path back to the site root ("../../")
   Audio wire: MEDIA_BASE + LESSON.aud_dir + NN + "." + LESSON.aud_ext   (01.mp3, 02.mp3 ...)
   While aud_ext is "mp3?v=pending" (or aud_dir is empty) the Play buttons are greyed out.
   Offline single-file builds define EMBED = { "<url>": dataURI } (tools/offline.py). */
(function () {
  const L = window.LESSON || {}, BASE = window.MEDIA_BASE || "", ROOT = window.ROOT || "";
  const pad = (n) => String(n).padStart(2, "0");
  const media = (u) => (typeof EMBED !== "undefined" && EMBED[u]) || u;
  /* Alternative wire: one recording for the whole text. LESSON.audio_file is its path under MEDIA_BASE,
     and each sentence has "t": [start, end] in seconds. Nothing is cut or re-encoded. */
  /* "audio_ver" is that recording's version tag (set by `audio.py upload`): a new take keeps its file name and
     gets a new tag, so browsers and the CDN fetch it instead of replaying a saved copy. It covers the glossary clips too. */
  const VER = L.audio_ver ? "?v=" + L.audio_ver : "";
  const FILE = L.audio_file ? media((/^https?:/.test(L.audio_file) ? "" : BASE) + L.audio_file + VER) : "";
  const SEG = {};
  (L.paragraphs || []).flat().forEach((s) => { if (s.t) SEG[s.n] = s.t; });
  /* Shadowing chunks taken from a longer clip: a chunk with "clip" plays clip NN = that number (not its own),
     and with "t": [start, end] only that part of it. `tools/audio.py chunks <lesson>` writes the "t" values. */
  const CH = {}, clipEls = {};
  (L.chunks || []).forEach((c) => { if (c.clip) CH[c.n] = c; });
  let fileEl = null, tick = null, wordEl = null;
  const getFile = () => fileEl || (fileEl = new Audio(FILE));
  /* glossary clips are named by word (ambre.mp3), in LESSON.glossary_dir */
  const wordUrl = (name) => media(BASE + (L.glossary_dir || "") + (name.includes(".") ? name : name + ".mp3") + VER);
  function playWord(name) { stop(); if (wordEl) wordEl.pause(); wordEl = new Audio(wordUrl(name)); wordEl.play().catch(() => {}); }
  const pending = !FILE && (!L.aud_dir || /pending/.test(L.aud_ext || ""));
  const clipUrl = (n) => (/^https?:/.test(L.aud_dir) ? "" : BASE) + L.aud_dir + pad(n) + "." + (L.aud_ext || "mp3");
  const imgUrl = (n) => media(ROOT + (L.img_dir || "") + n + "." + (L.img_ext || "jpg"));
  /* Pause: P.held freezes whatever is playing, and every gap between clips, until Resume. */
  let P = { held: false };
  const sleep = async (ms) => {
    await new Promise((r) => setTimeout(r, ms));
    while (P.held) await new Promise((r) => setTimeout(r, 120));
  };

  let cur = null, done = null, driven = null;   // driven: the on-page player this script started itself
  function stop() { P.held = false; driven = null; clearInterval(tick); if (cur) { cur.pause(); cur = null; } if (done) { const d = done; done = null; d(0); } }
  /* plays clip n; resolves with its length in seconds (0 if it could not play or was stopped) */
  function play(n, rate) {
    stop();
    return new Promise((res) => {
      if (pending || !n) return res(0);
      const ch = FILE ? null : CH[n];
      if (FILE || (ch && ch.t)) {       // play one sentence out of the single recording, or one chunk out of its clip
        const seg = FILE ? SEG[n] : ch.t;
        if (!seg) return res(0);
        const a = FILE ? getFile() : (clipEls[ch.clip] || (clipEls[ch.clip] = new Audio(media(clipUrl(ch.clip)))));
        a.playbackRate = rate || 1; cur = a; done = res;
        const end = (ok) => { clearInterval(tick); a.pause(); if (done === res) { done = null; cur = null; res(ok ? seg[1] - seg[0] : 0); } };
        const go = () => {
          a.currentTime = seg[0];
          a.play().then(() => { tick = setInterval(() => { if (a.currentTime >= seg[1] || a.ended) end(true); }, 25); }).catch(() => end(false));
        };
        a.onerror = () => end(false);
        if (a.readyState >= 1) go(); else a.addEventListener("loadedmetadata", go, { once: true });
        return;
      }
      /* a dialogue line has its own player on the page (<audio data-clip>): drive that one, so its slider moves */
      const own = document.querySelector('audio[data-clip="' + n + '"]');
      const a = own || new Audio(media(clipUrl(ch ? ch.clip : n)));
      if (own) { try { own.currentTime = 0; } catch (e) {} driven = own; }
      a.playbackRate = rate || 1; cur = a; done = res;
      const end = (ok) => { if (done === res) { done = null; cur = null; res(ok ? a.duration || 1 : 0); } };
      a.onended = () => end(true); a.onerror = () => end(false);
      a.play().catch(() => end(false));
    });
  }
  /* A story page read in one go (page.audio = "p01": p01.mp3 in aud_dir). page.t = { "<chunk>": [start, end] } inside it:
     onChunk(n) is called as the voice reaches each chunk. Resolves like play(). Made by `tools/audio.py pages`. */
  function playPageClip(p, rate, onChunk) {
    stop();
    return new Promise((res) => {
      if (pending) return res(0);
      const marks = Object.entries(p.t || {}).map(([n, t]) => [+n, t[0]]).sort((x, y) => x[1] - y[1]);
      const url = (/^https?:/.test(L.aud_dir) ? "" : BASE) + L.aud_dir + p.audio + "." + (L.aud_ext || "mp3");
      const a = new Audio(media(url));
      a.playbackRate = rate || 1; cur = a; done = res;
      let on = 0;
      const end = (ok) => { clearInterval(tick); if (done === res) { done = null; cur = null; res(ok ? a.duration || 1 : 0); } };
      a.onended = () => end(true); a.onerror = () => end(false);
      a.play().then(() => {
        tick = setInterval(() => {
          let n = 0;
          for (const m of marks) if (a.currentTime >= m[1] - 0.05) n = m[0]; else break;
          if (n && n !== on) { on = n; onChunk(n); }
        }, 40);
      }).catch(() => end(false));
    });
  }
  const common = () => ({
    pending, rate: 1, playing: 0, busy: false, run: 0,
    /* every new action takes a new run number; a sequence that wakes up under an old number stops quietly */
    async say(n) { const r = ++this.run; this.busy = false; this.playing = n; await play(n, this.rate); if (r === this.run) this.playing = 0; },
    halt() { this.run++; this.busy = false; this.playing = 0; stop(); },
    P,   // shared pause state (P.held), reactive: the pages read it for the Pause / Resume button
    /* pause in the middle of a clip or between two clips; Resume carries on from the same spot */
    togglePause() {
      if (!(this.playing || this.busy)) return;
      P.held = !P.held;
      if (cur) { if (P.held) cur.pause(); else cur.play().catch(() => {}); }
    },
    slow() { this.rate = this.rate === 1 ? 0.75 : 1; },
  });

  document.addEventListener("alpine:init", () => {
    P = Alpine.reactive(P);
    /* space bar = pause / resume, when the focus is not on a button or a text box */
    document.addEventListener("keydown", (ev) => {
      if (ev.code !== "Space" || (ev.target.closest && ev.target.closest("button, input, textarea, select, summary, a, video"))) return;
      const el = document.querySelector("[x-data=lines], [x-data=shadow], [x-data=reader], [x-data=text]");
      const d = el && Alpine.$data(el);
      if (d && (d.playing || d.busy) && d.togglePause) { ev.preventDefault(); d.togglePause(); }
    });
    /* ---- reader: picture pages, tappable chunks ---- */
    Alpine.data("reader", () => ({
      ...common(), i: 0, tr: false, broken: {}, pages: L.pages || [],
      hasTr: !!L.translation && (L.pages || []).some((p) => p.tr), trLabel: (L.translation || {}).label || "Translation",
      trLang: (L.translation || {}).lang || "",
      init() {
        /* the picture stays put; the text pane follows the voice, and goes back to the top on a new page */
        this.$watch("playing", (n) => n && this.$nextTick(() => {
          const el = this.$root.querySelector(".chunk.playing");
          if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }));
        this.$watch("i", () => { if (this.$refs.pane) this.$refs.pane.scrollTop = 0; });
      },
      get page() { return this.pages[this.i] || { sentences: [] }; },
      img(p) { return p.img ? imgUrl(p.img) : ""; },
      go(d) { this.halt(); this.i = Math.max(0, Math.min(this.pages.length - 1, this.i + d)); },
      async playPage() {
        if (this.busy) return this.halt();
        const r = ++this.run; this.busy = true;
        if (this.page.audio) {   // the whole page in one take: it reads like a sentence, and each chunk lights up as it is reached
          this.playing = (this.page.sentences[0] || [[0, 0]])[0][1];
          await playPageClip(this.page, this.rate, (n) => { if (r === this.run) this.playing = n; });
          if (r !== this.run) return;
          this.playing = 0; this.busy = false;
          return;
        }
        for (const s of this.page.sentences) for (const c of s) {
          this.playing = c[1]; const d = await play(c[1], this.rate);
          if (r !== this.run) return;
          if (!d) break;
          await sleep(250); if (r !== this.run) return;
        }
        this.playing = 0; this.busy = false;
      },
    }));

    /* ---- lines: dialogues, phrase lists (speaking, listening, Japanese) ---- */
    Alpine.data("lines", () => {
      const sections = L.sections || [{ lines: L.lines || [] }];
      const all = sections.flatMap((s) => s.lines);
      const langs = L.support || [...new Set(all.flatMap((l) => Object.keys(l.tr || {})))];
      return {
        ...common(), sections, langs, speakers: L.speakers || {},
        names: { en: "English", my: "မြန်မာ", fr: "Français" },
        trLang: L.start_hidden ? "" : langs[0] || "", trOpen: {}, hasScript: all.some((l) => l.romaji || l.rom), script: all.some((l) => l.hangul) ? "both" : "romaji",   // Korean shows Hangul under the romanization from the start
        clip(n) { return media(clipUrl(n)); },
        tone(l) { const i = Object.keys(this.speakers).indexOf(l.who); return i < 0 ? "spk-none" : "spk-" + (i % 4); },
        hasTr(l) { return !!l.tr && langs.some((k) => l.tr[k]); },
        /* the learner used a line's own player: stop whatever else is playing and follow that line */
        init() {
          const others = (el) => document.querySelectorAll("audio[data-clip]").forEach((x) => { if (x !== el && !x.paused) x.pause(); });
          this.$root.addEventListener("play", (ev) => {
            const el = ev.target;
            if (!el.dataset || !el.dataset.clip) return;
            el.playbackRate = this.rate;
            if (el === driven) return;
            this.run++; this.busy = false; stop(); others(el);
            this.playing = +el.dataset.clip;
          }, true);
          const off = (ev) => { const el = ev.target; if (el.dataset && el.dataset.clip && el !== driven && +el.dataset.clip === this.playing && !this.busy) this.playing = 0; };
          this.$root.addEventListener("pause", off, true);
          this.$root.addEventListener("ended", off, true);
        },
        hide: !!L.start_hidden, shown: {}, role: "",   // "start_hidden": true = a listening lesson: ears first
        get roles() { return Object.keys(this.speakers); },
        /* a romanized line: Japanese has "romaji" + "kana", Korean "rom" + "hangul" */
        main(l) { const r = l.romaji || l.rom, k = l.kana || l.hangul; return r ? (this.script === "kana" ? k || r : r) : l.text; },
        sub(l) { return (l.romaji || l.rom) && this.script === "both" ? l.kana || l.hangul : ""; },
        veiled(l) { return (this.hide || (this.role && this.role === l.who)) && !this.shown[l.n]; },
        async playAll() {
          if (this.busy) return this.halt();
          const r = ++this.run; this.busy = true; this.shown = {};
          for (const l of all) {
            this.playing = l.n;
            if (this.role && this.role === l.who) { await sleep(3500); if (r !== this.run) return; this.shown[l.n] = true; }
            const d = await play(l.n, this.rate);
            if (r !== this.run) return;
            if (!d && !pending) break;
            await sleep(pending ? 1200 : 350); if (r !== this.run) return;
          }
          this.playing = 0; this.busy = false;
        },
      };
    });

    /* ---- text: a reading in paragraphs; tap a sentence to hear it, tap an underlined word for its meaning ---- */
    Alpine.data("text", () => {
      const split = (s) => {            // cuts a sentence into plain parts and glossed words
        let parts = [{ t: s.text }];
        for (const key of Object.keys(s.gloss || {}).sort((a, b) => b.length - a.length)) {
          const g = s.gloss[key];
          for (let k = 0; k < parts.length; k++) {
            if (parts[k].g) continue;
            const at = parts[k].t.indexOf(key);
            if (at < 0) continue;
            const t = parts[k].t;
            parts.splice(k, 1, { t: t.slice(0, at) }, { t: key, g: { ipa: g[0], en: g[1], base: g[2] || "" } }, { t: t.slice(at + key.length) });
            break;
          }
        }
        return parts.filter((p) => p.t);
      };
      /* which glossary clip goes with a word in the text: by its base form, else by the word minus an ending */
      const plain = (w) => w.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      const clips = {};
      /* a glossary entry may hold several forms ("chasser / la chasse", "un os (des os)"): each form, without its article, finds the clip */
      const forms = (w) => w.replace(/\([^)]*\)/g, "").split(/\s*[\/,]\s*/).map((x) => plain(x.trim().replace(/^(un|une|le|la|les|des|se)\s+|^[ls]['’]/i, "").trim())).filter(Boolean);
      (L.glossary || []).forEach((g) => { const a = g.audio || g.word; clips[plain(g.word)] = a; forms(g.word).forEach((k) => { if (!clips[k]) clips[k] = a; }); });
      const clipFor = (t, base) => {
        const w = plain(t), b = base ? plain(base.split(" /")[0]) : "";
        for (const k of [b, w, w.replace(/s$/, ""), w.replace(/e$/, ""), w.replace(/es$/, ""), w.replace(/le$/, ""), w.replace(/x$/, ""), w.replace(/ue$/, ""), w.replace(/aux$/, "al")]) if (k && clips[k]) return clips[k];
        return "";
      };
      const paras = (L.paragraphs || []).map((p) => p.map((s) => ({ ...s, parts: split(s).map((x) => (x.g ? { ...x, g: { ...x.g, audio: clipFor(x.t, x.g.base) } } : x)) })));
      const all = paras.flat(), words = [];
      all.forEach((s) => s.parts.forEach((p) => { if (p.g && !words.some((w) => w.t.toLowerCase() === p.t.toLowerCase())) words.push({ t: p.t, ...p.g }); }));
      return {
        ...common(), paras, words, word: null, broken: false, hero: L.img ? media(ROOT + L.img) : "",
        langs: L.support || ["en"], names: { en: "English", my: "မြန်မာ" }, trLang: "",
        glossary: L.glossary || [], hasFile: !!FILE, pos: 0, dur: 0, on: false, cont: false,
        pick(part) { this.word = this.word && this.word.t === part.t ? null : { t: part.t, ...part.g }; if (this.word && this.word.audio) this.hear(this.word.audio); },
        hear(name) { this.cont = false; this.run++; this.busy = false; this.playing = 0; playWord(name); },
        /* ---- the player for a single recording: play, pause, stop, slide ---- */
        init() {
          if (!FILE) return;
          const a = getFile(); a.preload = "metadata";
          a.addEventListener("loadedmetadata", () => { this.dur = a.duration; });
          a.addEventListener("play", () => { this.on = true; });
          a.addEventListener("pause", () => { this.on = false; });
          a.addEventListener("ended", () => { this.cont = false; this.playing = 0; });
          a.addEventListener("timeupdate", () => {
            this.pos = a.currentTime;
            if (!this.cont) return;
            const s = all.find((x) => x.t && a.currentTime >= x.t[0] - 0.05 && a.currentTime < x.t[1] + 0.2);
            this.playing = s ? s.n : 0;
          });
        },
        filePlay() { this.run++; stop(); if (wordEl) wordEl.pause(); const a = getFile(); this.cont = true; a.playbackRate = this.rate; a.play().catch(() => {}); },
        filePause() { getFile().pause(); },
        fileStop() { this.halt(); const a = getFile(); a.pause(); a.currentTime = 0; this.cont = false; this.pos = 0; },
        seek(v) { const a = getFile(); a.currentTime = +v; this.pos = +v; },
        clock(s) { s = Math.floor(s || 0); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); },
        async say(n) { this.cont = false; if (wordEl) wordEl.pause(); const r = ++this.run; this.busy = false; this.playing = n; await play(n, this.rate); if (r === this.run) this.playing = 0; },
        slow() { this.rate = this.rate === 1 ? 0.75 : 1; if (FILE) getFile().playbackRate = this.rate; },
        line(p) { return p.map((s) => (s.tr || {})[this.trLang] || "").join(" "); },
        async playAll() {
          if (this.busy) return this.halt();
          const r = ++this.run; this.busy = true;
          for (const s of all) {
            this.playing = s.n; const d = await play(s.n, this.rate);
            if (r !== this.run) return;
            if (!d) break;
            await sleep(350); if (r !== this.run) return;
          }
          this.playing = 0; this.busy = false;
        },
      };
    });

    /* ---- practice: exercise blocks (true/false, choice, cloze, open questions, ordering) and video ---- */
    Alpine.data("practice", () => {
      const norm = (s) => String(s || "").trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[\u2019\u2018]/g, "'");
      const loose = (s) => norm(s).replace(/[.,!?;:\u2026]/g, "").replace(/\s+/g, " ").trim();   // a typed sentence: punctuation is not marked
      const fresh = (b) => (b.kind === "slides" || b.kind === "picture" ? [] : b.kind === "order" ? (b.start || b.items.map((_, i) => i)).map((k) => ({ k, text: b.items[k] })) : b.items ? b.items.map(() => null) : []);
      return {
        blocks: (L.blocks || []).map((b) => ({ ...b, ans: fresh(b), checked: false, shown: false })),
        offline: typeof EMBED !== "undefined", pending, heard: 0,
        async hear(n) { this.heard = n; await play(n); if (this.heard === n) this.heard = 0; },
        url(src) { return media((/^https?:/.test(src) ? "" : BASE) + src); },
        pic(src) { return media(ROOT + src); },   // a slide: a picture of this site
        tracks(b) { return [].concat(b.audio || []).map((a) => (typeof a === "string" ? { src: a } : a)); },   // "audio": a recording, or several with labels
        right(b, i) {
          if (b.kind === "order") return b.ans[i].k === i;
          if (b.kind === "cloze") return loose(b.ans[i]) === loose(b.items[i].answer);
          return b.ans[i] === b.items[i].answer;
        },
        score(b) { return (b.items || []).filter((_, i) => this.right(b, i)).length; },
        total(b) { return (b.items || []).length; },
        mark(b, i) { return !b.checked ? "" : this.right(b, i) ? "is-right" : "is-wrong"; },
        set(b, i, v) { b.ans[i] = v; b.checked = false; },
        move(b, i, d) { const j = i + d; if (j < 0 || j >= b.ans.length) return; const t = b.ans[i]; b.ans[i] = b.ans[j]; b.ans[j] = t; b.ans = [...b.ans]; b.checked = false; },
        check(b) { b.checked = true; },
        reveal(b) {
          b.shown = true;
          if (b.kind === "open") return;
          b.ans = b.kind === "order" ? b.items.map((text, k) => ({ k, text })) : b.items.map((x) => x.answer);
          b.checked = true;
        },
        reset(b) { b.ans = fresh(b); b.checked = false; b.shown = false; },
      };
    });

    /* ---- words: a themed word list; tap a word to hear it, hide one side to test yourself ---- */
    Alpine.data("words", () => ({
      ...common(), groups: L.groups || [], hideEn: false, hideFr: false, said: 0,
      hero: L.img ? media(ROOT + L.img) : "", alt: L.img_alt || "",   // an optional opening picture
      /* a word with its own file ("audio", in glossary_dir) plays that; the others are numbered clips */
      hear(w) { this.said = w.n; if (w.audio) { stop(); playWord(w.audio); } else this.say(w.n); },
      hearName(name) { if (name) { stop(); playWord(name); } },   // a group heading has a clip too
      /* Quiz: a word is played; choose it among four. "listen_pick": "fr" shows the French spellings instead of the meanings. */
      quiz: false, q: null, asked: 0, total: 0, score: 0, picked: 0, todo: [], show: L.listen_pick === "fr" ? "fr" : "en",
      label(o) { return this.show === "fr" ? o.fr : (o.en || o.fr); },
      pool() { const seen = {}; return this.groups.flatMap((g) => g.words).filter((w) => w.audio && !seen[this.label(w)] && (seen[this.label(w)] = 1)); },
      mix(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; },
      startQuiz() { this.quiz = true; this.todo = this.mix(this.pool()).slice(0, 10); this.total = this.todo.length; this.asked = 0; this.score = 0; this.nextQ(); },
      stopQuiz() { this.quiz = false; this.q = null; stop(); },
      nextQ() {
        this.picked = 0;
        const w = this.todo[this.asked];
        if (!w) { this.q = null; return; }
        this.asked++;
        this.q = { w, opts: this.mix([w, ...this.mix(this.pool().filter((x) => x.n !== w.n)).slice(0, 3)]) };
        this.hear(w);
      },
      choose(o) {
        if (this.picked || !this.q) return;
        this.picked = o.n;
        const right = o.n === this.q.w.n;
        if (right) this.score++;
        setTimeout(() => { if (this.quiz) this.nextQ(); }, right ? 800 : 1800);
      },
      optClass(o) { return !this.picked ? "" : o.n === this.q.w.n ? "btn-on" : o.n === this.picked ? "wl-wrong" : "opacity-40"; },
    }));

    /* ---- hotspots: pictures with dots. Explore them, or be asked a word and tap where it is ---- */
    Alpine.data("hotspots", () => ({
      slides: L.slides || [], i: 0, mode: "explore", pick: null, t: -1, queue: [], done: [], bad: -1, first: 0, missed: false, wait: false, listen: false, last: null,
      get slide() { return this.slides[this.i] || { spots: [] }; },
      get target() { return this.t >= 0 ? this.slide.spots[this.t] : null; },
      src(img) { return media(ROOT + img); },
      hear(p) { if (p && p.audio) playWord(p.audio); },
      go(k) { this.i = Math.max(0, Math.min(this.slides.length - 1, k)); this.pick = null; if (this.mode === "quiz") this.startQuiz(); },
      setMode(m) { this.mode = m; this.pick = null; if (m === "quiz") this.startQuiz(); },
      startQuiz() {
        const q = this.slide.spots.map((_, k) => k);
        for (let a = q.length - 1; a > 0; a--) { const b = Math.floor(Math.random() * (a + 1)); [q[a], q[b]] = [q[b], q[a]]; }
        this.queue = q; this.done = []; this.first = 0; this.last = null; this.wait = false; this.bad = -1;
        this.next();
      },
      next() { this.missed = false; this.t = this.queue.length ? this.queue.shift() : -1; if (this.t >= 0) this.hear(this.target); },
      tap(k) {
        const p = this.slide.spots[k];
        if (this.mode === "explore") { this.pick = p; this.hear(p); return; }
        if (this.t < 0 || this.wait || this.done.includes(k)) return;
        if (k === this.t) {
          this.done.push(k); this.last = p; if (!this.missed) this.first++;
          this.wait = true; setTimeout(() => { this.wait = false; this.next(); }, 800);
        } else {
          this.missed = true; this.bad = k; setTimeout(() => { if (this.bad === k) this.bad = -1; }, 600);
        }
      },
      dotClass(k) {
        if (this.mode === "quiz") return this.done.includes(k) ? "hs-good" : this.bad === k ? "hs-bad" : "";
        return this.pick === this.slide.spots[k] ? "hs-on" : "";
      },
    }));

    /* ---- shadow: listen, then speak along with the voice ---- */
    Alpine.data("shadow", () => ({
      ...common(), chunks: L.chunks || [], mode: 1, loop: 0,
      get noText() { return this.mode === 3; },
      async seq(list, gap) {
        const r = ++this.run; this.busy = true;
        for (const c of list) {
          this.playing = c.n; const d = await play(c.n, this.rate);
          if (r !== this.run) return;
          if (!d) break;
          if (gap) { await sleep((d / this.rate) * 1300 + 400); if (r !== this.run) return; }   // room to repeat the chunk
        }
        this.playing = 0; this.busy = false;
      },
      playAll() { if (this.busy) return this.halt(); this.loop = 0; this.seq(this.chunks, false); },
      echo() { if (this.busy) return this.halt(); this.loop = 0; this.seq(this.chunks, true); },   // voice, gap, voice, gap
      async repeat(c) {
        if (this.loop === c.n) { this.loop = 0; return this.halt(); }
        this.loop = 0;
        this.halt(); const r = ++this.run; this.loop = c.n; this.busy = true;
        for (;;) {
          this.playing = c.n; const d = await play(c.n, this.rate);
          if (r !== this.run) return;
          if (!d) break;
          await sleep((d / this.rate) * 1300 + 400); if (r !== this.run) return;
        }
        this.loop = 0; this.playing = 0; this.busy = false;
      },
    }));

    /* ---- timeline: the tenses on one line. A slider (or a tap, or the arrow keys) moves the marker;
       the panel under it shows the chosen tense with the chosen verb. Data: LESSON.tenses, LESSON.verbs ---- */
    Alpine.data("timeline", () => ({
      tenses: L.tenses || [], verbs: L.verbs || [], verb: (L.verbs || [])[0] || "", i: 0,
      picture: L.img ? media(ROOT + L.img) : "", pictureAlt: L.img_alt || "",
      init() {
        this.pick(location.hash.slice(1) || L.start);
        this.$watch("i", () => { try { history.replaceState(null, "", "#" + this.cur.key); } catch (e) {} });
      },
      get cur() { return this.tenses[this.i] || {}; },
      get form() { return ((this.cur.forms || {})[this.verb] || [])[0] || ""; },
      get gloss() { return ((this.cur.forms || {})[this.verb] || [])[1] || ""; },
      pick(key) { const k = this.tenses.findIndex((t) => t.key === key); if (k >= 0) this.i = k; },
      go(d) { this.i = Math.min(this.tenses.length - 1, Math.max(0, this.i + d)); },
      pos(t) { return "left:" + (t.x || 0) + "%;top:calc(50% + " + (t.dy || 0) + "px)"; },
      label(t) { return "left:" + (t.x || 0) + "%;top:calc(50% + " + ((t.dy || 0) + (t.up ? -50 : 20)) + "px)"; },
      /* "span": [from, to] (percent): a tense that lasts gets a bar through its point. "stem": [from, to] (pixels from the line): a dashed line to a point that sits off the line */
      span(t) { return "left:" + t.span[0] + "%;width:" + (t.span[1] - t.span[0]) + "%;top:calc(50% + " + ((t.dy || 0) - 4) + "px)"; },
      stem(t) { return "left:" + (t.x || 0) + "%;top:calc(50% + " + t.stem[0] + "px);height:" + (t.stem[1] - t.stem[0]) + "px"; },
      fmt(s) {
        const esc = String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return esc.replace(/\*\*(.+?)\*\*/g, '<b class="font-bold text-accent">$1</b>');
      },
    }));

    /* ---- family: a family tree seen by whoever is "moi". Tap a person: what they are for moi; tap again: become them.
       LESSON.people: { id, name, g: "m" | "f", row, x, parents: [id, id] }; LESSON.couples: [[id, id]];
       LESSON.terms: "<link>_<m|f>" -> { fr, ipa, en, stage, audio }; LESSON.stages: what the slider names, ring by ring ---- */
    Alpine.data("family", () => {
      const people = L.people || [], T = L.terms || {}, by = {}, mate = {};
      people.forEach((p) => { by[p.id] = p; });
      (L.couples || []).forEach(([a, b]) => { mate[a] = b; mate[b] = a; });
      const par = (id) => (by[id] && by[id].parents) || [];
      const kids = (id) => people.filter((p) => (p.parents || []).includes(id)).map((p) => p.id);
      const sibs = (id) => people.filter((p) => p.id !== id && par(p.id).some((x) => par(id).includes(x))).map((p) => p.id);
      const mates = (ids) => ids.map((x) => mate[x]).filter(Boolean);
      /* what b is to a: the kind of link, or "" when French has no single word for it */
      function kind(a, b) {
        const pa = par(a), ch = kids(a), sb = sibs(a), sp = mate[a], gp = pa.flatMap(par), gc = ch.flatMap(kids);
        const psib = pa.flatMap(sibs), spsib = sp ? sibs(sp) : [], neph = sb.concat(spsib).flatMap(kids), gpsib = gp.flatMap(sibs);
        const hit = [["parent", pa], ["child", ch], ["sibling", sb], ["spouse", sp ? [sp] : []], ["grandparent", gp], ["grandchild", gc],
          ["greatgrandparent", gp.flatMap(par)], ["greatgrandchild", gc.flatMap(kids)], ["uncle", psib.concat(mates(psib))], ["cousin", psib.flatMap(kids)],
          ["nephew", neph], ["granduncle", gpsib.concat(mates(gpsib))], ["grandnephew", neph.flatMap(kids)],
          ["parent_in_law", sp ? par(sp) : []], ["child_in_law", mates(ch)], ["sibling_in_law", spsib.concat(mates(sb))]].find((t) => t[1].includes(b));
        return hit ? hit[0] : "";
      }
      /* the drawing: x runs from 0 to W across the stage (in card widths), one row per generation */
      const CARD = 88, PITCH = 150, W = Math.max(1, ...people.map((p) => p.x || 0)) + 0.5, rows = Math.max(1, ...people.map((p) => p.row || 1));
      const top = (row) => ((row || 1) - 1) * PITCH, pc = (x) => (x / W * 100).toFixed(3) + "%";
      const flat = (x1, x2, y) => "left:" + pc(Math.min(x1, x2)) + ";width:" + pc(Math.abs(x2 - x1)) + ";top:" + (y - 1) + "px;height:2px";
      const drop = (x, y1, y2) => "left:calc(" + pc(x) + " - 1px);width:2px;top:" + y1 + "px;height:" + (y2 - y1) + "px";
      const lines = (L.couples || []).filter(([a, b]) => by[a] && by[b]).map(([a, b]) => flat(by[a].x, by[b].x, top(by[a].row) + CARD / 2));
      const homes = {};
      people.forEach((p) => { const ps = par(p.id).filter((x) => by[x]); if (ps.length) (homes[ps.slice().sort().join("+")] = homes[ps.slice().sort().join("+")] || { ps, ch: [] }).ch.push(p); });
      Object.values(homes).forEach(({ ps, ch }) => {
        const x = ps.reduce((s, id) => s + by[id].x, 0) / ps.length, row = Math.max(...ps.map((id) => by[id].row));
        const y0 = top(row) + (ps.length > 1 ? CARD / 2 : CARD), bus = top(row) + CARD + (PITCH - CARD) / 2, xs = ch.map((c) => c.x).concat(x);
        lines.push(drop(x, y0, bus), flat(Math.min(...xs), Math.max(...xs), bus));
        ch.forEach((c) => lines.push(drop(c.x, bus, top(c.row))));
      });
      const vowel = (s) => /^[aàâeéèêiîoôuœ]/i.test(s);
      const mix = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
      const start = by[L.start] ? L.start : (people[0] || {}).id || "";
      return {
        people, lines, height: top(rows) + CARD, stages: L.stages || [], stage: 1, start, startName: (by[start] || {}).name || "",
        me: "", pick: "", hide: false, rels: {},
        init() { this.become(start); this.$watch("stage", () => { if (this.quiz) this.startQuiz(); }); },
        get cur() { return this.stages[this.stage - 1] || {}; },
        get meP() { return by[this.me] || {}; },
        term(p) { return (p && T[this.rels[p.id]]) || null; },   // the word for what p is to moi
        shown(p) { const t = this.term(p); return !!t && (t.stage || 1) <= this.stage; },   // is that word within the slider's reach
        poss(t, p) { return (p.g === "f" && !vowel(t.fr) ? "ma " : "mon ") + t.fr; },   // mon arrière-grand-mère: "ma" becomes "mon" before a vowel
        art(t, p) { return (vowel(t.fr) ? "l’" : p.g === "f" ? "la " : "le ") + t.fr; },
        de(name) { return (/^[aeiouyéèh]/i.test(name) ? "d’" : "de ") + name; },
        pos(p) { return "left:" + pc(p.x || 0) + ";top:" + top(p.row) + "px"; },
        word(p) {
          if (p.id === this.me) return "moi";
          if (!this.shown(p)) return "";
          if (this.quiz ? !this.done.includes(p.id) : this.hide) return "• • •";
          return this.poss(this.term(p), p);
        },
        cardClass(p) {
          if (p.id === this.me) return "ft-me";
          const c = [this.shown(p) ? "ft-" + p.g : "ft-dim"];
          if (!this.quiz && p.id === this.pick) c.push("ft-sel");
          if (this.quiz && this.done.includes(p.id)) c.push("ft-good");
          if (this.bad === p.id) c.push("ft-bad");
          return c.join(" ");
        },
        hear(t) { if (t && t.audio) playWord(t.audio); },
        tap(p) {
          if (this.quiz) return this.answer(p);
          if (p.id === this.me) { this.pick = ""; return; }
          if (p.id === this.pick) return this.become(p.id);
          this.pick = p.id;
          this.hear(this.term(p));
        },
        become(id) {
          const r = {};
          people.forEach((p) => { const k = kind(id, p.id); if (k) r[p.id] = k + "_" + p.g; });
          this.me = id; this.pick = ""; this.rels = r;
          this.$nextTick(() => {   // on a narrow screen the tree scrolls sideways: bring moi to the middle
            const s = this.$refs.scroll, el = s && s.querySelector(".ft-me");
            if (el && s.scrollWidth > s.clientWidth) s.scrollTo({ left: el.offsetLeft - s.clientWidth / 2, behavior: "smooth" });
          });
        },
        /* the picked person and moi, said both ways: "Claire est la tante de Léa." / "Léa est la nièce de Claire." */
        get info() {
          const p = by[this.pick], m = this.meP;
          if (!p || p.id === this.me) return null;
          const t = this.term(p), back = T[kind(p.id, m.id) + "_" + m.g];
          return {
            p, t, mine: t ? this.poss(t, p) : "", en: t ? "my " + t.en : "",
            fr1: t ? p.name + " est " + this.art(t, p) + " " + this.de(m.name) + "." : "", en1: t ? p.name + " is " + m.name + "’s " + t.en + "." : "",
            fr2: back ? m.name + " est " + this.art(back, m) + " " + this.de(p.name) + "." : "", en2: back ? m.name + " is " + p.name + "’s " + back.en + "." : "",
          };
        },
        /* Quiz: "Trouvez : la tante de Léa". Tap the person; anyone who is that for moi is right. */
        quiz: false, q: null, todo: [], asked: 0, total: 0, first: 0, missed: false, done: [], bad: "", last: null,
        startQuiz() {
          const keys = [...new Set(people.filter((p) => p.id !== this.me && this.shown(p)).map((p) => this.rels[p.id]))];
          this.quiz = true; this.pick = ""; this.todo = mix(keys); this.total = keys.length; this.asked = 0; this.first = 0; this.done = []; this.last = null;
          this.nextQ();
        },
        stopQuiz() { this.quiz = false; this.q = null; this.done = []; this.last = null; this.bad = ""; },
        nextQ() {
          const key = this.todo[this.asked], p = people.find((x) => this.rels[x.id] === key);
          this.missed = false; this.bad = "";
          if (!key || !p) { this.q = null; return; }
          this.asked++;
          this.q = { key, text: this.art(T[key], p) + " " + this.de(this.meP.name), en: T[key].en, open: true };
        },
        answer(p) {
          const q = this.q;
          if (!q || !q.open || p.id === this.me || this.done.includes(p.id)) return;
          if (this.rels[p.id] !== q.key) { this.missed = true; this.bad = p.id; setTimeout(() => { if (this.bad === p.id) this.bad = ""; }, 400); return; }
          q.open = false;
          if (!this.missed) this.first++;
          this.done = this.done.concat(people.filter((x) => this.rels[x.id] === q.key).map((x) => x.id));
          this.last = { name: p.name, text: q.text, en: q.en };
          this.hear(T[q.key]);
          setTimeout(() => { if (this.quiz && this.q === q) this.nextQ(); }, 900);
        },
      };
    });

    /* ---- quiz: multiple choice with the reason for each answer ---- */
    Alpine.data("quiz", () => ({
      qs: L.questions || [], i: 0, pick: null, score: 0, over: false,
      get q() { return this.qs[this.i] || {}; },
      choose(k) { if (this.pick !== null) return; this.pick = k; if (k === this.q.answer) this.score++; if (this.q.n) play(this.q.n); },
      next() { if (this.i + 1 >= this.qs.length) this.over = true; else { this.i++; this.pick = null; } },
      again() { this.i = 0; this.pick = null; this.score = 0; this.over = false; },
    }));

    /* ---- "done" ticks, kept on this device only (no account) ---- */
    Alpine.data("progress", (id) => ({
      id, on: false,
      init() { try { this.on = !!JSON.parse(localStorage.getItem("done") || "{}")[id]; } catch (e) {} },
      toggle() { this.on = !this.on; try { const d = JSON.parse(localStorage.getItem("done") || "{}"); this.on ? (d[id] = 1) : delete d[id]; localStorage.setItem("done", JSON.stringify(d)); } catch (e) {} },
    }));
  });

  /* index pages: tick the lessons already done on this device */
  document.addEventListener("DOMContentLoaded", () => {
    let d = {}; try { d = JSON.parse(localStorage.getItem("done") || "{}"); } catch (e) {}
    document.querySelectorAll("[data-lesson]").forEach((el) => { if (d[el.dataset.lesson]) el.classList.add("is-done"); });
    /* card pages (expression design): grey out the Play buttons while the audio is pending */
    if (typeof AUD_EXT !== "undefined" && /pending/.test(AUD_EXT)) document.body.classList.add("audio-pending");
  });
})();
