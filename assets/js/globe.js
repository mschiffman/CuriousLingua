/* The Earth on the home page: a satellite picture with relief, drifting clouds, an atmosphere and stars.
   The countries of the four courses are lit in their course colours, each with a pulsing marker and a label.
   The globe tours from one to the next (a comet flies between them); drag to turn it; hovering a country, its
   label, a language button or a course tile turns the globe to it; a click or tap on a lit country flies into it
   and opens that course.
   Three.js r128 (assets/vendor/three.min.js). motion.js loads three.min.js and this file online only, after the
   page has loaded, on devices that can take it. Pictures and borders: tools/globe.py.
   Markup (tools/build.py, home()):
     <section data-globe-root>            the dark hero: the canvas fills it
       <canvas data-hero="globe">
       <div data-globe-slot>              the square the globe sits in (it decides position and size)
       <a class="globe-pin" data-globe="<course>" data-course="<course>" href>   one label per course
     anywhere: <a data-globe-link="<course>">   turns the globe to that country on hover / focus
   Longitude 0 faces +x, 90 E faces -z: the same as THREE.SphereGeometry's own texture coordinates. */
window.LangGlobe = async function (canvas, gsap, ScrollTrigger, assets) {
  const THREE = window.THREE, RAD = Math.PI / 180;
  const hero = canvas.closest("[data-globe-root]"), slot = hero.querySelector("[data-globe-slot]");
  const pins = [...hero.querySelectorAll("[data-globe]")];
  const small = Math.min(innerWidth, screen.width) < 768 || (navigator.deviceMemory && navigator.deviceMemory <= 2);
  const url = (p) => new URL(p, assets).href;
  const picture = (p) => new Promise((ok, no) => new THREE.TextureLoader().load(url(p), ok, undefined, no));
  const tag = small ? "1k" : "2k";
  const [map, dayMap, auxMap, normalMap] = await Promise.all([
    fetch(url("data/globe.json")).then((r) => r.json()),
    picture("img/globe/earth-" + tag + ".jpg"), picture("img/globe/aux-" + tag + ".jpg"),
    small ? null : picture("img/globe/normal-2k.jpg").catch(() => null),
  ]);
  const KEYS = Object.keys(map.countries).filter((k) => pins.some((a) => a.dataset.globe === k)).slice(0, 4);
  const SIDE = { jap: 1, kor: -1 };   // Japan and Korea are neighbours: their labels go to either side

  /* ---------- scene. The canvas covers the whole hero; the globe is placed over its slot (layout()). */
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setClearColor(0x000000, 0);
  const FOV = 24, DIST = 10;
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 200);
  camera.position.set(0, 0, DIST);
  const root = new THREE.Group(), globe = new THREE.Group();   // root: place and size; globe: the turning
  root.add(globe); scene.add(root);

  const glowOf = (k) => {   // the bright course colour (--glow, tools/site.src.css), from that course's label
    const el = pins.find((a) => a.dataset.globe === k);
    const v = el ? getComputedStyle(el).getPropertyValue("--glow").trim().split(/\s+/).map(Number) : [];
    return v.length === 3 ? new THREE.Color(v[0] / 255, v[1] / 255, v[2] / 255) : new THREE.Color(0x60a5fa);
  };
  const toXYZ = (lat, lon, r = 1) => {
    const p = lat * RAD, l = lon * RAD;
    return new THREE.Vector3(r * Math.cos(p) * Math.cos(l), r * Math.sin(p), -r * Math.cos(p) * Math.sin(l));
  };
  const facing = (lat, lon, tilt = 0.8) => ({ x: lat * RAD * tilt, y: -Math.PI / 2 - lon * RAD });   // the turn that brings a place to the front
  const SUN = new THREE.Vector3().fromArray(map.sun).normalize();   // fixed to the viewer, so the side we see is always lit

  /* ---------- the countries, painted on a world map (x = longitude, top = north): red, green, blue and yellow.
     Each is a soft ramp across its border (0 outside, 1/2 on the border, 1 inside), so the shader can draw the
     fill, a crisp border and a glow from one picture. The ramp is built from strokes, not canvas blur, so it is
     the same in every browser. */
  const maskMap = (() => {
    const W = small || renderer.capabilities.maxTextureSize < 4096 ? 2048 : 4096, H = W / 2;
    const c = document.createElement("canvas"); c.width = W; c.height = H;
    const x = c.getContext("2d"), INK = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0]], N = 5, half = (W / 4096) * 3.4;
    const rgb = (i, v) => "rgb(" + INK[i].map((on) => Math.round(on * v)).join(",") + ")";
    x.fillStyle = "#000"; x.fillRect(0, 0, W, H);
    x.lineJoin = x.lineCap = "round";
    KEYS.forEach((k, i) => {
      const path = new Path2D();
      map.countries[k].rings.forEach((ring) => {
        ring.forEach(([lon, lat], j) => { const px = ((lon + 180) / 360) * W, py = ((90 - lat) / 180) * H; j ? path.lineTo(px, py) : path.moveTo(px, py); });
        path.closePath();
      });
      x.globalCompositeOperation = "lighter"; x.strokeStyle = rgb(i, 127.5 / N);
      for (let j = 1; j <= N; j++) { x.lineWidth = (2 * half * j) / N; x.stroke(path); }
      x.globalCompositeOperation = "difference"; x.fillStyle = rgb(i, 255); x.fill(path);
    });
    const t = new THREE.CanvasTexture(c);
    t.wrapS = THREE.RepeatWrapping; t.anisotropy = 4;
    return t;
  })();
  dayMap.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  auxMap.wrapS = THREE.RepeatWrapping;

  /* glowing layers (air, stars, comet) add their light and as much opacity as they are bright: with plain additive
     blending they would turn the transparent canvas black around them */
  const GLOW = { transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor };
  const LIGHT = " float lum = max(c.r, max(c.g, c.b)); gl_FragColor = vec4(c, lum);";

  /* ---------- the Earth */
  const COLORS = [0, 1, 2, 3].map((i) => (KEYS[i] ? glowOf(KEYS[i]) : new THREE.Color(0)));
  const U = {
    dayMap: { value: dayMap }, auxMap: { value: auxMap }, normalMap: { value: normalMap }, maskMap: { value: maskMap },
    useNormal: { value: normalMap ? 1 : 0 }, sun: { value: SUN }, time: { value: 0 }, cloudShift: { value: 0 },
    tint: { value: COLORS }, lit: { value: new THREE.Vector4(0, 0, 0, 0) }, hot: { value: new THREE.Vector4(0, 0, 0, 0) },
  };
  const earth = new THREE.Mesh(new THREE.SphereGeometry(1, small ? 64 : 96, small ? 48 : 64), new THREE.ShaderMaterial({
    uniforms: U,
    vertexShader: `
      varying vec2 vUv; varying vec3 vN; varying vec3 vT; varying vec3 vB; varying vec3 vP;
      void main() {
        vUv = uv;
        vec3 n = normalize(position), t = normalize(cross(vec3(0., 1., 0.), n) + vec3(1e-5, 0., 0.)), b = cross(n, t);   // east, north
        vN = normalMatrix * n; vT = normalMatrix * t; vB = normalMatrix * b;
        vec4 mv = modelViewMatrix * vec4(position, 1.);
        vP = mv.xyz; gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      precision highp float;
      uniform sampler2D dayMap, auxMap, normalMap, maskMap;
      uniform float useNormal, time, cloudShift;
      uniform vec3 sun; uniform vec3 tint[4]; uniform vec4 lit, hot;
      varying vec2 vUv; varying vec3 vN; varying vec3 vT; varying vec3 vB; varying vec3 vP;
      /* one course country: m = its ramp, c = its colour, a = how lit (0-1), b = how hot (hover / on tour) */
      void country(float m, vec3 c, float a, float b, inout vec3 col, inout float clear) {
        float fill = smoothstep(.5, .62, m), edge = 1. - smoothstep(0., .3, abs(m - .5)), halo = smoothstep(.02, .5, m) * (1. - fill);
        float beat = .5 + .5 * sin(time * 2.4);
        float g = dot(col, vec3(.299, .587, .114));
        col = mix(col, c * (.25 + 1.5 * g), fill * a * (.42 + .2 * b));          // the land's own light and shade, in the course colour
        col += c * fill * a * (.03 + .1 * b + .05 * beat * b);
        col += mix(c, vec3(1.), .35 + .35 * b) * edge * a * (.75 + .55 * b);
        col += c * halo * a * (.18 + .45 * b);
        clear = max(clear, max(fill, edge) * a);
      }
      void main() {
        vec3 N = normalize(vN), V = normalize(-vP), Nr = N;
        if (useNormal > .5) {
          vec3 nm = texture2D(normalMap, vUv).xyz * 2. - 1.;
          Nr = normalize(normalize(vT) * nm.x * 1.3 + normalize(vB) * nm.y * 1.3 + N * nm.z);
        }
        vec3 aux = texture2D(auxMap, vUv).rgb;
        vec2 cuv = vec2(vUv.x + cloudShift, vUv.y);
        float cloud = texture2D(auxMap, cuv).g, shadow = texture2D(auxMap, cuv + vec2(.0035, -.0025)).g;
        float day = smoothstep(-.25, .9, dot(Nr, sun)), dayFlat = smoothstep(-.25, .9, dot(N, sun));
        vec3 col = texture2D(dayMap, vUv).rgb;
        col = max(mix(vec3(dot(col, vec3(.299, .587, .114))), col, 1.35) * 1.12, 0.);   // a little more vivid than the photograph
        col *= .22 + day;
        col *= 1. - .3 * shadow * (1. - cloud) * dayFlat;                                // the clouds' shadows
        col += vec3(.75, .86, 1.) * pow(max(dot(N, normalize(sun + V)), 0.), 55.) * aux.r * .5;   // the sun on the sea
        vec3 m = texture2D(maskMap, vUv).rgb;
        float y = min(m.r, m.g), clear = 0.;
        country(m.r - y, tint[0], lit.x, hot.x, col, clear);
        country(m.g - y, tint[1], lit.y, hot.y, col, clear);
        country(m.b, tint[2], lit.z, hot.z, col, clear);
        country(y, tint[3], lit.w, hot.w, col, clear);
        col = mix(col, vec3(.3 + .95 * dayFlat), cloud * .9 * (1. - .82 * clear));       // clouds part over the lit countries
        col += vec3(.3, .55, 1.) * pow(1. - max(dot(N, V), 0.), 3.) * (.35 + .65 * dayFlat) * .9;   // the air at the rim
        gl_FragColor = vec4(col, 1.);
      }`,
  }));
  globe.add(earth);

  /* the atmosphere: a larger shell seen from inside, brightest against the Earth's rim, fading outward */
  const AIR = 1.17;
  const air = new THREE.Mesh(new THREE.SphereGeometry(AIR, 64, 48), new THREE.ShaderMaterial({
    uniforms: { sun: { value: SUN }, power: { value: 0 }, edge: { value: Math.sqrt(1 - 1 / (AIR * AIR)) } },
    side: THREE.BackSide, ...GLOW,
    vertexShader: "varying vec3 vN; varying vec3 vP; void main() { vN = normalMatrix * normal; vec4 mv = modelViewMatrix * vec4(position, 1.); vP = mv.xyz; gl_Position = projectionMatrix * mv; }",
    fragmentShader: `
      precision highp float;
      uniform vec3 sun; uniform float power, edge; varying vec3 vN; varying vec3 vP;
      void main() {
        vec3 N = normalize(vN), V = normalize(-vP);
        float g = pow(clamp(-dot(N, V) / edge, 0., 1.), 2.6);
        float side = smoothstep(-.7, .8, dot(normalize(vec3(N.xy, .25)), sun));
        vec3 c = vec3(.25, .52, 1.) * g * (.3 + .8 * side) * power;` + LIGHT + `
      }`,
  }));
  root.add(air);

  /* ---------- stars: soft points far behind, twinkling */
  const starU = { time: { value: 0 }, px: { value: 1 }, show: { value: 0 } };
  const stars = (() => {
    const n = small ? 320 : 900, pos = new Float32Array(n * 3), a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      pos.set([(Math.random() * 2 - 1) * 34, (Math.random() * 2 - 1) * 13, -8 - Math.random() * 30], i * 3);
      a.set([Math.random() < 0.08 ? 2.4 + Math.random() * 1.6 : 0.8 + Math.random() * 1.3, Math.random() * 6.28, 0.4 + Math.random() * 1.6], i * 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("a", new THREE.BufferAttribute(a, 3));
    const p = new THREE.Points(geo, new THREE.ShaderMaterial({
      uniforms: starU, ...GLOW,
      vertexShader: "attribute vec3 a; uniform float time, px; varying float vA; void main() { vA = .55 + .45 * sin(time * a.z + a.y); gl_PointSize = a.x * px; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }",
      fragmentShader: "precision mediump float; uniform float show; varying float vA; void main() { float d = length(gl_PointCoord - .5); vec3 c = vec3(.82, .9, 1.) * smoothstep(.5, .05, d) * vA * show;" + LIGHT + " }",
    }));
    p.frustumCulled = false;
    scene.add(p);
    return p;
  })();

  /* ---------- the four countries: a marker that pulses, and the label that follows it */
  const C = {}, state = { lit: {}, hot: {} };
  KEYS.forEach((k, i) => {
    const d = map.countries[k], [lat, lon] = d.anchor, color = COLORS[i], tag = d.label || d.anchor;
    const at = toXYZ(lat, lon, 1.004), mark = new THREE.Group();
    mark.position.copy(at); mark.lookAt(at.clone().multiplyScalar(2));
    const flat = (geo, c, opacity) => new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide }));
    mark.add(flat(new THREE.CircleGeometry(0.011, 20), 0xffffff, 1));
    const rings = [0, 1].map((j) => {
      const m = flat(new THREE.RingGeometry(0.02, 0.026, 40), color.clone().lerp(new THREE.Color(0xffffff), 0.4), 0);
      mark.add(m);
      gsap.fromTo(m.scale, { x: 1, y: 1 }, { x: 3.6, y: 3.6, duration: 2.6, ease: "power1.out", repeat: -1, delay: j * 1.3 });
      gsap.fromTo(m.material, { opacity: 0.9 }, { opacity: 0, duration: 2.6, ease: "power1.out", repeat: -1, delay: j * 1.3 });
      return m;
    });
    mark.scale.setScalar(0.001);
    globe.add(mark);
    state.lit[k] = 0; state.hot[k] = 0;
    C[k] = { i, lat, lon, at, mark, tagAt: toXYZ(tag[0], tag[1], 1.004), rings, color, pin: pins.find((a) => a.dataset.globe === k),
      boxes: d.rings.map((r) => { let a = 180, b = 90, c = -180, e = -90; r.forEach(([x, y]) => { a = Math.min(a, x); b = Math.min(b, y); c = Math.max(c, x); e = Math.max(e, y); }); return [a, b, c, e]; }),
      rings2: d.rings, tiny: k !== "eng" };
  });
  const heat = (k, on) => {   // the country on tour or under the pointer
    gsap.to(state.hot, { [k]: on ? 1 : 0, duration: on ? 0.45 : 0.8, ease: "power2.out", overwrite: "auto" });
    if (C[k].pin) C[k].pin.classList.toggle("is-on", on);
    hero.querySelectorAll('[data-globe-link="' + k + '"]').forEach((a) => a.classList.toggle("is-on", on));
  };

  /* ---------- a comet from one country to the next along a raised great circle */
  const cometU = { p: { value: 0 }, color: { value: new THREE.Color() } };
  const comet = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.ShaderMaterial({
    uniforms: cometU, ...GLOW,
    vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }",
    fragmentShader: "precision mediump float; uniform float p; uniform vec3 color; varying vec2 vUv; void main() { float d = p - vUv.x; float a = d < 0. ? 0. : exp(-d * 4.5) * smoothstep(0., .03, vUv.x) * smoothstep(1., .97, vUv.x); vec3 c = mix(color, vec3(1.), exp(-d * 30.) * .8) * a * 1.5;" + LIGHT + " }",
  }));
  comet.visible = false;
  globe.add(comet);
  function fly(a, b) {
    const A = a.at.clone().normalize(), B = b.at.clone().normalize(), angle = A.angleTo(B), lift = 0.05 + angle * 0.14, pts = [];
    for (let i = 0; i <= 40; i++) {
      const t = i / 40;
      pts.push(A.clone().multiplyScalar(Math.sin((1 - t) * angle)).add(B.clone().multiplyScalar(Math.sin(t * angle))).normalize().multiplyScalar(1.006 + Math.sin(Math.PI * t) * lift));
    }
    comet.geometry.dispose();
    comet.geometry = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 80, 0.0045, 6, false);
    cometU.color.value.copy(b.color); comet.visible = true;
    gsap.killTweensOf(cometU.p);
    gsap.fromTo(cometU.p, { value: 0 }, { value: 1.9, duration: 2.4, ease: "power2.inOut", onComplete: () => { comet.visible = false; } });
  }

  /* ---------- turning: the tour brings each country to the front; dragging takes over until left alone */
  const start = facing(map.start[0], map.start[1], 1);
  const view = { x: start.x, y: start.y }, pose = { s: 0.7, zoom: 1, pins: 0 };
  const near = (from, to) => from + ((((to - from) % (2 * Math.PI)) + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;   // the short way round
  let step = -1, current = null, turning = null, timer = null, dragging = false, leaving = false;
  function go(k, fromTour) {
    if (!C[k] || leaving) return;
    clearTimeout(timer);
    if (fromTour) timer = setTimeout(next, 5200);
    if (k === current) return;
    const prev = current;
    if (prev) heat(prev, false);
    current = k; heat(k, true);
    if (turning) turning.kill();
    const f = facing(C[k].lat, C[k].lon);
    turning = gsap.to(view, { x: f.x, y: near(view.y, f.y), duration: 2, ease: "power3.inOut" });
    if (prev) fly(C[prev], C[k]);
  }
  function next() { if (!dragging && !leaving) go(KEYS[(step = (step + 1) % KEYS.length)], true); }
  const resume = (ms) => { clearTimeout(timer); if (!leaving) timer = setTimeout(next, ms); };
  const point = (k) => { step = KEYS.indexOf(k); go(k, false); };

  /* ---------- which country is under the pointer: where the ray meets the ball, as lat / lon, against the borders */
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), ball = new THREE.Sphere(), hit = new THREE.Vector3();
  let W = 1, H = 1, unit = 1;   // the hero in pixels; world units per pixel
  const inRing = (x, y, ring) => {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  const inCountry = (c, lon, lat) => c.rings2.some((r, n) => { const b = c.boxes[n]; return lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3] && inRing(lon, lat, r); });
  const NUDGE = [[0, 0], [0.7, 0], [-0.7, 0], [0, 0.6], [0, -0.6]];   // small countries forgive a near miss
  function probe(ev) {   // { on: over the ball, k: the course country there }
    const r = hero.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, 1 - ((ev.clientY - r.top) / r.height) * 2);
    ray.setFromCamera(ndc, camera);
    ball.center.copy(root.position); ball.radius = root.scale.x;
    if (!ray.ray.intersectSphere(ball, hit)) return { on: false, k: null };
    const p = globe.worldToLocal(hit.clone()).normalize();
    const lat = Math.asin(p.y) / RAD, lon = Math.atan2(-p.z, p.x) / RAD;
    for (const [dx, dy] of NUDGE) for (const k of KEYS) if ((!dx && !dy) || C[k].tiny) if (inCountry(C[k], lon + dx, lat + dy)) return { on: true, k };
    return { on: true, k: null };
  }

  /* ---------- the pointer: drag to turn; a click or tap on a lit country flies into it */
  let lastX = 0, lastY = 0, downX = 0, downY = 0, vx = 0, vy = 0, moved = false, pressed = false, hoverK = null;
  const hover = (h) => {
    const k = h.k;
    hero.style.cursor = k ? "pointer" : h.on ? "grab" : "";
    if (k === hoverK) return;
    if (hoverK && hoverK !== current) heat(hoverK, false);
    hoverK = k;
    if (k) { heat(k, true); clearTimeout(timer); } else if (!dragging) resume(2600);
  };
  hero.addEventListener("pointerdown", (ev) => {
    if (leaving || ev.button || ev.target.closest("a, button")) return;
    if (!probe(ev).on) return;
    pressed = true; moved = false; downX = lastX = ev.clientX; downY = lastY = ev.clientY; vx = vy = 0;
    if (ev.pointerType === "mouse") ev.preventDefault();   // no text selection while turning
    try { hero.setPointerCapture(ev.pointerId); } catch (e) {}
  });
  hero.addEventListener("pointermove", (ev) => {
    if (leaving) return;
    if (!pressed) { if (ev.pointerType === "mouse") hover(ev.target.closest("a, button") ? { on: false, k: null } : probe(ev)); return; }
    if (!moved && Math.hypot(ev.clientX - downX, ev.clientY - downY) < 6) return;   // still a tap
    if (!moved) {
      moved = dragging = true; hero.classList.add("is-dragging");
      if (turning) turning.kill();
      gsap.killTweensOf(view); clearTimeout(timer);
      if (current) { heat(current, false); current = null; }
    }
    const s = 1 / Math.max(root.scale.x / unit, 1);   // one radius of drag = one radian
    vx = (ev.clientX - lastX) * s; vy = (ev.clientY - lastY) * s;
    view.y += vx; view.x = Math.max(-1.2, Math.min(1.2, view.x + vy));
    lastX = ev.clientX; lastY = ev.clientY;
  });
  const release = () => {
    dragging = moved = false; hero.classList.remove("is-dragging");
    gsap.to(view, { y: view.y + vx * 14, x: Math.max(-1.2, Math.min(1.2, view.x + vy * 8)), duration: 1.4, ease: "power3.out" });   // it coasts
    resume(6000);
  };
  hero.addEventListener("pointerup", (ev) => {
    if (!pressed) return;
    pressed = false;
    if (moved) return release();
    const k = probe(ev).k;
    if (k && C[k].pin) dive(k, C[k].pin.href);
  });
  hero.addEventListener("pointercancel", () => { if (pressed) { pressed = false; if (moved) release(); } });
  hero.addEventListener("pointerleave", () => { if (!pressed) hover({ on: false, k: null }); });

  document.querySelectorAll("[data-globe], [data-globe-link]").forEach((a) => {
    const k = a.dataset.globe || a.dataset.globeLink;
    if (!C[k]) return;
    a.addEventListener("pointerenter", () => { if (seen) point(k); });
    a.addEventListener("focus", () => { if (seen) point(k); });
    a.addEventListener("pointerleave", () => resume(2600));
    if (hero.contains(a)) a.addEventListener("click", (ev) => {   // inside the hero: fly in first
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button) return;
      ev.preventDefault(); dive(k, a.href);
    });
  });

  /* ---------- flying into a country, then opening its course */
  const veil = document.createElement("div");
  veil.className = "globe-veil"; veil.setAttribute("aria-hidden", "true");
  document.body.appendChild(veil);
  function dive(k, href) {
    if (leaving) return;
    leaving = true; clearTimeout(timer);
    if (current && current !== k) heat(current, false);
    current = k; heat(k, true);
    if (turning) turning.kill();
    gsap.killTweensOf(view);
    hero.classList.add("is-leaving"); hero.style.cursor = "";
    veil.dataset.course = k;
    const f = facing(C[k].lat, C[k].lon, 1);
    gsap.to(view, { x: f.x, y: near(view.y, f.y), duration: 0.7, ease: "power2.inOut" });
    gsap.to(pose, { zoom: 3.4, duration: 0.95, ease: "power3.in" });
    gsap.to(veil, { opacity: 1, duration: 0.4, delay: 0.55, ease: "power1.in", onComplete: () => { window.location.href = href; } });
  }
  addEventListener("pageshow", (ev) => {   // back from the course page: the globe as it was
    if (!ev.persisted) return;
    leaving = false; hero.classList.remove("is-leaving");
    gsap.set(veil, { opacity: 0 }); gsap.to(pose, { zoom: 1, duration: 0.8, ease: "power3.out" });
    resume(1500);
  });

  /* ---------- size and place: the globe sits over its slot, wherever the layout puts that */
  const base = { x: 0, y: 0, s: 1 };
  function layout() {
    const hr = hero.getBoundingClientRect(), sr = slot.getBoundingClientRect();
    if (!hr.width || !hr.height) return;
    W = hr.width; H = hr.height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4.2e6 / (W * H)));   // never more than about 4 million pixels
    renderer.setPixelRatio(dpr); renderer.setSize(W, H, false);
    camera.aspect = W / H; camera.updateProjectionMatrix();
    unit = (2 * DIST * Math.tan((FOV * RAD) / 2)) / H;
    base.x = (sr.left + sr.width / 2 - hr.left - W / 2) * unit;
    base.y = (H / 2 - (sr.top + sr.height / 2 - hr.top)) * unit;
    base.s = (Math.min(sr.width, sr.height) / 2) * 0.86 * unit;   // the same 86% as the still picture (.globe-slot::before)
    starU.px.value = dpr * (small ? 1.5 : 1.25);
  }
  new ResizeObserver(layout).observe(hero);
  layout();

  /* ---------- scroll: the globe falls behind, shrinks and turns as the hero leaves */
  let scroll = 0, eased = 0, mx = 0, my = 0;
  ScrollTrigger.create({ trigger: hero, start: "top top", end: "bottom top", onUpdate: (s) => { scroll = s.progress; } });
  addEventListener("pointermove", (ev) => { mx = (ev.clientX / innerWidth) * 2 - 1; my = (ev.clientY / innerHeight) * 2 - 1; }, { passive: true });

  /* ---------- run only while the hero is on screen */
  let seen = true, looping = false, last = 0, t = 0, live = false;
  const loop = () => { if (!looping) { looping = true; last = performance.now(); requestAnimationFrame(tick); } };
  new IntersectionObserver((e) => { seen = e[0].isIntersecting; if (seen) { loop(); if (live) resume(1800); } else clearTimeout(timer); }).observe(hero);
  const v = new THREE.Vector3(), nrm = new THREE.Vector3(), toCam = new THREE.Vector3();
  function tick(now) {
    if (!seen) { looping = false; return; }
    requestAnimationFrame(tick);
    const dt = Math.min((now - last) / 1000, 0.05) || 0; last = now; t += dt;
    eased += (scroll - eased) * Math.min(1, dt * 8);
    if (!dragging && !current && !leaving && !(turning && turning.isActive())) view.y += dt * 0.07;   // drifts when nothing holds it
    U.time.value = starU.time.value = t; U.cloudShift.value = t * 0.0022;
    KEYS.forEach((k) => {
      U.lit.value.setComponent(C[k].i, state.lit[k]); U.hot.value.setComponent(C[k].i, state.hot[k]);
      C[k].mark.scale.setScalar(Math.max(0.001, state.lit[k] * (1 + 0.35 * state.hot[k])));
    });
    root.position.set(base.x, base.y - eased * H * 0.22 * unit, 0);
    root.scale.setScalar(base.s * pose.s * pose.zoom * (1 - 0.16 * eased));
    globe.rotation.set(view.x, view.y + eased * 0.9, 0, "XYZ");
    stars.position.set(-mx * 0.35, my * 0.2 + eased * 2.2, 0);
    stars.rotation.z = t * 0.004;
    scene.updateMatrixWorld();
    for (const k of KEYS) {   // each label follows its country and fades as it goes round the back
      const c = C[k];
      if (!c.pin) continue;
      v.copy(c.tagAt); globe.localToWorld(v);
      nrm.copy(v).sub(root.position).normalize();
      const front = nrm.dot(toCam.copy(camera.position).sub(v).normalize());
      v.project(camera);
      const x = (v.x * 0.5 + 0.5) * W, y = (-v.y * 0.5 + 0.5) * H, side = SIDE[k] || 0, pw = c.pin.offsetWidth, ph = c.pin.offsetHeight;
      const left = Math.max(8, Math.min(W - pw - 8, side < 0 ? x - pw - 16 : side > 0 ? x + 16 : x - pw / 2));   // never off the edge of a phone
      c.pin.style.transform = "translate3d(" + left.toFixed(1) + "px," + (side ? y - ph / 2 : y - ph - 14).toFixed(1) + "px,0)";
      const o = Math.max(0, Math.min(1, (front - 0.3) * 4)) * pose.pins * (1 - Math.min(1, eased * 2.5));
      c.pin.style.opacity = o.toFixed(2);
      c.pin.style.pointerEvents = o > 0.5 ? "auto" : "none";
    }
    renderer.render(scene, camera);
  }
  loop();

  /* ---------- entrance: stars, the globe swings in, the air lights, the countries switch on one by one, the tour starts */
  hero.classList.add("is-live");
  view.y = start.y + 1.5;
  gsap.to(canvas, { opacity: 1, duration: 1, ease: "power2.out" });
  gsap.to(starU.show, { value: 1, duration: 2.4, ease: "power1.out" });
  gsap.to(pose, { s: 1, duration: 2.2, ease: "power3.out" });
  gsap.to(air.material.uniforms.power, { value: 1, duration: 2.4, delay: 0.3, ease: "power2.out" });
  gsap.to(view, { y: start.y, duration: 2.6, ease: "power3.out" });
  KEYS.forEach((k, i) => gsap.to(state.lit, { [k]: 1, duration: 1.1, delay: 1.1 + i * 0.22, ease: "power2.out" }));
  gsap.to(pose, { pins: 1, duration: 0.9, delay: 1.9, ease: "power2.out" });
  timer = setTimeout(() => { live = true; next(); }, 4200);
  window.__globe = { point, keys: KEYS };
};
