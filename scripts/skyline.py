"""Genera dist/skyline.svg: la actividad de GitHub del último año como una
ciudad pixel de noche (un edificio por semana) con el avión de pomoplane
cruzando el cielo.

Uso: GITHUB_TOKEN=... python3 scripts/skyline.py [usuario]
Sin dependencias: solo la stdlib, para que corra tal cual en el runner.
"""
import base64
import json
import math
import os
import pathlib
import random
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "RiosMauricio"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "skyline.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

# Paleta del portfolio
ACCENT = "#63b3ed"
CYAN = "#22d3ee"
PINK = "#f472b6"
AMBER = "#fbbf24"
GREEN = "#4ade80"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

W, H = 960, 300
GROUND = 262
BW, GAP = 13, 4  # ancho de edificio y separación
MAX_H = 150
BASE_X, PLANE_Y = 700, 92  # posición estática del avión (sin animación)


def fetch_calendar():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.load(res)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def pixel_frame_points(w, h, s=6):
    pts = [
        (0, 2 * s), (s, 2 * s), (s, s), (2 * s, s), (2 * s, 0),
        (w - 2 * s, 0), (w - 2 * s, s), (w - s, s), (w - s, 2 * s), (w, 2 * s),
        (w, h - 2 * s), (w - s, h - 2 * s), (w - s, h - s), (w - 2 * s, h - s), (w - 2 * s, h),
        (2 * s, h), (2 * s, h - s), (s, h - s), (s, h - 2 * s), (0, h - 2 * s),
    ]
    return " ".join(f"{x},{y}" for x, y in pts)


# Avión pixel (mirando a la derecha). Cada string es una fila; los
# caracteres mapean a colores, "." es transparente.
PLANE = [
    "..........ww........",
    "..........wbw.......",
    "rr........wbbw......",
    "rrr.......wbbbw.....",
    "rrwwwwwwwwwwwwwwwc..",
    ".wwwwwwwwwwwwwwwwwcc",
    "..gggggggggggggggg..",
    "..........wbbbw.....",
    "..........wbbw......",
    "..........ww........",
]
PLANE_COLORS = {"w": "#e8f1ff", "b": ACCENT, "r": PINK, "c": CYAN, "g": "#8aa4c8"}


def plane_rects(px=3):
    out = []
    for y, row in enumerate(PLANE):
        for x, ch in enumerate(row):
            if ch != ".":
                out.append(f'<rect x="{x * px}" y="{y * px}" width="{px}" height="{px}" fill="{PLANE_COLORS[ch]}"/>')
    return "".join(out), len(PLANE[0]) * px, len(PLANE) * px


def build_svg(cal):
    weeks = cal["weeks"][-53:]
    total = cal["totalContributions"]
    sums = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    top = max(sums) or 1
    best_i = sums.index(top)
    rnd = random.Random(20260)  # determinista: el SVG solo cambia si cambian los datos

    n = len(weeks)
    city_w = n * (BW + GAP) - GAP
    x0 = (W - city_w) // 2

    parts = []
    twinkles = 0

    # --- estrellas ---
    stars = []
    for i in range(70):
        sx, sy = rnd.randint(16, W - 16), rnd.randint(14, 150)
        size = 2 if rnd.random() < 0.25 else 1
        cls = f' class="tw" style="animation-delay:{rnd.uniform(0, 4):.2f}s"' if i % 4 == 0 else ""
        stars.append(f'<rect x="{sx}" y="{sy}" width="{size}" height="{size}" fill="#dbeafe" fill-opacity="{rnd.uniform(.35, .9):.2f}"{cls}/>')
    parts.append("".join(stars))

    # --- luna pixel ---
    moon = []
    cx, cy, r = W // 2 - 40, 40, 18
    for yy in range(-r, r + 1, 3):
        for xx in range(-r, r + 1, 3):
            if xx * xx + yy * yy <= r * r and (xx - 7) ** 2 + (yy + 4) ** 2 > (r - 4) ** 2:
                moon.append(f'<rect x="{cx + xx}" y="{cy + yy}" width="3" height="3" fill="#fde68a"/>')
    parts.append(f'<g opacity=".9">{"".join(moon)}</g>')

    # --- edificios ---
    city = []
    lights = []
    for i, s in enumerate(sums):
        x = x0 + i * (BW + GAP)
        h = 6 if s == 0 else 14 + round(math.sqrt(s / top) * (MAX_H - 14))
        h -= h % 3
        y = GROUND - h
        shade = ["#0e1a3a", "#112047", "#0c1734"][i % 3]
        city.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{h}" fill="{shade}"/>')
        city.append(f'<rect x="{x}" y="{y}" width="{BW}" height="2" fill="{ACCENT}" fill-opacity=".35"/>')
        if s == 0:
            continue
        # ventanas: dos columnas, una fila cada 6px; se encienden según
        # la cantidad de contribuciones de la semana
        slots = [(x + 3, wy) for wy in range(y + 6, GROUND - 6, 6)] + [(x + 8, wy) for wy in range(y + 6, GROUND - 6, 6)]
        rnd.shuffle(slots)
        lit = min(len(slots), max(1, round(len(slots) * min(1, 0.25 + s / top))))
        for (wx, wy) in slots[:lit]:
            c = rnd.choices([AMBER, CYAN, "#fef3c7", PINK], weights=[5, 3, 3, 1])[0]
            anim = ""
            if twinkles < 60 and rnd.random() < 0.08:
                twinkles += 1
                anim = f' class="tw" style="animation-delay:{rnd.uniform(0, 5):.2f}s"'
            lights.append(f'<rect x="{wx}" y="{wy}" width="2" height="3" fill="{c}"{anim}/>')
        if i == best_i:
            # antena con baliza en la mejor semana
            city.append(f'<rect x="{x + 6}" y="{y - 14}" width="1" height="14" fill="#8aa4c8"/>')
            city.append(f'<rect class="beacon" x="{x + 5}" y="{y - 17}" width="3" height="3" fill="{PINK}"/>')
            label = f"BEST WEEK · {top}"
            lx = min(max(x - 40, 20), W - 150)
            city.append(f'<text x="{lx}" y="{y - 24}" class="silk" font-size="9" fill="{PINK}" letter-spacing="1">{label}</text>')
    parts.append("".join(city))
    parts.append(f'<g class="lights">{"".join(lights)}</g>')

    # --- suelo y meses ---
    parts.append(f'<rect x="0" y="{GROUND}" width="{W}" height="2" fill="{ACCENT}" fill-opacity=".55"/>')
    parts.append(f'<rect x="0" y="{GROUND + 2}" width="{W}" height="{H - GROUND}" fill="#070d1f"/>')
    seen = set()
    for i, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"][5:7])
        if m not in seen and w["contributionDays"][0]["date"][8:10] <= "07":
            seen.add(m)
            x = x0 + i * (BW + GAP)
            parts.append(f'<text x="{x}" y="{GROUND + 18}" class="silk" font-size="9" fill="#7f9cc6" letter-spacing="1">{MONTHS[m - 1]}</text>')
            parts.append(f'<rect x="{x}" y="{GROUND + 2}" width="1" height="4" fill="#7f9cc6"/>')

    # --- avión con cartel ---
    plane, pw, ph = plane_rects()
    banner_txt = f"{total:,} CONTRIBUTIONS · LAST 12 MONTHS"
    bw = round(len(banner_txt) * 10.2) + 28
    plane_g = f"""
<g transform="translate({BASE_X},{PLANE_Y})"><g class="fly"><g class="bob">
  <path d="M{-bw - 18},10 L{-18},10" stroke="#8aa4c8" stroke-width="1" stroke-dasharray="2 2"/>
  <g class="flag">
    <rect x="{-bw - 18}" y="-2" width="{bw}" height="24" fill="#0b1329" stroke="{AMBER}" stroke-width="2"/>
    <text x="{-bw / 2 - 18}" y="14" text-anchor="middle" class="silk" font-size="11" fill="{AMBER}" letter-spacing="1">{banner_txt}</text>
  </g>
  <g transform="translate(0,-4)">{plane}</g>
  <rect class="trail" x="-6" y="11" width="4" height="2" fill="#dbeafe" fill-opacity=".6"/>
</g></g></g>"""

    font = base64.b64encode((ROOT / "assets" / "fonts" / "Silkscreen-Bold.ttf").read_bytes()).decode()
    frame = pixel_frame_points(W - 4, H - 4)
    travel_from = -BASE_X - pw - 20
    travel_to = W - BASE_X + bw + 40

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{banner_txt}: GitHub activity drawn as a night city, one building per week">
<title>{banner_txt}</title>
<style>
@font-face {{ font-family: 'Silk'; font-weight: 700; src: url(data:font/ttf;base64,{font}) format('truetype'); }}
.silk {{ font-family: 'Silk', monospace; font-weight: 700; }}
.tw {{ animation: tw 3.4s steps(1) infinite; }}
@keyframes tw {{ 40% {{ opacity: .15; }} 55% {{ opacity: 1; }} }}
.beacon {{ animation: beacon 1.2s steps(1) infinite; }}
@keyframes beacon {{ 50% {{ opacity: .1; }} }}
.fly {{ animation: fly 16s linear infinite; }}
@keyframes fly {{ from {{ transform: translateX({travel_from}px); }} to {{ transform: translateX({travel_to}px); }} }}
.bob {{ animation: bob 2.4s ease-in-out infinite; }}
@keyframes bob {{ 50% {{ transform: translateY(5px); }} }}
.flag {{ animation: flag .9s steps(2) infinite; transform-origin: 0 10px; }}
@keyframes flag {{ 50% {{ transform: skewY(-2deg); }} }}
.trail {{ animation: tw .4s steps(1) infinite; }}
.roll {{ animation: roll 8s linear infinite; }}
@keyframes roll {{ from {{ transform: translateY(-60px); }} to {{ transform: translateY({H + 60}px); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070c1f"/><stop offset=".7" stop-color="#132a63"/><stop offset="1" stop-color="#1c3a7a"/></linearGradient>
<radialGradient id="glow" cx=".5" cy="1" r=".7"><stop offset="0" stop-color="{CYAN}" stop-opacity=".16"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
<radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></radialGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity=".25"/></pattern>
<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#94c9ff" stop-opacity="0"/><stop offset=".5" stop-color="#94c9ff" stop-opacity=".06"/><stop offset="1" stop-color="#94c9ff" stop-opacity="0"/></linearGradient>
<clipPath id="frame"><polygon points="{frame}" transform="translate(2,2)"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<rect width="{W}" height="{H}" fill="url(#glow)"/>
{"".join(parts)}
{plane_g}
<text x="22" y="32" class="silk" font-size="11" fill="{GREEN}" letter-spacing="2">● NIGHT FLIGHT</text>
<text x="22" y="48" class="silk" font-size="9" fill="#7f9cc6" letter-spacing="1">1 BUILDING = 1 WEEK OF COMMITS</text>
<rect class="roll" width="{W}" height="60" fill="url(#bar)"/>
<rect width="{W}" height="{H}" fill="url(#scan)"/>
<rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
<polygon points="{frame}" transform="translate(2,2)" fill="none" stroke="{ACCENT}" stroke-opacity=".55" stroke-width="2" shape-rendering="crispEdges"/>
</svg>"""


def main():
    cal = fetch_calendar()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(cal))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {cal['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
