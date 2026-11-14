from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)
R = 3389.5  # rayon moyen de Mars (km, NASA Mars Fact Sheet)
MARS = {"radius_km": R, "area_mkm2": 144.8, "gravity": 3.71, "sol_h": 24.66, "temp_c": -63,
        "pressure_pa": 610, "delay_min": [3, 22], "dose_msv_day": 0.67}  # dose mesurée par RAD (Curiosity)

# id, nom, mission, lat, lon (est), type
_S = [
    ("jezero", "Jezero Crater", "Perseverance 2021", 18.4446, 77.4509, "landing"),
    ("gale", "Gale Crater", "Curiosity 2012", -4.5895, 137.4417, "landing"),
    ("elysium", "Elysium Planitia", "InSight 2018", 4.50, 135.62, "landing"),
    ("meridiani", "Meridiani Planum", "Opportunity 2004", -1.9483, 354.4734, "landing"),
    ("gusev", "Gusev Crater", "Spirit 2004", -14.5718, 175.4785, "landing"),
    ("viking1", "Chryse Planitia", "Viking 1 - 1976", 22.27, 312.05, "landing"),
    ("viking2", "Utopia Planitia", "Viking 2 - 1976", 47.96, 225.74, "landing"),
    ("pathfinder", "Ares Vallis", "Pathfinder 1997", 19.13, 326.75, "landing"),
    ("phoenix", "Vastitas Borealis", "Phoenix 2008", 68.22, 234.25, "landing"),
    ("zhurong", "Utopia Planitia", "Tianwen-1 / Zhurong 2021 (CNSA)", 25.07, 109.93, "landing"),
    ("oxia", "Oxia Planum", "ExoMars (prévu)", 18.2, 335.45, "future"),
    ("olympus", "Olympus Mons", "Volcan, 21,9 km de haut", 18.65, 226.2, "landmark"),
    ("valles", "Valles Marineris", "Canyon, ~4000 km", -14.0, 301.0, "landmark"),
    ("hellas", "Hellas Planitia", "Bassin d'impact, ~7 km de profondeur", -42.7, 70.0, "landmark"),
]
SITES = [dict(zip(("id", "name", "mission", "lat", "lon", "type"), s)) for s in _S]
SC = [(s[3], s[4]) for s in _S]
PROFILES = {"sentinel": (3, 0), "discovery": (2.5, 1), "fortress": (10, 0), "sprint": (0, 0)}  # (poids du danger, bonus science)
TYPES = ["SLOPE", "ROCKS", "DUNES", "CLIFF"]


def vec(la, lo):
    a, b = math.radians(la), math.radians(lo)
    return [math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)]


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def latlon(v):
    x, y, z = unit(v)
    return math.degrees(math.asin(z)), math.degrees(math.atan2(y, x)) % 360


def ang(a, b):
    return math.acos(max(-1, min(1, sum(i * j for i, j in zip(a, b)))))


def dist(p, q):
    return R * ang(vec(*p[:2]), vec(*q[:2]))


def hz(la, lo):
    """Danger 0-1. MODELE SIMULE : à remplacer par la pente MOLA / HiRISE."""
    a, b = math.radians(la), math.radians(lo)
    v = .46 + .3 * math.sin(31 * a + 7 * b) + .24 * math.sin(37 * b - 19 * a + 1) + .15 * math.sin(53 * a + 41 * b)
    return max(0, min(1, v))


def plan(A, B, w, bonus):
    """Couloir le long du grand cercle A->B ; programmation dynamique sur le décalage latéral."""
    a, b = vec(*A), vec(*B)
    om = ang(a, b)
    if om < 1e-4 or om > 3.1:
        return [(*A, hz(*A)), (*B, hz(*B))]
    d = om * R
    n, K = max(8, min(80, int(d / 25) + 8)), 11
    m = K // 2
    dev = min(.2 * d, 450)
    nv = unit([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])
    grid = []
    for i in range(n + 1):
        f, row = i / n, []
        for j in range(K):
            o = (j - m) / m * dev if 0 < i < n else 0
            p = [(math.sin((1 - f) * om) * a[c] + math.sin(f * om) * b[c]) / math.sin(om) + o / R * nv[c] for c in range(3)]
            la, lo = latlon(p)
            row.append((la, lo, hz(la, lo)))
        grid.append(row)
    INF = 1e18
    cost = [[INF] * K for _ in range(n + 1)]
    prev = [[m] * K for _ in range(n + 1)]
    cost[0][m] = 0
    for i in range(1, n + 1):
        for j in range(K):
            q = grid[i][j]
            f = 1 + w * q[2]
            if bonus and any(dist(q, s) < 250 for s in SC):
                f *= .55
            for k in (j - 1, j, j + 1):
                if 0 <= k < K and cost[i - 1][k] < INF:
                    c = cost[i - 1][k] + dist(grid[i - 1][k], q) * f
                    if c < cost[i][j]:
                        cost[i][j], prev[i][j] = c, k
    j, idx = m, []
    for i in range(n, -1, -1):
        idx.append(grid[i][j])
        j = prev[i][j]
    pts = [vec(*p[:2]) for p in idx[::-1]]
    for _ in range(3):  # lissage du tracé (les extrémités restent fixes)
        pts = [pts[0]] + [unit([pts[i - 1][c] + 2 * pts[i][c] + pts[i + 1][c] for c in range(3)]) for i in range(1, len(pts) - 1)] + [pts[-1]]
    return [(*latlon(v), hz(*latlon(v))) for v in pts]


def analyse(path, veh, eff):
    """veh 0=à pied (EVA) 1=rover pressurisé ; eff 0/1/2 = léger/modéré/intense."""
    km = hrs = o2 = wt = 0
    hs, last = [], -9
    base, v0 = (0.035, 0.06, 0.09)[eff], (2.5, 10)[veh]  # kg O2/h (~0,84 kg/j au repos) ; km/h
    for i in range(1, len(path)):
        d = dist(path[i - 1], path[i])
        h = (path[i - 1][2] + path[i][2]) / 2
        t = d / (v0 * (1 - .55 * h))
        km += d
        hrs += t
        o2 += t * (base * (1 + .8 * h) if veh == 0 else .035 * (1 + .15 * eff))
        wt += t * (.25 * (1 + .3 * eff) if veh == 0 else .1)
        if path[i][2] > .62 and i - last > 1:
            last = i
            hs.append({"i": i, "km": round(km, 1), "type": TYPES[int(path[i][2] * 1000) % 4], "sev": round(path[i][2] * 100)})
    hm = [p[2] for p in path]
    mean = sum(hm) / len(hm)
    return {"path": [[round(p[0], 3), round(p[1], 3)] for p in path], "km": round(km, 1), "h": round(hrs, 2),
            "unc": round(5 + 25 * mean), "o2": round(o2 * 1.3, 2), "water": round(wt * 1.3, 1),
            "msv": round(.67 / 24 * hrs, 3), "risk": round(max(0, min(100, (mean - .25) * 160))),
            "haz": hs[:8], "ok": hrs <= (8, 240)[veh]}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/sites")
def sites():
    return jsonify({"sites": SITES, "mars": MARS})


@app.route("/api/route", methods=["POST"])
def route():
    d = request.get_json()
    A, B = tuple(d["start"][:2]), tuple(d["end"][:2])
    veh, eff = max(0, min(1, int(d.get("veh", 1)))), max(0, min(2, int(d.get("eff", 1))))
    out = {k: analyse(plan(A, B, w, b), veh, eff) for k, (w, b) in PROFILES.items()}
    out["direct_km"] = round(dist(A, B), 1)
    return jsonify(out)


if __name__ == "__main__":
    app.run(debug=True, port=5000)