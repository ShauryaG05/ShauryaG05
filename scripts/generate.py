#!/usr/bin/env python3
"""Builds contrib-heatmap.svg and stats.svg from a GitHub user's public contribution calendar.
Standard library only. Usage:  GH_USER=ShauryaG05 python scripts/generate.py
"""
import os, re, sys, html, datetime as dt, pathlib, urllib.request

USER = os.environ.get("GH_USER", "ShauryaG05")
ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------- fetch ----------
def fetch(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "profile-readme-generator", "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse(page):
    tips = {m.group(1): m.group(2) for m in
            re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>\s*([^<]*?)\s*</tool-tip>', page)}
    days = {}
    for m in re.finditer(r"<td\b([^>]*ContributionCalendar-day[^>]*)>", page):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        if "data-date" not in attrs:
            continue
        row, col = map(int, attrs["id"].rsplit("-", 2)[-2:])      # row = weekday (Sun=0), col = week
        t = tips.get(attrs["id"], "")
        n = re.match(r"(\d+)\s+contribution", t)
        days[attrs["data-date"]] = dict(row=row, col=col, level=int(attrs.get("data-level", 0)),
                                        count=int(n.group(1)) if n else 0)
    if not days:
        raise RuntimeError("no contribution cells found, GitHub markup may have changed")
    return days

# ---------- numbers ----------
def streaks(days):
    ds = sorted(days)
    longest = run = 0
    for d in ds:
        run = run + 1 if days[d]["count"] > 0 else 0
        longest = max(longest, run)
    cur, i = 0, len(ds) - 1
    if i >= 0 and days[ds[i]]["count"] == 0:      # today may simply not have happened yet
        i -= 1
    while i >= 0 and days[ds[i]]["count"] > 0:
        cur += 1; i -= 1
    return cur, longest

def pretty(d):
    x = dt.date.fromisoformat(d)
    return f"{x.strftime('%b')} {x.day}"

# ---------- shared styling ----------
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
BG, TILE, INK, MUTED, ACCENT = "#0b0f17", "#111826", "#eef3ff", "#7d8aa5", "#5b87ee"
LEVELS = ["#161d2b", "#1d3b78", "#2b5bc4", "#4a82f0", "#9dbfff"]

def head(w, h, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">',
        "<style>",
        f"text{{font-family:{FONT};font-variant-numeric:tabular-nums;fill:{INK}}}",
        f".m{{fill:{MUTED}}}.a{{fill:{ACCENT}}}",
        ".in{opacity:0;transform-box:fill-box;transform-origin:center;animation:in .45s cubic-bezier(.2,0,0,1) forwards}",
        "@keyframes in{from{opacity:0;transform:translateY(4px) scale(.96)}to{opacity:1;transform:none}}",
        "@media (prefers-reduced-motion:reduce){.in{animation:none;opacity:1}}",
        "</style>",
        f'<rect width="{w}" height="{h}" rx="20" fill="{BG}"/>',
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="19.5" fill="none" stroke="#fff" stroke-opacity=".1"/>',
    ]

# ---------- heatmap ----------
def heatmap(days, total, today):
    cell, gap, left, top, pad = 13, 3, 34, 64, 24
    weeks = max(v["col"] for v in days.values()) + 1
    W = pad * 2 + left + weeks * (cell + gap) - gap
    H = top + 7 * (cell + gap) - gap + 56
    o = head(W, H, f"{total} contributions in the last year")
    o.append(f'<text x="{pad}" y="36" font-size="15" font-weight="600">{total:,} <tspan class="m" font-weight="400">contributions in the last year</tspan></text>')
    # month labels
    last_x, seen = -99, None
    first_by_col = {}
    for d, v in days.items():
        if v["col"] not in first_by_col or d < first_by_col[v["col"]]:
            first_by_col[v["col"]] = d
    for c in range(weeks):
        d = first_by_col.get(c)
        if not d: continue
        mth = d[5:7]
        x = pad + left + c * (cell + gap)
        if mth != seen and x - last_x >= 36:
            o.append(f'<text class="m" x="{x}" y="{top-10}" font-size="10">{dt.date.fromisoformat(d).strftime("%b")}</text>')
            last_x = x
        seen = mth
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        o.append(f'<text class="m" x="{pad}" y="{top + r*(cell+gap) + 10}" font-size="10">{name}</text>')
    for d, v in sorted(days.items()):
        x = pad + left + v["col"] * (cell + gap)
        y = top + v["row"] * (cell + gap)
        c = "contribution" + ("" if v["count"] == 1 else "s")
        o.append(f'<rect class="in" style="animation-delay:{v["col"]*9}ms" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{LEVELS[v["level"]]}"><title>{v["count"]} {c} on {pretty(d)}</title></rect>')
    # legend, bottom right
    lx = W - pad - (5 * (cell + 3) + 74)
    ly = H - 30
    o.append(f'<text class="m" x="{lx}" y="{ly+10}" font-size="10">Less</text>')
    for i, col in enumerate(LEVELS):
        o.append(f'<rect x="{lx + 30 + i*(cell+3)}" y="{ly}" width="{cell}" height="{cell}" rx="4" fill="{col}"/>')
    o.append(f'<text class="m" x="{lx + 30 + 5*(cell+3) + 4}" y="{ly+10}" font-size="10">More</text>')
    o.append(f'<text class="m" x="{pad}" y="{ly+10}" font-size="10">updated {today.isoformat()}</text>')
    o.append("</svg>")
    return "\n".join(o)

# ---------- stats ----------
def stats(days, total, today):
    W, H, inset, gap = 498, 442, 12, 8          # card r=20 = tile r 8 + inset 12 (concentric)
    cur, longest = streaks(days)
    active = sum(1 for v in days.values() if v["count"] > 0)
    best_d = max(days, key=lambda d: days[d]["count"])
    best = days[best_d]["count"]
    first = min(days)
    # weekly totals for the sparkline
    wk = {}
    for v in days.values():
        wk[v["col"]] = wk.get(v["col"], 0) + v["count"]
    series = [wk.get(c, 0) for c in range(max(wk) + 1)]

    o = head(W, H, f"GitHub stats for {USER}")
    iw = W - inset * 2
    hero_h = 184
    o.append(f'<rect class="in" x="{inset}" y="{inset}" width="{iw}" height="{hero_h}" rx="8" fill="{TILE}"/>')
    o.append(f'<text class="m in" style="animation-delay:100ms" x="{inset+20}" y="{inset+34}" font-size="12">contributions · last year</text>')
    o.append(f'<text class="in" style="animation-delay:150ms" x="{inset+20}" y="{inset+92}" font-size="56" font-weight="700">{total:,}</text>')
    o.append(f'<text class="m in" style="animation-delay:200ms" x="{inset+20}" y="{inset+114}" font-size="11">since {pretty(first)}</text>')
    # sparkline bars
    sx, sw, sb, sh = inset + 20, iw - 40, inset + hero_h - 18, 34
    n = len(series); bw = sw / n; mx = max(series) or 1
    for i, val in enumerate(series):
        h = max(2, val / mx * sh)
        o.append(f'<rect class="in" style="animation-delay:{250+i*8}ms" x="{sx + i*bw:.1f}" y="{sb-h:.1f}" width="{bw-2:.1f}" height="{h:.1f}" rx="1.5" fill="{ACCENT if val else LEVELS[0]}"/>')
    tiles = [
        ("current streak", f"{cur}", "day" + ("" if cur == 1 else "s")),
        ("longest streak", f"{longest}", "day" + ("" if longest == 1 else "s")),
        ("active days", f"{active}", f"of {len(days)}"),
        ("best day", f"{best}", f"on {pretty(best_d)}"),
    ]
    ty0 = inset + hero_h + gap
    th = (H - inset - ty0 - gap) / 2
    tw = (iw - gap) / 2
    for i, (lab, val, sub) in enumerate(tiles):
        x = inset + (i % 2) * (tw + gap)
        y = ty0 + (i // 2) * (th + gap)
        d = 450 + i * 100
        o.append(f'<rect class="in" style="animation-delay:{d}ms" x="{x:.1f}" y="{y:.1f}" width="{tw:.1f}" height="{th:.1f}" rx="8" fill="{TILE}"/>')
        o.append(f'<text class="m in" style="animation-delay:{d}ms" x="{x+20:.1f}" y="{y+32:.1f}" font-size="12">{lab}</text>')
        o.append(f'<text class="in" style="animation-delay:{d+50}ms" x="{x+20:.1f}" y="{y+th-38:.1f}" font-size="34" font-weight="700">{val}</text>')
        o.append(f'<text class="m in" style="animation-delay:{d+50}ms" x="{x+20:.1f}" y="{y+th-18:.1f}" font-size="11">{sub}</text>')
    o.append("</svg>")
    return "\n".join(o)

def main():
    days = parse(fetch(USER))
    total = sum(v["count"] for v in days.values())
    today = dt.date.today()
    (ROOT / "contrib-heatmap.svg").write_text(heatmap(days, total, today))
    (ROOT / "stats.svg").write_text(stats(days, total, today))
    cur, longest = streaks(days)
    print(f"{USER}: total={total} current={cur} longest={longest} days={len(days)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:          # keep the old SVGs if anything goes wrong
        print("generate.py failed:", e, file=sys.stderr); sys.exit(1)
