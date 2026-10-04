"""
T_Foliage (512 x 512, sRGB PNG, opaque, tiles seamlessly) for leafy clusters (oleander, saltbush): a canopy of many
small overlapping leaves. Same channel layout as T_PlantLeaf:

  R  shading: dark gaps between leaves; each leaf has a lit side, a shaded side and a paler midrib, and leaves drawn
     later (on top) are brighter, so the canopy reads with depth
  G  defects: a few whole leaves yellowed / dried, plus small spots on some others (blended to the slot's DamageColor)
  B  = R

The mesh UVs set the leaf size: one texture tile is TILE cm of canopy (oleander 200, saltbush 60).
"""
import math
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")
N = 512
LEAVES = 2600


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    rng = np.random.default_rng(17)
    R = np.full((N, N), 0.12)                 # deep shadow between leaves
    G = np.zeros((N, N))
    for i in range(LEAVES):
        depth = i / LEAVES                     # later = nearer the top of the canopy = brighter
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        L = rng.uniform(24, 40)
        Wd = L * rng.uniform(0.24, 0.34)
        ang = rng.uniform(0, math.pi)
        ca, sa = math.cos(ang), math.sin(ang)
        base = 0.5 + 0.45 * depth + rng.uniform(-0.08, 0.08)
        lit = rng.choice([-1, 1])
        dead = rng.random() < 0.05
        spotted = (not dead) and rng.random() < 0.08
        r = int(L / 2) + 2
        for ox in (-N, 0, N):                  # wrap so the tile is seamless
            for oy in (-N, 0, N):
                x0, y0 = cx + ox, cy + oy
                xa, xb = int(max(0, x0 - r)), int(min(N, x0 + r + 1))
                ya, yb = int(max(0, y0 - r)), int(min(N, y0 + r + 1))
                if xa >= xb or ya >= yb:
                    continue
                yy, xx = np.mgrid[ya:yb, xa:xb] + 0.5
                dx, dy = xx - x0, yy - y0
                a = (dx * ca + dy * sa) / (L / 2)            # along the leaf, -1..1
                b = (-dx * sa + dy * ca) / (Wd / 2)          # across, -1..1
                width = np.sqrt(np.clip(1 - a * a, 0, 1)) * (1 - 0.25 * np.clip(a, 0, 1))   # pointed tip
                inside = np.abs(b) <= width
                if not inside.any():
                    continue
                bn = np.where(width > 0, b / np.maximum(width, 1e-3), 0)
                shade = base * (0.82 + 0.18 * lit * bn)       # lit half / shaded half
                shade = np.where(np.abs(bn) < 0.12, shade * 1.08, shade)   # midrib
                shade = shade * (1 - 0.18 * np.abs(bn) ** 3)  # darker rim
                sub_r = R[ya:yb, xa:xb]
                sub_r[inside] = shade[inside]
                sub_g = G[ya:yb, xa:xb]
                if dead:
                    sub_g[inside] = 0.9
                elif spotted:
                    sp = (np.hypot(a - 0.3, bn * 0.5) < 0.22) | (np.hypot(a + 0.4, bn * 0.4 + 0.3) < 0.15)
                    sub_g[inside & sp] = 0.8
                    sub_g[inside & ~sp] = 0.0
                else:
                    sub_g[inside] = 0.0
    R = np.clip(R, 0, 1)
    rgb = np.stack([srgb(R), srgb(G), srgb(R)], axis=2)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "T_Foliage.png")
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB").save(path)
    Image.fromarray((srgb(R) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "T_Foliage_Surface.png"))
    print(path, "gain %.3f" % (1 / R.mean()), "damaged %.1f%%" % (100 * (G > 0.3).mean()))


if __name__ == "__main__":
    main()
