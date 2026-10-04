"""
T_CactusPad (256 x 256, sRGB PNG, opaque) for the prickly-pear pads, same channel layout as T_PlantLeaf:

  R  surface: soft mottling, the pad lighter towards its top (V near 1) and rim
  G  areole mask: a staggered grid of spine tufts - a pale cushion with a few short spines radiating from it.
     The material blends to the slot's DamageColor (a pale cream on the pads) by G x DamageAmount.
  B  = R

Pad UVs are planar: U across the pad (0.5 = midline), V along it (0 = base, 1 = top). A pad is about twice as
long as it is wide, so the dots are drawn twice as wide in U as in V to come out round on the mesh.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")
N = 256
COLS, ROWS = 6, 11                      # areoles across / along a pad


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:N, 0:N] + 0.5
    u, v = xx / N, yy / N
    # surface: gentle blotches, lighter towards the top and the rim
    blot = np.zeros((N, N))
    for k in range(40):
        cx, cy, r = rng.uniform(0, N), rng.uniform(0, N), rng.uniform(15, 45)
        blot += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)) * rng.uniform(-1, 1)
    blot /= np.abs(blot).max()
    rim = np.clip((np.hypot((u - 0.5) * 2, (v - 0.5) * 2) - 0.7) / 0.3, 0, 1)
    surf = 0.80 + 0.06 * blot + 0.16 * np.clip((v - 0.55) / 0.45, 0, 1) ** 1.5 + 0.06 * rim
    surf = np.clip(surf, 0.6, 1.0)
    # areoles: staggered grid, slightly jittered; cushion + short spines
    g = np.zeros((N, N))
    du, dv = N / COLS, N / ROWS
    for row in range(ROWS + 1):
        for col in range(COLS + 1):
            cx = (col + (0.5 if row % 2 else 0.0)) * du + rng.uniform(-2, 2)
            cy = row * dv + rng.uniform(-1.5, 1.5)
            for ox in (-N, 0, N):                                   # tile seamlessly
                for oy in (-N, 0, N):
                    x0, y0 = cx + ox, cy + oy
                    if not (-12 < x0 < N + 12 and -8 < y0 < N + 8):
                        continue
                    d = np.hypot((xx - x0) / 2.0, (yy - y0))       # round on the mesh (pad is 2:1)
                    g = np.maximum(g, np.clip(1.6 - d / 2.2, 0, 1))  # soft cushion, ~4.5 px across in V
                    for s in range(rng.integers(3, 6)):             # short spines
                        a = rng.uniform(0, 2 * math.pi)
                        for t in np.linspace(0, 1, 8):
                            px = int(round(x0 + math.cos(a) * 9 * t))
                            py = int(round(y0 + math.sin(a) * 4.5 * t))
                            if 0 <= px < N and 0 <= py < N:
                                g[py, px] = max(g[py, px], 0.85 * (1 - 0.6 * t))
    g = np.clip(g, 0, 1)
    surf = surf * (1 - 0.12 * np.clip(g * 2, 0, 1))                 # slight dimple under each areole
    rgb = np.stack([srgb(surf), srgb(g), srgb(surf)], axis=2)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "T_CactusPad.png")
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB").save(path)
    Image.fromarray((srgb(surf) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "T_CactusPad_Surface.png"))
    print(path, "gain %.3f" % (1 / surf.mean()), "areole cover %.1f%%" % (100 * (g > 0.3).mean()))


if __name__ == "__main__":
    main()
