"""
T_PlantLeaf (512 x 512, sRGB PNG, opaque) for the low-poly plants and grasses. Two channels do different jobs:

  R  surface: soft mottling, fine fibres running along the leaf (V), a pale crease down the middle (U = 0.5),
     darker towards the edges. The material multiplies the slot colour by it.
  G  defects mask: blemish spots with a pale halo, scratches and scars, a burnt tip (V near 1) with a ragged
     edge, nibbled-looking patches along the edges. The material blends towards the slot's DamageColor by
     G x DamageAmount, so damage is brown / bleached rather than just darker.
  B  = R (so the texture looks sensible in a viewer).

UVs on the meshes: U across a leaf / blade (0.5 on the midline), V from base (0) to tip (1).
"""
import math
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")
N = 512
rng = np.random.default_rng(11)


def value_noise(n, cells, seed):
    """Tileable smooth value noise in [0, 1]."""
    r = np.random.default_rng(seed).random((cells, cells))
    x = np.linspace(0, cells, n, endpoint=False)
    i0 = np.floor(x).astype(int)
    f = x - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells
    a = r[np.ix_(i0, i0)]
    b = r[np.ix_(i0, i1)]
    c = r[np.ix_(i1, i0)]
    d = r[np.ix_(i1, i1)]
    fy, fx = f[:, None], f[None, :]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(n, seed, octaves=(4, 8, 16, 32), gains=(0.5, 0.25, 0.15, 0.1)):
    v = sum(g * value_noise(n, o, seed + k) for k, (o, g) in enumerate(zip(octaves, gains)))
    return v / sum(gains)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    v, u = np.mgrid[0:N, 0:N] / N           # rows = V (along the leaf), columns = U (across)
    du = np.abs(u - 0.5) * 2                 # 0 on the crease, 1 at the edges

    # ---- R: surface variation (linear values, ~0.7..1)
    mott = fbm(N, 3)
    fib = value_noise(N, 64, 9)[:, :]        # fine streaks: stretch noise along V
    fib = np.repeat(value_noise(N // 8, 64, 9)[:, :N // 8], 1, axis=0)
    fib = np.array(Image.fromarray((fib * 255).astype(np.uint8)).resize((N, N), Image.BILINEAR)) / 255.0
    surf = 0.80 + 0.30 * (mott - 0.5) * 2 + 0.12 * (fib - 0.5) * 2
    surf -= 0.18 * du ** 2                                        # darker edges
    crease = np.exp(-(du / 0.03) ** 2)
    surf = surf * (1 - 0.5 * crease) + 0.97 * 0.5 * crease        # pale crease
    surf = np.clip(surf, 0.55, 1.0)

    # ---- G: defect mask 0..1
    dmg = np.zeros((N, N))
    yy, xx = np.mgrid[0:N, 0:N]
    warp = fbm(N, 51, octaves=(8, 16, 32), gains=(0.5, 0.3, 0.2))
    for _ in range(24):                                           # blemish spots: ragged core, faint halo (big enough to read on a pad)
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        r = rng.uniform(10, 40)
        dx = np.minimum(np.abs(xx - cx), N - np.abs(xx - cx))     # tileable distance
        dy = np.minimum(np.abs(yy - cy), N - np.abs(yy - cy))
        d = np.sqrt(dx * dx + dy * dy * rng.uniform(0.4, 1.0)) * (1 + 0.9 * (warp - 0.5))
        core = np.clip(1 - d / r, 0, 1) ** 0.4 * rng.uniform(0.6, 1.0)
        halo = np.clip(1 - np.abs(d - r * 1.3) / (r * 0.5), 0, 1) * rng.uniform(0.1, 0.25)
        dmg = np.maximum(dmg, np.maximum(core, halo))
        surf = surf - 0.05 * halo / 0.25
    for _ in range(22):                                           # scratches / scars
        x0, y0 = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, math.pi)
        L = rng.uniform(40, 150)
        for t in np.linspace(0, 1, int(L * 2)):
            x = int(x0 + math.cos(ang) * L * t) % N
            y = int(y0 + math.sin(ang) * L * t) % N
            for oy in (-1, 0, 1, 2):
                dmg[(y + oy) % N, x] = max(dmg[(y + oy) % N, x], 0.8 if 0 <= oy <= 1 else 0.45)
    tipn = fbm(N, 21)                                             # burnt tip, ragged edge
    tip = np.clip((v - 0.87 + 0.10 * (tipn - 0.5) * 2) / 0.08, 0, 1)
    dmg = np.maximum(dmg, tip)
    edgen = fbm(N, 33)                                            # nibbled edges
    edge = np.clip((du - 0.88 + 0.2 * (edgen - 0.5)) / 0.08, 0, 1) * (edgen > 0.55)
    dmg = np.maximum(dmg, edge * 0.9)
    dmg = np.array(Image.fromarray((np.clip(dmg, 0, 1) * 255).astype(np.uint8)).resize((N, N), Image.BILINEAR)) / 255.0

    surf = np.clip(surf, 0.5, 1.0)
    rgb = np.stack([srgb(surf), srgb(dmg), srgb(surf)], axis=2)
    img = Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "T_PlantLeaf.png")
    img.save(path)
    # surface only, for engines / OBJ viewers that just multiply a diffuse map
    Image.fromarray((srgb(surf) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "T_PlantLeaf_Surface.png"))
    print(path, "gain %.3f" % (1.0 / surf.mean()), "damage cover %.1f%%" % (100 * (dmg > 0.3).mean()))


if __name__ == "__main__":
    main()
