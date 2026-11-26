/* ---------------------------------------------------------------
   Generic expression-flashcard engine (fr/expression/<topic>.html).
   Expects the page to define, before loading this script:
     AUD_DIR, AUD_EXT, categories
   Each card is [French, English, note, exFR, exEN, exFR, exEN, ...]:
   any number of example pairs, shown under the note in the note popup.
   The note may be "" when the examples say enough on their own.

   Explanation languages. A page may also define
     langs = ["my", "es", "fr"]   the languages a visitor can choose; the first is the one the cards are written in
     COURSE = "eng"               the choice is remembered per course
   A card then ends with one more item, the other languages:
     [..., { es: [meaning, note, example 1 translated, example 2 translated, ...], fr: [...] }]
   and a category may hold  tr: { es: "title" }  or  tr: { es: ["title", "description"] }.
   Whatever a card or a category does not have in the chosen language is shown in the first one.
   (see the per-page <script> block for the data shape), plus
   <div id="cards"></div> and an optional <span id="count"></span>.
   The hamburger menu is separate (nav-expression-flash.js), so offline
   single-file builds (fr/expression/build_single.py) can leave it out.
--------------------------------------------------------------- */
(function () {
  /* Offline single-file builds define EMBED = { "<url>": dataURI };
     online pages don't, so this falls back to the plain URL. */
  const media = (url) => (typeof EMBED !== "undefined" && EMBED[url]) || url;

  const esc = (s) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  // French puts a space before ! ? ; : and inside « » — make it a narrow
  // no-break space so the mark never wraps onto a line of its own.
  const frSpace = (s) =>
    s.replace(/ ([!?;:»])/g, "\u202F$1").replace(/« /g, "«\u202F");

  // Either line of a card may mark its swappable part with
  // <span class=gray>…</span>; everything else in it stays escaped.
  const phrase = (s) =>
    esc(s).replace(
      /&lt;span class=gray&gt;(.*?)&lt;\/span&gt;/g,
      '<span class="gray">$1</span>',
    );

  // On the English pages the second line is Burmese: tag it lang="my"
  // (pimsleur.css colors it blue).
  const BURMESE = /[က-႟]/;

  const SPEAKER = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>`;
  const CLIPBOARD = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>`;

  // Explanation languages: the page's `langs`, the visitor's last choice for this course, else the first.
  const LANGS = typeof langs !== "undefined" && Array.isArray(langs) ? langs : [];
  const NAMES = { my: "မြန်မာ", en: "English", es: "Español", fr: "Français" };
  const KEY = "explain:" + (typeof COURSE !== "undefined" ? COURSE : "");
  let lang = LANGS[0] || "";
  try {
    const saved = localStorage.getItem(KEY);
    if (LANGS.includes(saved)) lang = saved;
  } catch (e) {}
  const other = () => LANGS.length > 1 && lang !== LANGS[0];   // a language other than the one the cards are written in
  const isObj = (x) => x && typeof x === "object" && !Array.isArray(x);

  // Audio files are numbered 01, 02, … in reading order across all categories.
  let audioNum = 0;
  const pad = (n) => String(n).padStart(2, "0");

  const card = (c) => {
    const more = isObj(c[c.length - 1]) ? c[c.length - 1] : null;
    const [fr, en0, note0, ...ex] = more ? c.slice(0, -1) : c;
    const t = (more && other() && more[lang]) || [];   // [meaning, note, example translations…] in the chosen language
    const en = t[0] || en0, note = t[1] != null ? t[1] : note0;
    const examples = [];
    for (let i = 0; i < ex.length; i += 2) examples.push(`${ex[i]}\n${t[2 + i / 2] || ex[i + 1] || ""}`);
    const popup = [note, ...examples].filter(Boolean).join("\n\n");
    return `
    <div class="card p-5 flex items-center gap-4 shadow-md">
      <button class="sound-btn" data-audio="${esc(`${AUD_DIR}${pad(++audioNum)}.${AUD_EXT}`)}" title="Play audio">${SPEAKER}</button>
      <div class="flex-1 min-w-0">
        <p class="phrase text-lg mb-1" lang="fr">${phrase(frSpace(fr))}</p>
        <p class="english"${BURMESE.test(en) ? ' lang="my"' : ""}>${phrase(en)}</p>
      </div>
      <div class="note-wrapper note-multiline" data-note="${esc(frSpace(popup))}">
        <button class="note-btn" title="Notes" aria-label="Notes">${CLIPBOARD}</button>
      </div>
    </div>`;
  };

  // A heading has two titles. On the English pages the second is in the explanation language (cat.my): that one
  // changes. On the other pages the second is in the language being learned (cat.fr): there the first one changes.
  const section = (cat, i) => {
    const tr = (other() && cat.tr && cat.tr[lang]) || null;
    const [title, desc] = Array.isArray(tr) ? tr : [tr, null];
    const first = title && cat.fr != null ? title : cat.en;
    const second = title && cat.fr == null ? title : (cat.fr ?? cat.my ?? "");
    return `
    <div class="${i ? "mt-14 " : ""}mb-6">
      <h2 class="text-3xl font-bold" style="font-family: 'Playfair Display', 'Noto Sans Myanmar', serif; color: white">
        ${esc(first)}
        <span class="text-xl" style="color: var(--cyan); opacity: 0.85; font-style: italic">· ${esc(second)}</span>
      </h2>
      <p class="mt-1 text-sm" style="color: rgba(255, 255, 255, 0.55); font-family: 'Roboto', 'Noto Sans Myanmar', sans-serif">${esc(desc || cat.desc)}</p>
      <div class="header-line w-48 mt-3"></div>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">${cat.cards.map(card).join("")}
    </div>`;
  };

  const draw = () => {
    audioNum = 0;
    document.getElementById("cards").innerHTML = categories.map(section).join("");
  };
  draw();

  // The chooser, in the page's <div id="explain">: only on pages with more than one explanation language.
  const slot = document.getElementById("explain");
  if (slot && LANGS.length > 1) {
    slot.innerHTML = `<label class="explain"><span>Explanations in</span><select aria-label="Explanation language">${LANGS.map(
      (k) => `<option value="${esc(k)}"${k === lang ? " selected" : ""}>${esc(NAMES[k] || k)}</option>`,
    ).join("")}</select></label>`;
    slot.querySelector("select").addEventListener("change", (e) => {
      lang = e.target.value;
      try {
        localStorage.setItem(KEY, lang);
      } catch (err) {}
      if (playing) playing.pause();
      draw();
      document.dispatchEvent(new CustomEvent("explain:change", { detail: lang }));   // expression-quiz.js follows
    });
  }

  // One clip at a time: a new click stops whatever is still playing. (The cards are redrawn when the explanation
  // language changes, so the click is caught on the page, not on each button.)
  let playing = null;
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".sound-btn");
    if (!btn) return;
    if (playing) playing.pause();
    playing = new Audio(media(btn.dataset.audio));
    playing.play();
  });

  // Notes open on hover (pimsleur.css) and also on click/tap, so they work
  // on touch screens and from the keyboard. Clicking elsewhere closes them.
  document.addEventListener("click", (e) => {
    const wrapper = e.target.closest(".note-btn")?.parentElement;
    document.querySelectorAll(".note-wrapper.show").forEach((w) => {
      if (w !== wrapper) w.classList.remove("show");
    });
    if (wrapper) wrapper.classList.toggle("show");
  });

  const count = document.getElementById("count");
  if (count) {
    count.textContent = categories.reduce((n, c) => n + c.cards.length, 0);
  }
})();
