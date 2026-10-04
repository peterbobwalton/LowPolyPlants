"""
LowPolyPlants generator: 4 low-poly plants and 3 dry grass clumps as OBJ + MTL. Python 3, no dependencies.

    python gen_plants.py [out_dir]

Z up, centimetres, pivot on the ground. Leaves, pads and blades carry UVs for T_PlantLeaf (U across a leaf, 0.5 on
the midline; V from base to tip). Leaves and blades are single-sided strips: render with a TWO-SIDED material.

Plants:  SM_Plant_Agave        blue-grey rosette of thick pointed leaves, a few dead ones at the base
         SM_Plant_PricklyPear  Opuntia: flat oval pads growing off each other, red fruit on the rims
         SM_Plant_Oleander     dense dark-green flowering shrub, pink flowers
         SM_Plant_Saltbush     low grey-green mound
Grasses: SM_Grass_Tuft         clump of short dry tufts (~2.5 m across)
         SM_Grass_Seed         taller tufts with seed heads
         SM_Grass_Dead         dead brown clumps splayed flat

Slots: Agave, AgaveDead, Pad, Fruit, Leaf, LeafDark, Flower, Stem, Salt, Straw, StrawPale, Olive, Seed, DeadGrass.
"""
import math
import os
import random
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")

# linear RGB slot colours (as used in Unreal); the MTL gets them in sRGB
COLOURS = {"Agave": (0.10, 0.16, 0.12), "AgaveDead": (0.20, 0.13, 0.06), "Pad": (0.07, 0.15, 0.04),
           "Fruit": (0.30, 0.03, 0.05), "Leaf": (0.04, 0.10, 0.03), "LeafDark": (0.025, 0.07, 0.02),
           "Flower": (0.55, 0.12, 0.22), "Stem": (0.12, 0.09, 0.05), "Salt": (0.13, 0.15, 0.10),
           "Straw": (0.20, 0.16, 0.06), "StrawPale": (0.30, 0.25, 0.12), "Olive": (0.11, 0.12, 0.04),
           "Seed": (0.26, 0.21, 0.10), "DeadGrass": (0.12, 0.07, 0.03)}
UNTEXTURED = ("Flower", "Fruit")


def srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


class Mesh:
    """Flat-shaded OBJ builder in cm; faces CCW seen from the front."""

    def __init__(self):
        self.v, self.vt, self.vn, self.vi, self.ti, self.ni, self.faces = [], [], [], {}, {}, {}, {}

    def _idx(self, store, lut, val):
        k = tuple(round(c, 4) for c in val)
        if k not in lut:
            store.append(k)
            lut[k] = len(store)
        return lut[k]

    def poly(self, slot, pts, uvs=None):
        a, b, c = pts[0], pts[1], pts[-1]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        L = math.sqrt(sum(x * x for x in n))
        if L < 1e-9:
            return
        ni = self._idx(self.vn, self.ni, tuple(x / L for x in n))
        uvs = uvs or [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)][:len(pts)]
        self.faces.setdefault(slot, []).append([(self._idx(self.v, self.vi, p), self._idx(self.vt, self.ti, t), ni)
                                                for p, t in zip(pts, uvs)])

    def tris(self):
        return sum(len(f) - 2 for fs in self.faces.values() for f in fs)

    def write(self, path, comment=""):
        base = os.path.splitext(os.path.basename(path))[0]
        with open(path, "w") as f:
            f.write("# LowPolyPlants - %s (cm, Z up)\nmtllib %s.mtl\no %s\n" % (comment, base, base))
            for p in self.v:
                f.write("v %.2f %.2f %.2f\n" % p)
            for t in self.vt:
                f.write("vt %.4f %.4f\n" % t)
            for n in self.vn:
                f.write("vn %.4f %.4f %.4f\n" % n)
            for slot in COLOURS:
                if slot in self.faces:
                    f.write("usemtl %s\n" % slot)
                    for face in self.faces[slot]:
                        f.write("f " + " ".join("%d/%d/%d" % c for c in face) + "\n")
        with open(os.path.join(os.path.dirname(path), base + ".mtl"), "w") as f:
            for slot in COLOURS:
                if slot in self.faces:
                    r, g, b = (srgb(c) for c in COLOURS[slot])
                    f.write("newmtl %s\nKd %.4f %.4f %.4f\nKs 0 0 0\nd 1\nillum 1\n" % (slot, r, g, b))
                    if slot not in UNTEXTURED:
                        f.write("map_Kd T_PlantLeaf_Surface.png\n")
                    f.write("\n")


def quad(m, slot, a, b, c, d):
    m.poly(slot, [a, b, c, d])


def tri(m, slot, a, b, c):
    m.poly(slot, [a, b, c])


Z = (0.0, 0.0, 1.0)


def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


def uvface(m, slot, pts, uvs):
    """Face with its own UVs (U across a leaf, 0.5 on the midline; V base -> tip)."""
    m.poly(slot, pts, uvs)


def blade(m, slot, base, az, elev, length, width, droop, segs=3, fold=0.0, taper=1.0):
    """A strip from base outwards at azimuth/elevation, bending down by droop (cm at the tip), pointed tip.
    fold > 0 folds it into a V (thick leaves). Returns the tip point."""
    d = (math.cos(elev) * math.cos(az), math.cos(elev) * math.sin(az), math.sin(elev))
    side = (math.sin(az), -math.cos(az), 0.0)
    pts = [add(add(base, d, length * j / segs), Z, -droop * (j / segs) ** 2) for j in range(segs + 1)]
    prev = None
    for j, p in enumerate(pts):
        t = j / segs
        w = width * (1.0 - t) ** taper if j < segs else 0.0
        T = norm(sub(pts[min(j + 1, segs)], pts[max(j - 1, 0)]))
        up = norm(cross(side, T))
        R = add(add(p, side, w * math.cos(fold)), up, -w * math.sin(fold))
        L = add(add(p, side, -w * math.cos(fold)), up, -w * math.sin(fold))
        e = 0.5 * w / max(width, 0.01)                   # texture width follows the leaf width
        if prev:
            p0, R0, L0, t0, e0 = prev
            if w > 0:
                if fold > 0:
                    uvface(m, slot, [p0, p, R, R0], [(0.5, t0), (0.5, t), (0.5 + e, t), (0.5 + e0, t0)])
                    uvface(m, slot, [L0, L, p, p0], [(0.5 - e0, t0), (0.5 - e, t), (0.5, t), (0.5, t0)])
                else:
                    uvface(m, slot, [L0, L, R, R0], [(0.5 - e0, t0), (0.5 - e, t), (0.5 + e, t), (0.5 + e0, t0)])
            else:
                if fold > 0:
                    uvface(m, slot, [p0, p, R0], [(0.5, t0), (0.5, t), (0.5 + e0, t0)])
                    uvface(m, slot, [L0, p, p0], [(0.5 - e0, t0), (0.5, t), (0.5, t0)])
                else:
                    uvface(m, slot, [L0, p, R0], [(0.5 - e0, t0), (0.5, t), (0.5 + e0, t0)])
        prev = (p, R, L, t, e)
    return pts[-1]


def blob(m, slot, c, r, rng, squash=0.8, jitter=0.18):
    """Faceted foliage lump: an octahedron split once (32 faces), jittered."""
    V = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    F = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    cache = {}

    def mid(a, b):
        k = (min(a, b), max(a, b))
        if k not in cache:
            p = norm(tuple((V[a][i] + V[b][i]) / 2 for i in range(3)))
            V.append(p)
            cache[k] = len(V) - 1
        return cache[k]

    F2 = []
    for a, b, cc in F:
        ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
        F2 += [(a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)]
    P = [add(c, (v[0] * r * (1 + rng.uniform(-jitter, jitter)), v[1] * r * (1 + rng.uniform(-jitter, jitter)),
                 v[2] * r * squash * (1 + rng.uniform(-jitter, jitter)))) for v in V]
    def uv(i):
        v = V[i]
        return (0.5 + math.atan2(v[1], v[0]) / (2 * math.pi), 0.5 + 0.5 * v[2])
    for a, b, cc in F2:
        uva, uvb, uvc = uv(a), uv(b), uv(cc)
        # keep a face from wrapping the long way round the seam
        us = [uva[0], uvb[0], uvc[0]]
        if max(us) - min(us) > 0.5:
            uva, uvb, uvc = [((x + 1) if x < 0.5 else x, y) for x, y in (uva, uvb, uvc)]
        uvface(m, slot, [P[a], P[b], P[cc]], [uva, uvb, uvc])
    return P


# ------------------------------------------------------------------ plants
def agave(seed=31):
    rng = random.Random(seed)
    m = Mesh()
    n = 17
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        t = i / (n - 1)                                  # 0 = outer/older, 1 = inner/young
        az = i * golden * 2 + rng.uniform(-0.1, 0.1)
        elev = math.radians(18 + 55 * t + rng.uniform(-6, 6))
        L = (95 - 35 * t) * rng.uniform(0.9, 1.1)
        base = (math.cos(az) * 6, math.sin(az) * 6, 4 + 6 * t)
        blade(m, "Agave", base, az, elev, L, 9.0 - 2.5 * t, 18 * (1 - t), segs=3, fold=math.radians(35), taper=0.8)
    for i in range(3):                                   # dead outer leaves lying on the ground
        az = rng.uniform(0, 2 * math.pi)
        blade(m, "AgaveDead", (math.cos(az) * 10, math.sin(az) * 10, 2), az, math.radians(4), rng.uniform(60, 80), 7.0, 8,
              segs=2, fold=math.radians(20), taper=0.8)
    return m


def opuntia_pad(m, c, axis, side, length, width, thick=4.0, sides=8):
    """Flat oval pad centred at c, long axis `axis`, broad face across `side` (unit vectors)."""
    nrm = norm(cross(axis, side))
    ring = [add(add(c, axis, math.cos(2 * math.pi * k / sides) * length / 2), side, math.sin(2 * math.pi * k / sides) * width / 2)
            for k in range(sides)]
    front = [add(p, nrm, thick / 2) for p in ring]
    back = [add(p, nrm, -thick / 2) for p in ring]
    cf, cb = add(c, nrm, thick * 0.9), add(c, nrm, -thick * 0.9)
    uv = [(0.5 + 0.48 * math.sin(2 * math.pi * k / sides), 0.5 + 0.48 * math.cos(2 * math.pi * k / sides)) for k in range(sides)]
    for k in range(sides):
        k1 = (k + 1) % sides
        uvface(m, "Pad", [front[k], front[k1], cf], [uv[k], uv[k1], (0.5, 0.5)])
        uvface(m, "Pad", [back[k1], back[k], cb], [uv[k1], uv[k], (0.5, 0.5)])
        uvface(m, "Pad", [back[k], back[k1], front[k1], front[k]], [uv[k], uv[k1], uv[k1], uv[k]])
    return ring


def prickly_pear(seed=32):
    rng = random.Random(seed)
    m = Mesh()
    # pads: start with a few on the ground, each grows 1-3 more off its upper rim, leaning outwards
    pads = []
    stack = []
    for k in range(3):
        az = 2 * math.pi * k / 3 + rng.uniform(-0.4, 0.4)
        stack.append(((math.cos(az) * 12, math.sin(az) * 12, 0.0), norm((math.cos(az) * 0.35, math.sin(az) * 0.35, 1.0)), 0))
    count = 0
    while stack and count < 22:
        base, up, depth = stack.pop(0)
        L = rng.uniform(34, 44) * (1 - 0.06 * depth)
        W = L * rng.uniform(0.62, 0.75)
        turn = rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(0.15, 0.6)
        axis = norm((up[0] + math.sin(tilt) * math.cos(turn), up[1] + math.sin(tilt) * math.sin(turn), max(up[2], 0.35)))
        side = norm(cross(axis, (math.cos(turn + 1.3), math.sin(turn + 1.3), 0.0)))
        c = add(base, axis, L / 2 - 3)
        opuntia_pad(m, c, axis, side, L, W)
        pads.append((c, axis, side, L, W))
        count += 1
        if depth < 3:
            for k in range(rng.choice([1, 2, 2, 3]) if depth < 2 else rng.choice([0, 1, 1])):
                a = rng.uniform(-1.1, 1.1)
                rim = add(add(c, axis, math.cos(a) * L / 2 * 0.92), side, math.sin(a) * W / 2 * 0.92)
                nxt = norm(add(axis, side, math.sin(a) * 1.4))
                stack.append((rim, nxt, depth + 1))
    # fruit on the top rims of the outer pads
    for c, axis, side, L, W in pads[-7:]:
        for k in range(rng.choice([2, 3, 4])):
            a = rng.uniform(-0.6, 0.6)
            p = add(add(c, axis, math.cos(a) * L / 2), side, math.sin(a) * W / 2)
            r = 3.2
            P = [add(p, (r, 0, 0)), add(p, (0, r, 0)), add(p, (-r, 0, 0)), add(p, (0, -r, 0))]
            top, bot = add(p, axis, r * 1.6), add(p, axis, -r * 0.6)
            for i in range(4):
                tri(m, "Fruit", P[i], P[(i + 1) % 4], top)
                tri(m, "Fruit", P[(i + 1) % 4], P[i], bot)
    return m


def oleander(seed=33):
    rng = random.Random(seed)
    m = Mesh()
    # a few stems, a canopy of lumps, flowers on the outside
    for k in range(5):
        az = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        blade(m, "Stem", (0, 0, 0), az, math.radians(rng.uniform(55, 75)), rng.uniform(40, 60), 2.0, 0, segs=1, taper=0.0)
    lumps = []
    for k in range(8):
        az = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(20, 60)
        z = rng.uniform(45, 130) - rad * 0.4               # lower towards the edge: a mound from the ground up
        c = (math.cos(az) * rad, math.sin(az) * rad, z)
        r = rng.uniform(36, 50)
        P = blob(m, "Leaf" if k % 3 else "LeafDark", c, r, rng, squash=0.9)
        lumps.append((c, r, P))
    for c, r, P in lumps:
        for i in range(12):
            v = P[rng.randrange(len(P))]
            if v[2] < c[2] - r * 0.2:
                continue
            o = norm(sub(v, c))
            p = add(v, o, 1.5)
            a = norm(cross(o, Z)) if abs(o[2]) < 0.95 else (1.0, 0.0, 0.0)
            b = cross(o, a)
            s = 9.0
            for j in range(5):                                       # little five-petal star
                t0 = 2 * math.pi * j / 5
                q0 = add(add(p, a, math.cos(t0) * s), b, math.sin(t0) * s)
                q1 = add(add(p, a, math.cos(t0 + 0.6) * s * 0.4), b, math.sin(t0 + 0.6) * s * 0.4)
                tri(m, "Flower", p, q0, q1)
    return m


def saltbush(seed=34):
    rng = random.Random(seed)
    m = Mesh()
    for k in range(4):
        az = rng.uniform(0, 2 * math.pi)
        rad = 0 if k == 0 else rng.uniform(20, 35)
        c = (math.cos(az) * rad, math.sin(az) * rad, rng.uniform(22, 32))
        blob(m, "Salt", c, rng.uniform(30, 40), rng, squash=0.7, jitter=0.25)
    for k in range(10):                                              # dry twigs poking out
        az = rng.uniform(0, 2 * math.pi)
        blade(m, "Stem", (math.cos(az) * 25, math.sin(az) * 25, 25), az, math.radians(rng.uniform(15, 50)), rng.uniform(25, 40),
              1.0, 0, segs=1, taper=0.0)
    return m


# ------------------------------------------------------------------ grasses
def tuft(rng, m, n, hmin, hmax, elev, slots, width=2.6, splay=0.5, at=(0.0, 0.0)):
    for i in range(n):
        az = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, 5)
        base = (at[0] + math.cos(az) * r, at[1] + math.sin(az) * r, 0.0)
        h = rng.uniform(hmin, hmax)
        e = math.radians(rng.uniform(*elev))
        blade(m, rng.choice(slots), base, az + rng.uniform(-splay, splay), e, h, width * rng.uniform(0.8, 1.2), h * rng.uniform(0.1, 0.35),
              segs=2, taper=0.9)


def clump_spots(rng, n, radius):
    """Tuft positions for a clump: one in the middle, the rest scattered round it."""
    spots = [(0.0, 0.0)]
    while len(spots) < n:
        a, r = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.uniform(0.15, 1.0))
        spots.append((math.cos(a) * r, math.sin(a) * r))
    return spots


def grass_tuft(seed=41):
    """A clump of short dry tufts about 2.5 m across."""
    rng = random.Random(seed)
    m = Mesh()
    for i, at in enumerate(clump_spots(rng, 8, 120)):
        tuft(rng, m, 10 if i else 14, 28, 55, (50, 85), ["Straw", "Straw", "StrawPale", "Olive"], width=4.5, at=at)
    return m


def grass_seed(seed=42):
    """Taller tufts with oat-like seed heads, about 2 m across."""
    rng = random.Random(seed)
    m = Mesh()
    for at in clump_spots(rng, 6, 95):
        tuft(rng, m, 9, 40, 70, (60, 85), ["Straw", "StrawPale", "Olive"], width=4.5, at=at)
        for i in range(2):                                           # seed stalks with an oat-like head
            az = rng.uniform(0, 2 * math.pi)
            e = math.radians(rng.uniform(68, 84))
            h = rng.uniform(65, 90)
            base = (at[0], at[1], 0.0)
            tip = blade(m, "Seed", base, az, e, h, 1.0, 6, segs=2, taper=0.0)
            d = norm(sub(tip, base))
            side = (math.sin(az), -math.cos(az), 0.0)
            for k in range(3):
                c = add(tip, d, -5 * k)
                w = 2.8 - 0.5 * k
                tri(m, "Seed", add(c, side, -w), add(c, side, w), add(c, d, 7))
    return m


def grass_dead(seed=43):
    """Dead brown clumps splayed flat, about 2 m across."""
    rng = random.Random(seed)
    m = Mesh()
    for at in clump_spots(rng, 6, 100):
        tuft(rng, m, 12, 32, 58, (8, 35), ["DeadGrass", "DeadGrass", "Straw"], width=4.0, splay=0.3, at=at)
    return m


ITEMS = [("SM_Plant_Agave", agave), ("SM_Plant_PricklyPear", prickly_pear), ("SM_Plant_Oleander", oleander),
         ("SM_Plant_Saltbush", saltbush), ("SM_Grass_Tuft", grass_tuft), ("SM_Grass_Seed", grass_seed),
         ("SM_Grass_Dead", grass_dead)]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, f in ITEMS:
        m = f()
        m.write(os.path.join(OUT, name + ".obj"), name)
        print(name, m.tris())
