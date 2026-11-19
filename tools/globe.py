"""Prepares everything the home page globe (assets/js/globe.js) loads.

    python tools/globe.py

Reads the source files in _archive/globe-src/ (downloaded when missing; that folder is not in git):
  earth_atmos_2048.jpg, earth_specular_2048.jpg, earth_normal_2048.jpg, clouds.png   three.js r128, examples/textures/planets
  ne_50m.geojson                                                                    Natural Earth 1:50m countries (public domain)
A sharper Earth picture can replace earth_atmos_2048.jpg: any 2:1 world map with longitude -180 at its left edge.

Writes:
  assets/img/globe/earth-2k.jpg, earth-1k.jpg     the Earth's surface (the small one is for phones)
  assets/img/globe/aux-2k.jpg, aux-1k.jpg         red = where the sea shines, green = the clouds
  assets/img/globe/normal-2k.jpg                  the mountains' relief (large screens only)
  assets/img/globe/poster.webp                    a still picture of the globe: shown until the 3D one is ready,
                                                  and instead of it for reduced motion or slow connections
  assets/data/globe.json                          for each course, its country's borders ([lon, lat] rings),
                                                  its marker ("anchor") and its label ("label"), both [lat, lon]
Only needs running again to change which countries light up (HIGHLIGHT) or the pictures. Needs Pillow.
"""
import json, math, os, shutil, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from PIL import Image

SRC = os.path.join(lib.ROOT, "_archive", "globe-src")
OUT = os.path.join(lib.ROOT, "assets", "img", "globe")
THREE = "https://raw.githubusercontent.com/mrdoob/three.js/r128/examples/textures/planets/"
SOURCES = {
    "earth_atmos_2048.jpg": THREE + "earth_atmos_2048.jpg",
    "earth_specular_2048.jpg": THREE + "earth_specular_2048.jpg",
    "earth_normal_2048.jpg": THREE + "earth_normal_2048.jpg",
    "clouds.png": THREE + "earth_clouds_1024.png",
    "ne_50m.geojson": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson",
}
HIGHLIGHT = {"FRA": "fr", "USA": "eng", "JPN": "jap", "KOR": "kor"}   # Natural Earth ADM0_A3 -> course
ANCHOR = {"fr": [46.6, 2.4], "eng": [39.5, -98.5], "jap": [36.2, 138.3], "kor": [36.3, 127.9]}   # [lat, lon]
LABEL = {"eng": [50.5, -99.0]}   # [lat, lon] where a label sits when not on the anchor: above a large country, not on it
EPS = {"fr": 0.02, "eng": 0.035, "jap": 0.02, "kor": 0.012}   # degrees: how much border detail is dropped
POSTER = (28.0, -40.0, 720)   # the still picture: centre lat, centre lon, size in pixels (must match START in globe.js)
SUN = (-0.52, 0.42, 0.74)     # light from the upper left, toward the viewer (the same in globe.js)


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for name, url in SOURCES.items():
        path = os.path.join(SRC, name)
        if not os.path.exists(path):
            print("downloading", name)
            with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
                shutil.copyfileobj(r, f)


# ------------------------------------------------------------------ borders
def simplify(ring, eps):
    """Douglas-Peucker, without recursion."""
    if len(ring) < 5:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = ring[a][:2], ring[b][:2]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-12
        best, at = 0.0, None
        for i in range(a + 1, b):
            x, y = ring[i][:2]
            d = abs(dy * (x - x1) - dx * (y - y1)) / n if n > 1e-9 else math.hypot(x - x1, y - y1)
            if d > best:
                best, at = d, i
        if at is not None and best > eps:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(ring, keep) if k]


def wanted(code, ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    if code == "FRA":   # only France in Europe (Natural Earth's France also holds Guiana, Réunion...)
        return -10 < sum(xs) / len(xs) < 12 and min(ys) > 40
    return True


def borders():
    data = json.load(open(os.path.join(SRC, "ne_50m.geojson"), encoding="utf-8"))
    out = {}
    for f in data["features"]:
        code = f["properties"].get("ADM0_A3")
        k = HIGHLIGHT.get(code)
        if not k:
            continue
        g = f["geometry"]
        rings = []
        for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            ring = poly[0]   # outer ring; lakes are not cut out
            if not wanted(code, ring):
                continue
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 0.004:   # specks
                continue
            ring = simplify(ring, EPS[k])
            if len(ring) >= 4:
                rings.append([[round(p[0], 3), round(p[1], 3)] for p in ring])
        rings.sort(key=len, reverse=True)
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        out[k] = {"anchor": ANCHOR[k], "label": LABEL.get(k, ANCHOR[k]), "rings": rings}
        print(f"  {k}: {len(rings)} rings, {sum(len(r) for r in rings)} points, lon {min(xs):.1f}..{max(xs):.1f}, lat {min(ys):.1f}..{max(ys):.1f}")
    out = {k: out[k] for k in HIGHLIGHT.values()}
    path = os.path.join(lib.ROOT, "assets", "data", "globe.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"sun": SUN, "start": POSTER[:2], "countries": out}, fh, separators=(",", ":"))
    print(f"globe.json {os.path.getsize(path) / 1024:.0f} KB")


# ------------------------------------------------------------------ pictures
def pictures():
    os.makedirs(OUT, exist_ok=True)
    day = Image.open(os.path.join(SRC, "earth_atmos_2048.jpg")).convert("RGB")
    if day.size[0] != 2 * day.size[1]:
        sys.exit("The Earth picture must be twice as wide as it is high.")
    spec = Image.open(os.path.join(SRC, "earth_specular_2048.jpg")).convert("L")
    cl = Image.open(os.path.join(SRC, "clouds.png")).convert("RGBA")
    clouds = Image.composite(cl.convert("L"), Image.new("L", cl.size, 0), cl.getchannel("A"))   # white clouds x their opacity
    for tag, w in (("2k", 2048), ("1k", 1024)):
        size = (w, w // 2)
        day.resize(size, Image.LANCZOS).save(os.path.join(OUT, f"earth-{tag}.jpg"), quality=86 if w > 1024 else 82, optimize=True, progressive=True)
        aux = Image.merge("RGB", (spec.resize(size, Image.LANCZOS), clouds.resize(size, Image.LANCZOS), Image.new("L", size, 0)))
        aux.save(os.path.join(OUT, f"aux-{tag}.jpg"), quality=80, subsampling=0, optimize=True)   # 4:4:4, so the two channels stay apart
    Image.open(os.path.join(SRC, "earth_normal_2048.jpg")).convert("RGB").save(os.path.join(OUT, "normal-2k.jpg"), quality=78, optimize=True)
    poster(day.resize((1024, 512), Image.LANCZOS), clouds.resize((1024, 512), Image.LANCZOS))
    for f in sorted(os.listdir(OUT)):
        print(f"  {f}: {os.path.getsize(os.path.join(OUT, f)) / 1024:.0f} KB")


def poster(day, clouds):
    """The globe seen from far away (orthographic), lit like the 3D one. Plain Python: takes a few seconds."""
    lat0, lon0, n = math.radians(POSTER[0]), math.radians(POSTER[1]), POSTER[2]
    W, H = day.size
    dpx, cpx = day.load(), clouds.load()
    sl, cl0 = math.sin(lat0), math.cos(lat0)
    sn = math.sqrt(sum(v * v for v in SUN))
    sun = [v / sn for v in SUN]
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = img.load()
    r = n / 2
    for j in range(n):
        y = (r - j - 0.5) / r
        for i in range(n):
            x = (i + 0.5 - r) / r
            rho2 = x * x + y * y
            if rho2 >= 1:
                continue
            rho = math.sqrt(rho2)
            z = math.sqrt(1 - rho2)
            if rho < 1e-9:
                lat, lon = lat0, lon0
            else:
                c = math.asin(rho)
                sc, cc = rho, z
                lat = math.asin(max(-1, min(1, cc * sl + y * sc * cl0 / rho)))
                lon = lon0 + math.atan2(x * sc, rho * cc * cl0 - y * sc * sl)
            u = (math.degrees(lon) + 180) / 360 % 1 * W
            v = (90 - math.degrees(lat)) / 180 * H
            ui, vi = int(u) % W, min(H - 1, max(0, int(v)))
            cr, cg, cb = dpx[ui, vi]
            cloud = cpx[ui, vi] / 255
            grey = 0.299 * cr + 0.587 * cg + 0.114 * cb
            col = [max(0.0, (grey + (ch - grey) * 1.35) * 1.12) for ch in (cr, cg, cb)]
            d = x * sun[0] + y * sun[1] + z * sun[2]
            lit = max(0.0, min(1.0, (d + 0.25) / 1.15))
            lit = lit * lit * (3 - 2 * lit)
            col = [ch * (0.22 + lit) for ch in col]
            white = 255 * (0.3 + 0.95 * lit)
            col = [ch + (white - ch) * cloud * 0.9 for ch in col]
            rim = (1 - z) ** 3 * (0.35 + 0.65 * lit) * 0.9
            col = [ch + 255 * t * rim for ch, t in zip(col, (0.3, 0.55, 1.0))]
            a = min(1.0, (1 - rho) * r)   # a soft pixel at the edge
            px[i, j] = (min(255, int(col[0])), min(255, int(col[1])), min(255, int(col[2])), int(255 * a))
    img.save(os.path.join(OUT, "poster.webp"), quality=82, method=6)


if __name__ == "__main__":
    fetch()
    borders()
    pictures()
