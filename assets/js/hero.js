/* The 3D background behind the page title: letters and short words of the course's languages, drifting
   upward in depth. They lean with the mouse, glow when the pointer is over one, and the camera flies
   into them as the title scrolls away.
   Three.js r128 (assets/vendor/three.min.js). motion.js loads both files online only, after the page has
   loaded, on devices that can take it. <canvas data-hero="fr|eng|jap|kor|all"> picks the letters;
   the colours are each course's --accent (tools/site.src.css). */
window.LangHero = async function (canvas, gsap, ScrollTrigger) {
  const THREE = window.THREE, box = canvas.parentElement;
  const SETS = {
    fr: ["é", "è", "à", "ç", "ê", "ô", "œ", "ù", "ï", "«", "»", "A", "R", "M", "bonjour", "merci", "oui", "café", "rêve", "voilà"],
    eng: ["A", "b", "C", "d", "e", "G", "h", "k", "m", "Q", "s", "w", "z", "hello", "cat", "sun", "book", "play", "က", "မ", "သ", "အ", "ခ"],
    jap: ["あ", "い", "う", "か", "の", "ん", "さ", "ア", "カ", "ネ", "日", "本", "語", "話", "山", "こんにちは", "ありがとう"],
    kor: ["가", "나", "다", "한", "글", "말", "ㄱ", "ㄴ", "ㅎ", "ㅏ", "ㅗ", "사랑", "안녕", "감사"],
  };
  const FONT = '"Fraunces", "Noto Sans Myanmar", "Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Serif KR", Georgia, serif';
  const which = canvas.dataset.hero, keys = SETS[which] ? [which] : Object.keys(SETS);
  const small = innerWidth < 640, N = small ? 30 : 70;

  /* the page's own fonts must be ready before the letters are painted into textures */
  if (document.fonts) {
    await Promise.all([
      document.fonts.load('600 64px "Fraunces"', "A"), document.fonts.load('italic 400 64px "Fraunces"', "a"),
      document.fonts.load('400 64px "Noto Sans Myanmar"', "က"),
    ]).catch(() => {});
  }

  const accent = (k) => {   // "43 74 203" from any element of that course (the nav links carry data-course)
    const el = document.querySelector('[data-course="' + k + '"]');
    const v = el ? getComputedStyle(el).getPropertyValue("--accent").trim().split(/\s+/).map(Number) : [];
    return v.length === 3 ? new THREE.Color(v[0] / 255, v[1] / 255, v[2] / 255) : new THREE.Color(0x2b4acb);
  };
  const INK = new THREE.Color(0x1e2330);

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(50, 2, 0.1, 100);
  const CAM_Z = 20;
  camera.position.set(0, 0, CAM_Z);

  /* one texture per text, white, tinted by the sprite colour */
  const cache = {};
  function texture(text) {
    if (cache[text]) return cache[text];
    const latin = /^[\u0000-ɏ]+$/.test(text), word = text.length > 2;
    const px = 128, font = (latin && word ? "italic 400 " : latin ? "600 " : "400 ") + px + "px " + FONT;
    const c = document.createElement("canvas"), x = c.getContext("2d");
    x.font = font;
    const w = Math.ceil(x.measureText(text).width + px * 0.5), h = Math.ceil(px * 1.7);
    c.width = w; c.height = h;
    x.font = font; x.textAlign = "center"; x.textBaseline = "middle"; x.fillStyle = "#fff";
    x.fillText(text, w / 2, h / 2);
    const map = new THREE.CanvasTexture(c);
    map.minFilter = THREE.LinearFilter; map.generateMipmaps = false;   // no power-of-two resize in WebGL 1
    return (cache[text] = { map, aspect: w / h });
  }

  const halfH = (d) => Math.tan((camera.fov * Math.PI) / 360) * d;   // half the visible height at distance d
  const sprites = [];
  for (let i = 0; i < N; i++) {
    const k = keys[i % keys.length], set = SETS[k], text = set[(Math.random() * set.length) | 0], tex = texture(text);
    const mat = new THREE.SpriteMaterial({ map: tex.map, transparent: true, depthWrite: false, opacity: 0,
      color: Math.random() < 0.2 ? INK : accent(k) });
    const s = new THREE.Sprite(mat), z = -32 + Math.random() * 34, hh = halfH(CAM_Z - z) * 1.15;
    const size = (text.length > 2 ? 2.1 : 3.6) * (0.6 + Math.random() * 0.8);
    s.position.set((Math.random() * 2 - 1) * hh * 2.2, (Math.random() * 2 - 1) * hh, z);
    s.userData = { base: 0.14 + Math.random() * 0.3, hh, size, aspect: tex.aspect, speed: 0.15 + Math.random() * 0.35,
      phase: Math.random() * 6.28, sway: 0.2 + Math.random() * 0.4, show: 0, boost: 0 };
    scene.add(s); sprites.push(s);
    gsap.to(s.userData, { show: 1, duration: 1.4, delay: 0.2 + Math.random() * 1.4, ease: "power2.out" });
  }

  /* pointer: parallax for the camera, and which letter is under it */
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  const canHover = matchMedia("(hover: hover)").matches;   // touch screens: no hover glow
  let px = 0, py = 0, inside = false, hovered = null;
  addEventListener("pointermove", (ev) => {
    const r = canvas.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
    inside = x >= 0 && x <= 1 && y >= 0 && y <= 1;
    px = Math.max(-1, Math.min(1, x * 2 - 1)); py = Math.max(-1, Math.min(1, y * 2 - 1));
    ndc.set(x * 2 - 1, 1 - y * 2);
  }, { passive: true });
  function hover() {
    let hit = null;
    if (inside && canHover) {
      ray.setFromCamera(ndc, camera);
      try { hit = (ray.intersectObjects(sprites)[0] || {}).object || null; } catch (e) { hit = null; }
    }
    if (hit === hovered) return;
    if (hovered) gsap.to(hovered.userData, { boost: 0, duration: 0.6, ease: "power2.out" });
    if (hit) gsap.to(hit.userData, { boost: 1, duration: 0.35, ease: "back.out(2)" });
    hovered = hit;
  }

  /* scroll: the camera moves into the letters as the title leaves the screen */
  let fly = 0;
  ScrollTrigger.create({ trigger: box, start: "top top", end: "bottom top", onUpdate: (s) => { fly = s.progress; } });

  /* run only while the title is on screen (requestAnimationFrame already stops in hidden tabs) */
  let seen = true, looping = false, last = 0, t = 0, frame = 0;
  function loop() {
    if (looping) return;
    looping = true; last = performance.now();
    requestAnimationFrame(tick);
  }
  new IntersectionObserver((e) => { seen = e[0].isIntersecting; if (seen) loop(); }).observe(box);

  function resize() {
    const w = box.clientWidth, h = box.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(box);
  resize();

  function tick(now) {
    if (!seen) { looping = false; return; }
    requestAnimationFrame(tick);
    const dt = Math.min((now - last) / 1000, 0.05) || 0;
    last = now; t += dt;
    camera.position.x += (px * 1.6 - camera.position.x) * 0.04;
    camera.position.y += (-py * 1.0 - camera.position.y) * 0.04;
    camera.position.z += (CAM_Z - fly * 10 - camera.position.z) * 0.08;
    camera.lookAt(0, 0, -15);
    if (++frame % 3 === 0) hover();
    for (const s of sprites) {
      const u = s.userData, p = s.position;
      p.y += u.speed * dt;
      if (p.y > u.hh + 2) p.y = -u.hh - 2;
      p.x += Math.sin(t * 0.3 + u.phase) * u.sway * dt;
      s.material.rotation = Math.sin(t * 0.4 + u.phase) * 0.15;
      const d = camera.position.z - p.z;
      const fade = Math.min(1, Math.max(0, (62 - d) / 30)) * Math.min(1, Math.max(0, (d - 2) / 6));   // fade far away and very close
      s.material.opacity = (u.base + (0.95 - u.base) * u.boost) * fade * u.show;
      const k = u.size * (1 + u.boost * 0.45);
      s.scale.set(k * u.aspect, k, 1);
    }
    renderer.render(scene, camera);
  }
  loop();
  gsap.to(canvas, { opacity: 1, duration: 1.4, ease: "power2.out" });
};
