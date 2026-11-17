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
        trLang: L.start_hidden ? "" : langs[0] || "", trOpen: {}, hasScript: all.some((l) => l.romaji), script: "romaji",
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
        main(l) { return l.romaji ? (this.script === "kana" ? l.kana || l.romaji : l.romaji) : l.text; },
        sub(l) { return l.romaji && this.script === "both" ? l.kana : ""; },
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
      (L.glossary || []).forEach((g) => { clips[plain(g.word)] = g.audio || g.word; });
      const clipFor = (t, base) => {
        const w = plain(t), b = base ? plain(base.split(" /")[0]) : "";
        for (const k of [b, w, w.replace(/s$/, ""), w.replace(/e$/, ""), w.replace(/es$/, ""), w.replace(/le$/, "")]) if (k && clips[k]) return clips[k];
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
      const fresh = (b) => (b.kind === "order" ? (b.start || b.items.map((_, i) => i)).map((k) => ({ k, text: b.items[k] })) : b.items ? b.items.map(() => null) : []);
      return {
        blocks: (L.blocks || []).map((b) => ({ ...b, ans: fresh(b), checked: false, shown: false })),
        offline: typeof EMBED !== "undefined", pending, heard: 0,
        async hear(n) { this.heard = n; await play(n); if (this.heard === n) this.heard = 0; },
        url(src) { return media((/^https?:/.test(src) ? "" : BASE) + src); },
        right(b, i) {
          if (b.kind === "order") return b.ans[i].k === i;
          if (b.kind === "cloze") return norm(b.ans[i]) === norm(b.items[i].answer);
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
