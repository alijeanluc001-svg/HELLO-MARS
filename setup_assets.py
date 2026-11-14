"""Downloads everything the site needs into ./static (run ONCE, with internet).
Usage:  python setup_assets.py [max_tile_zoom]     (default 4 = ~680 tiles, ~20 MB)
Creates: three.min.js, leaflet.js/.css, mars.jpg (3D globe texture), static/tiles (offline 2D map)."""
import os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

LF = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/"
ASSETS = {
    "static/three.min.js": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
    "static/leaflet.js": LF + "leaflet.js",
    "static/leaflet.css": LF + "leaflet.css",
    "static/images/layers.png": LF + "images/layers.png",
    "static/images/layers-2x.png": LF + "images/layers-2x.png",
}
TILE = "https://trek.nasa.gov/tiles/Mars/EQ/Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg"


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print("  FAILED", url, "->", e)
        return False


def stitch(z=3):
    from PIL import Image
    rows, cols = 2 ** z, 2 ** (z + 1)
    w, h = Image.open(f"static/tiles/{z}/0/0.jpg").size
    img = Image.new("RGB", (cols * w, rows * h))
    for y in range(rows):
        for x in range(cols):
            img.paste(Image.open(f"static/tiles/{z}/{y}/{x}.jpg"), (x * w, y * h))
    img.save("static/mars.jpg", quality=90)
    print("  static/mars.jpg", img.size)


if __name__ == "__main__":
    zmax = max(3, int(sys.argv[1])) if len(sys.argv) > 1 else 4
    print("1/3 libraries")
    for p, u in ASSETS.items():
        print("  ", p, "OK" if get(u, p) else "MISSING")
    print("2/3 NASA Trek tiles (zoom 0-%d)" % zmax)
    jobs = [(TILE.format(z=z, y=y, x=x), f"static/tiles/{z}/{y}/{x}.jpg")
            for z in range(zmax + 1) for y in range(2 ** z) for x in range(2 ** (z + 1))]
    with ThreadPoolExecutor(8) as ex:
        ok = sum(ex.map(lambda j: get(*j), jobs))
    print(f"  {ok}/{len(jobs)} tiles")
    print("3/3 globe texture")
    try:
        stitch(3)
    except Exception as e:
        print("  texture skipped:", e, "(pip install pillow, then rerun)")
    print("Done. Now run: python app.py")