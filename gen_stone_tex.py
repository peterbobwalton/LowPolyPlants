"""
T_Stone for the LowPolyPlants rocks (Stone, StoneLight, StoneDark, Concrete slots): weathered stone / concrete
surface (mottling, grain, patched areas, hairline cracks), tileable 1024 x 1024, sRGB. R = surface variation (the
material multiplies the slot colour by it, gain ~1.71), G = 0 (no defects), B = R. T_Stone_Surface.png is R alone.
Made from the Heroes of Benghazi facade plaster generator; its notes follow.

Plaster for the town facades (M_BGZ_Facade). Tileable, 1024 x 1024, linear (not sRGB). One tile covers
2 window bays x 2 storeys on the wall (7.2 m x 6.6 m).

T_BGZ_Plaster   R  albedo variation (~0.6..1.1, mean ~0.9): mottling, sand grain, repaired patches, hairline cracks
                G  grime: vertical rain streaks (the shader shows them under sills, slabs and the parapet)
                B  spalled plaster: concrete / block showing through (the shader tints it grey)
T_BGZ_Plaster_N tangent-space normal map from the same height: stucco grain, raised repair patches, cracks and
                spalls cut in. Green = +V (up the wall), DirectX style flip done in the shader if needed.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")
N = 1024
rng = np.random.default_rng(77)


def value_noise(n, cells_x, cells_y, seed):
    """Tileable smooth value noise in [0, 1], cells_x across, cells_y down."""
    r = np.random.default_rng(seed).random((cells_y, cells_x))
    def axis(cells):
        x = np.linspace(0, cells, n, endpoint=False)
        i0 = np.floor(x).astype(int)
        f = x - i0
        return i0, (i0 + 1) % cells, f * f * (3 - 2 * f)
    y0, y1, fy = axis(cells_y)
    x0, x1, fx = axis(cells_x)
    a, b = r[np.ix_(y0, x0)], r[np.ix_(y0, x1)]
    c, d = r[np.ix_(y1, x0)], r[np.ix_(y1, x1)]
    fy, fx = fy[:, None], fx[None, :]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(seed, octaves=(4, 8, 16, 32, 64), gains=(0.5, 0.3, 0.2, 0.12, 0.08), stretch=1):
    v = sum(g * value_noise(N, o, max(1, o // stretch), seed + k) for k, (o, g) in enumerate(zip(octaves, gains)))
    return v / sum(gains)


def blur(a, r):
    """Tileable box blur (twice, ~gaussian)."""
    for _ in range(2):
        k = 2 * r + 1
        a = sum(np.roll(a, s, axis=0) for s in range(-r, r + 1)) / k
        a = sum(np.roll(a, s, axis=1) for s in range(-r, r + 1)) / k
    return a


def tdist(xx, yy, cx, cy):
    dx = np.abs(xx - cx); dx = np.minimum(dx, N - dx)
    dy = np.abs(yy - cy); dy = np.minimum(dy, N - dy)
    return dx, dy


def main():
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    mott = fbm(1)
    grain = blur(rng.random((N, N)), 1)
    alb = 0.92 + 0.16 * (mott - 0.5) * 2 + 0.06 * (grain - 0.5) * 2
    height = 0.35 * grain + 0.15 * fbm(5, octaves=(32, 64, 128), gains=(0.5, 0.3, 0.2))

    # repaired / repainted patches: rough rectangles and blobs, slightly lighter or darker, raised a touch
    warp = fbm(9)
    for _ in range(26):
        cx, cy = rng.uniform(0, N, 2)
        w, h = rng.uniform(40, 220), rng.uniform(30, 160)
        dx, dy = tdist(xx, yy, cx, cy)
        if rng.random() < 0.5:   # rectangle with ragged edge
            d = np.maximum(dx / w, dy / h) + 0.25 * (warp - 0.5)
        else:                    # blob
            d = np.sqrt((dx / w) ** 2 + (dy / h) ** 2) + 0.4 * (warp - 0.5)
        m = np.clip((1 - d) / 0.06, 0, 1)
        alb += m * rng.choice([-1, 1]) * rng.uniform(0.04, 0.09)
        height += m * 0.12

    # spalled plaster: concrete / block showing through, recessed with a dark rim
    spall = np.zeros((N, N))
    for _ in range(4):
        cx, cy = rng.uniform(0, N, 2)
        r = rng.uniform(14, 40)
        dx, dy = tdist(xx, yy, cx, cy)
        d = np.sqrt(dx * dx + (dy * rng.uniform(0.6, 1.4)) ** 2) / r + 1.3 * (fbm(20 + _, octaves=(8, 16, 32), gains=(0.5, 0.3, 0.2)) - 0.5)
        core = np.clip((1 - d) / 0.08, 0, 1)
        rim = np.clip(1 - np.abs(d - 1.05) / 0.08, 0, 1)
        spall = np.maximum(spall, core)
        alb -= rim * 0.06
        height -= core * 0.45
    # block courses inside the spalls (horizontal joints every ~20 cm => 1024 px / 6.6 m * 0.2 m ~ 31 px)
    joints = (np.abs(((yy % 31) - 15.5)) > 14.0) | (np.abs((((xx + 31 * (yy // 31 % 2)) % 62) - 31)) > 29.5)
    alb -= spall * joints * 0.25

    # hairline cracks: random walks, mostly from corners of patches downwards / diagonal
    crack = np.zeros((N, N))
    for _ in range(22):
        x, y = rng.uniform(0, N, 2)
        ang = math.pi / 2 + rng.uniform(-0.8, 0.8)      # mostly running down the wall
        a0 = ang
        L = int(rng.uniform(50, 220))
        for _s in range(L):
            ang += rng.normal(0, 0.18)
            ang += (a0 - ang) * 0.05                        # jagged but keeps its heading
            x = (x + math.cos(ang)) % N
            y = (y + math.sin(ang)) % N
            crack[int(y), int(x)] = 1
            if rng.random() < 0.01:   # small branch
                ang += rng.choice([-1, 1]) * 0.9
    crack = np.clip(blur(crack, 1) * 3.0, 0, 1)
    alb -= crack * 0.30
    height -= crack * 0.35

    # rain grime: thin vertical streaks of varying length (stretched noise), softly broken up
    streak = value_noise(N, 160, 6, 31) * 0.6 + value_noise(N, 90, 3, 32) * 0.4
    streak = np.clip((streak - 0.42) / 0.4, 0, 1) * (0.55 + 0.45 * fbm(33))
    grime = np.clip(streak, 0, 1)

    alb = np.clip(alb, 0.45, 1.15)
    r = np.clip(alb / 1.15, 0, 1)
    rgb = (r * 255 + 0.5).astype(np.uint8)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(np.stack([rgb, np.zeros_like(rgb), rgb], axis=2), "RGB").save(os.path.join(OUT, "T_Stone.png"))
    Image.fromarray(rgb, "L").save(os.path.join(OUT, "T_Stone_Surface.png"))
    x = rgb / 255.0
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    print("T_Stone gain %.3f" % (1 / lin.mean()))


if __name__ == "__main__":
    main()
