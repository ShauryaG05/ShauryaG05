"""One-off: turn source-photo.png into shaurya-ascii.svg (dark card, blue-tinted ASCII).
Needs: pip install pillow numpy
"""
from PIL import Image, ImageFilter
import numpy as np, html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLS = 100
CELL_W, CELL_H = 4.5, 8.2
PAD = 24
RAMP = " .,:;-=+*#%@"
CLASSES = ["#2a4a9a", "#3a64c8", "#5b87ee", "#a9c3ff", "#eef3ff"]   # dim blue -> near white
CROP = (0, 30, 460, 440)                                            # trim empty top

im = Image.open(ROOT / "source-photo.png").convert("RGB").crop(CROP)
a = np.array(im).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
bg = ((b - r) > 60) & (b > 150)
lum = 0.299 * r + 0.587 * g + 0.114 * b

blur = lambda arr, s: np.array(Image.fromarray(arr.astype("uint8")).filter(ImageFilter.GaussianBlur(s)))
rows = int(COLS * (im.height / im.width) * (CELL_W / CELL_H))
size = (COLS, rows)
L = np.array(Image.fromarray(blur(lum, 2.0)).resize(size, Image.BOX)).astype(float) / 255
M = np.array(Image.fromarray(blur(~bg * 255, 2.0)).resize(size, Image.BOX)).astype(float) / 255
subject = M >= 0.5

# 1) stretch mid-tones so eyes, nose and jaw separate from the bright skin
V = np.clip((L - 0.05) / 0.95, 0, 1) ** 1.1
# 2) the white shirt (lower third) shouldn't be a solid wall
yy = np.arange(rows)[:, None] / rows
shirt = np.clip((yy - 0.62) / 0.10, 0, 1)
V = V * (1 - 0.50 * shirt)
xx = np.arange(COLS)[None, :]
V = V + shirt * 0.07 * (((xx + np.arange(rows)[:, None] * 2) % 4) / 3 - 0.5)   # light dither so it isn't striped
# 3) keep hair / deep shadows visible on the dark card
V = np.where(subject, np.clip(V, 0.26, 1), 0)

cls = lambda v: min(len(CLASSES) - 1, int(v * len(CLASSES)))
ch = lambda v: RAMP[max(1, int(v * (len(RAMP) - 1)))]

W = PAD * 2 + COLS * CELL_W
H = PAD * 2 + rows * CELL_H
out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Shaurya, ASCII portrait">',
    "<style>",
    f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;font-size:{CELL_H*0.9:.1f}px;white-space:pre}}",
    *[f".c{i}{{fill:{c}}}" for i, c in enumerate(CLASSES)],
    ".row{opacity:0;animation:in .5s cubic-bezier(.2,0,0,1) forwards}",
    "@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}",
    "@media (prefers-reduced-motion:reduce){.row{animation:none;opacity:1}}",
    "</style>",
    f'<rect width="{W:.0f}" height="{H:.0f}" rx="16" fill="#0b0f17"/>',
    f'<rect x=".5" y=".5" width="{W-1:.0f}" height="{H-1:.0f}" rx="15.5" fill="none" stroke="#fff" stroke-opacity=".1"/>',
]
for y in range(rows):
    segs, x = [], 0
    while x < COLS:
        if not subject[y, x]:
            x += 1; continue
        c, start, s = cls(V[y, x]), x, ""
        while x < COLS and subject[y, x] and cls(V[y, x]) == c:
            s += ch(V[y, x]); x += 1
        segs.append((start, c, s))
    if not segs:
        continue
    ty = PAD + (y + 1) * CELL_H - 1.5
    out.append(f'<g class="row" style="animation-delay:{y*12}ms">')
    for start, c, s in segs:
        out.append(f'<text class="c{c}" x="{PAD + start*CELL_W:.1f}" y="{ty:.1f}" textLength="{len(s)*CELL_W:.1f}" lengthAdjust="spacing">{html.escape(s)}</text>')
    out.append("</g>")
out.append("</svg>")
(ROOT / "shaurya-ascii.svg").write_text("\n".join(out))
print("ok", round(W), round(H), rows)
