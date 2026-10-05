"""T_PalmFrond: 2048 px RGBA atlas of four date-palm fronds (Phoenix dactylifera) for leaf cards:
4 rows of 2048 x 512, each a frond lying along +X (base at the left): a thin central rib with many narrow stiff leaflets angled
forward in a V / herringbone, shorter towards the tip, spines at the base. Rows: 0-1 grey-green, 2 yellow-green, 3 dry brown (skirt).
Painted at 2x and downsampled for soft edges; alpha = leaf coverage (opacity mask). Python 3 + Pillow: python gen_datepalm_tex.py"""
import math, os, random
from PIL import Image, ImageDraw
S = 4096; ROW = S // 4
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FBX", "T_PalmFrond.png")
img = Image.new('RGBA', (S, S), (70, 80, 50, 0)); d = ImageDraw.Draw(img); rnd = random.Random(1991)
PAL = [((88, 104, 72), (70, 86, 58)), ((96, 112, 76), (74, 90, 60)), ((120, 128, 70), (98, 106, 58)), ((150, 118, 74), (118, 92, 58))]
for row in range(4):
    oy = row * ROW + ROW // 2; light, dark = PAL[row]
    x0, x1 = int(S * 0.02), int(S * 0.98)
    rib = [(x0 + (x1 - x0) * t / 40, oy + math.sin(t / 40 * 2.2) * ROW * 0.03) for t in range(41)]
    d.line(rib, fill=(*[int(c * 0.75) for c in dark], 255), width=14)
    n = 110
    for k in range(n):
        t = 0.08 + 0.9 * k / n; i = int(t * 40); x, y = rib[i]
        L = ROW * 0.52 * (1.0 - 0.6 * t) * rnd.uniform(0.85, 1.1)          # leaflets shorten towards the tip
        if t < 0.18: L *= 0.45                                               # short spines at the base
        for side in (-1, 1):
            a = math.radians(rnd.uniform(28, 42))                            # angled forward (towards the tip): the V
            ex, ey = x + math.cos(a) * L, y + side * math.sin(a) * L
            g = rnd.uniform(0.85, 1.12); col = tuple(min(255, int(c * g)) for c in (light if rnd.random() > 0.35 else dark))
            w = 13 if t > 0.18 else 8
            d.line([(x, y), (ex, ey)], fill=(*col, 255), width=w)
            if row == 3 and rnd.random() < 0.3:                              # dry fronds: some leaflets broken off
                d.line([(x, y), (x + (ex - x) * 0.4, y + (ey - y) * 0.4)], fill=(*col, 255), width=w)
img = img.resize((2048, 2048), Image.LANCZOS)
os.makedirs(os.path.dirname(OUT), exist_ok=True); img.save(OUT); print('saved', OUT)
