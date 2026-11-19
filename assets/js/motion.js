/* Motion layer for every generated page (tools/build.py, frame()). Loaded with defer after
     assets/vendor/gsap.min.js and assets/vendor/ScrollTrigger.min.js.
   - The page head sets <html class="motion">, so [data-reveal] and [data-split] start hidden and never flash.
     If this file does not run within 3 s, the head script takes the class off again.
   - Nothing moves for visitors who ask for reduced motion.
   - Offline single files have no GSAP (tools/offline.py leaves assets/vendor out): this file then only undoes the hiding.
   What it does:
     [data-split]   page titles: the words rise out of a mask
     [data-reveal]  fades up when it scrolls into view, a few at a time
     [data-count]   a number that counts up when it comes into view
     .tile          tilts toward the mouse, with a soft light under the pointer (mouse and trackpad only)
     .btn-primary   leans toward the mouse
     header         gets a shadow once the page is scrolled
     lesson pages   a thin reading-progress bar; a small burst when "Mark as done" is switched on
     canvas[data-hero]  the 3D letters behind the title (assets/js/hero.js + Three.js), loaded after the page */
(function () {
  const html = document.documentElement;
  window.__motion = true;
  /* home page: the header is dark over the hero, and turns to paper once the hero has scrolled away (no GSAP needed) */
  const space = document.querySelector(".space");
  if (space && "IntersectionObserver" in window) {
    new IntersectionObserver((e) => document.body.classList.toggle("past-hero", !e[0].isIntersecting), { rootMargin: "-56px 0px 0px 0px" }).observe(space);
  }
  const g = window.gsap, ST = window.ScrollTrigger;
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!g || !ST || calm || document.body.hasAttribute("data-offline")) { html.classList.remove("motion"); html.classList.add("lite"); return; }
  const slow = !html.classList.contains("motion");   // the head script left the text visible (slow connection): no entrance, only the interactions
  g.registerPlugin(ST);
  const here = document.currentScript ? document.currentScript.src : "";
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const ease = "power3.out";

  /* ---------- page titles: each word rises out of its own mask (text nodes only, so inner spans keep their style) */
  if (!slow) g.utils.toArray("[data-split]").forEach((el) => {
    const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), texts = [];
    while (walk.nextNode()) texts.push(walk.currentNode);
    texts.forEach((t) => {
      const frag = document.createDocumentFragment();
      t.textContent.split(/(\s+)/).forEach((w) => {
        if (!w) return;
        if (/^\s+$/.test(w)) return frag.appendChild(document.createTextNode(w));
        const outer = document.createElement("span"), inner = document.createElement("span");
        outer.className = "split-w"; inner.textContent = w;
        outer.appendChild(inner); frag.appendChild(outer);
      });
      t.parentNode.replaceChild(frag, t);
    });
    g.set(el, { opacity: 1 });
    g.from(el.querySelectorAll(".split-w > span"), { yPercent: 115, rotate: 5, duration: 1.1, ease: "power4.out", stagger: 0.055, delay: 0.05 });
  });

  /* ---------- scroll reveals: whatever is on screen at load cascades in; the rest follows as it scrolls in */
  const items = slow ? [] : g.utils.toArray("[data-reveal]");
  if (items.length) {
    g.set(items, { autoAlpha: 0, y: 28 });
    ST.batch(items, {
      start: "top 94%", once: true,
      onEnter: (batch) => g.to(batch, { autoAlpha: 1, y: 0, duration: 0.8, ease, stagger: 0.07, overwrite: true,
        clearProps: fine ? "opacity,visibility" : "opacity,visibility,transform" }),   // tilt keeps the transform on desktop
    });
  }
  html.classList.remove("motion");   // GSAP holds them hidden now

  /* ---------- numbers that count up */
  if (!slow) g.utils.toArray("[data-count]").forEach((el) => {
    const n = +el.dataset.count, o = { v: 0 };
    if (!n) return;
    el.textContent = "0";
    g.to(o, { v: n, duration: 1.4, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 96%", once: true },
      onUpdate: () => { el.textContent = Math.round(o.v); } });
  });

  /* ---------- tiles: tilt and lift toward the pointer; the light (.tile::before) follows --mx / --my */
  if (fine) {
    html.classList.add("has-tilt");
    g.utils.toArray(".tile").forEach((t) => {
      const rx = g.quickTo(t, "rotationX", { duration: 0.6, ease }), ry = g.quickTo(t, "rotationY", { duration: 0.6, ease });
      const ty = g.quickTo(t, "y", { duration: 0.45, ease });
      t.addEventListener("pointerenter", () => { g.set(t, { transformPerspective: 900 }); ty(-5); });
      t.addEventListener("pointermove", (ev) => {
        const r = t.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        ry((x - 0.5) * 7); rx((0.5 - y) * 7);
        t.style.setProperty("--mx", (x * 100).toFixed(1) + "%"); t.style.setProperty("--my", (y * 100).toFixed(1) + "%");
      });
      t.addEventListener("pointerleave", () => { rx(0); ry(0); ty(0); });
    });

    /* primary buttons lean toward the pointer */
    g.utils.toArray(".btn-primary").forEach((b) => {
      const mx = g.quickTo(b, "x", { duration: 0.5, ease }), my = g.quickTo(b, "y", { duration: 0.5, ease });
      b.addEventListener("pointermove", (ev) => {
        const r = b.getBoundingClientRect();
        mx((ev.clientX - r.left - r.width / 2) * 0.3); my((ev.clientY - r.top - r.height / 2) * 0.4);
      });
      b.addEventListener("pointerleave", () => { mx(0); my(0); });
    });
  }

  /* ---------- home page: the hero text drifts up and fades as it leaves; lines marked [data-draw] draw themselves */
  if (space) {
    g.to(".space-copy", { y: -70, autoAlpha: 0.1, ease: "none", scrollTrigger: { trigger: space, start: "top top", end: "bottom 35%", scrub: 0.4 } });
    g.to(".space-cue", { autoAlpha: 0, ease: "none", scrollTrigger: { trigger: space, start: "top top", end: "+=160", scrub: true } });
  }
  g.utils.toArray("[data-draw]").forEach((el) => {
    const wide = () => el.parentElement.offsetWidth > el.parentElement.offsetHeight;   // a row on desktop, a column on phones
    g.fromTo(el, { scaleX: () => (wide() ? 0 : 1), scaleY: () => (wide() ? 1 : 0) }, { scaleX: 1, scaleY: 1, ease: "none",
      scrollTrigger: { trigger: el.parentElement.parentElement, start: "top 80%", end: "bottom 60%", scrub: 0.5, invalidateOnRefresh: true } });
  });

  /* ---------- header shadow once scrolled */
  const head = document.querySelector("body > header[data-nav]");
  if (head) ST.create({ start: 4, end: "max", onToggle: (s) => head.classList.toggle("is-scrolled", s.isActive) });

  /* ---------- lesson pages: reading progress (not on the one-screen reader, which does not scroll) */
  if (window.LESSON && getComputedStyle(document.body).overflowY !== "hidden") {
    const bar = document.createElement("div");
    bar.className = "scroll-progress"; bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);
    g.to(bar, { scaleX: 1, ease: "none", scrollTrigger: { start: 0, end: "max", scrub: 0.3 } });
  }

  /* ---------- "Mark as done": a small burst of colour when it turns on */
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest('[x-data^="progress"] button');
    if (b) setTimeout(() => { if (b.classList.contains("btn-on")) burst(b); }, 40);   // Alpine sets btn-on just after the click
  });
  function burst(b) {
    const r = b.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const acc = getComputedStyle(b).getPropertyValue("--accent").trim() || "43 74 203";
    const colors = ["rgb(" + acc + ")", "#F2B600", "#1A9FB0", "#3E9A4B", "#E86A92"];
    g.fromTo(b, { scale: 0.9 }, { scale: 1, duration: 0.7, ease: "elastic.out(1, .4)", clearProps: "transform" });
    for (let i = 0; i < 18; i++) {
      const d = document.createElement("span");
      d.className = "burst-dot";
      d.style.cssText = "left:" + cx + "px;top:" + cy + "px;background:" + colors[i % colors.length];
      document.body.appendChild(d);
      const a = (i / 18) * Math.PI * 2 + Math.random() * 0.35, dist = 45 + Math.random() * 55;
      g.fromTo(d, { x: -4, y: -4, scale: 1 }, { x: Math.cos(a) * dist - 4, y: Math.sin(a) * dist - 4 + 10, scale: 0,
        duration: 0.7 + Math.random() * 0.35, ease: "power3.out", onComplete: () => d.remove() });
    }
  }

  /* ---------- 3D: Three.js is ~600 KB, so it loads only after the page, and only where it will run well.
     data-hero="globe" is the home page globe (globe.js); a course key is the letters behind a course title (hero.js).
     Without it, <html class="lite"> leaves the globe's still picture in place; the letters simply never appear. */
  const canvas = document.querySelector("canvas[data-hero]");
  if (canvas && here && heroOk()) {
    const globe = canvas.dataset.hero === "globe";
    const start = () => load(new URL("../vendor/three.min.js", here).href)
      .then(() => load(new URL(globe ? "globe.js" : "hero.js", here).href))
      .then(() => (globe ? window.LangGlobe(canvas, g, ST, new URL("../", here).href) : window.LangHero(canvas, g, ST)))
      .catch(() => html.classList.add("lite"));
    const idle = () => ("requestIdleCallback" in window ? requestIdleCallback(start, { timeout: 1500 }) : setTimeout(start, 300));
    if (document.readyState === "complete") idle(); else addEventListener("load", idle, { once: true });
  } else if (canvas) html.classList.add("lite");
  function heroOk() {
    const c = navigator.connection;
    if (c && (c.saveData || /2g|3g/.test(c.effectiveType || ""))) return false;   // slow or metered data: skip it
    if (navigator.deviceMemory && navigator.deviceMemory < 2) return false;
    return "WebGLRenderingContext" in window;
  }
  function load(src) {
    return new Promise((ok, no) => {
      const s = document.createElement("script");
      s.src = src; s.onload = ok; s.onerror = no;
      document.head.appendChild(s);
    });
  }

  if (document.fonts) document.fonts.ready.then(() => ST.refresh());   // positions shift once the web fonts arrive
})();
