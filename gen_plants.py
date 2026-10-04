"""
LowPolyPlants generator: 4 low-poly plants, 4 dry grass clumps and 3 rock clutter clumps as OBJ + MTL.
Python 3, no dependencies.

    python gen_plants.py [out_dir]             OBJ for Blender / Godot / Unity
    python gen_plants.py out_dir --unreal      OBJ for Unreal's importer (V flipped), see tools/build_unreal_pack.py

Z up, centimetres, pivot on the ground. Leaves, pads and blades carry UVs for their texture (U across a leaf, 0.5 on
the midline; V from base to tip); foliage clusters and stones have UVs scaled to the surface so their texture
tiles evenly. Leaves and blades are single-sided strips: render with a TWO-SIDED material.

Plants:  SM_Plant_Agave        blue-grey rosette of thick pointed leaves, a few dead ones at the base
         SM_Plant_PricklyPear  bunny-ear Opuntia: flat oval pads growing off each other in fans
         SM_Plant_Oleander     dense dark-green flowering shrub, pink flowers
         SM_Plant_Saltbush     low grey-green shrub: woody stems and small leaf clusters
Grasses: SM_Grass_Tuft         clump of short dry tufts (~2.5 m across)
         SM_Grass_Seed         taller tufts with seed heads
         SM_Grass_Dead         dead brown clumps splayed flat
         SM_Grass_Tussock      bushy pale straw tussocks, roadside grass (~1.4 m patch)
Rocks:   SM_Rocks_Scatter      loose stones and pebbles (~1.8 m)
         SM_Rocks_Rubble       broken concrete and block chunks with stones (~1.4 m)
         SM_Rocks_Litter       stones with scraps of paper and plastic (~1.8 m)

Slots: see COLOURS (linear RGB, as used in Unreal).
"""
import math
import os
import random
import sys

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = ARGS[0] if ARGS else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")
# --unreal: negate V for Unreal's OBJ importer (it flips V), so leaf tips stay at V = 1 in the engine
FLIP_V = "--unreal" in sys.argv

# linear RGB slot colours (as used in Unreal); the MTL gets them in sRGB
COLOURS = {"Agave": (0.10, 0.16, 0.12), "AgaveDead": (0.20, 0.13, 0.06), "Pad": (0.10, 0.24, 0.05),
           "Fruit": (0.30, 0.03, 0.05), "Leaf": (0.04, 0.10, 0.03), "LeafDark": (0.025, 0.07, 0.02),
           "Flower": (0.55, 0.12, 0.22), "Stem": (0.12, 0.09, 0.05), "Salt": (0.11, 0.15, 0.08),
           "Straw": (0.20, 0.16, 0.06), "StrawPale": (0.30, 0.25, 0.12), "Olive": (0.11, 0.12, 0.04),
           "Seed": (0.26, 0.21, 0.10), "DeadGrass": (0.12, 0.07, 0.03),
           "Tussock": (0.30, 0.24, 0.12), "TussockPale": (0.42, 0.35, 0.20),
           "Stone": (0.16, 0.13, 0.10), "StoneLight": (0.24, 0.20, 0.15), "StoneDark": (0.09, 0.075, 0.06),
           "Concrete": (0.22, 0.21, 0.19), "Litter": (0.50, 0.49, 0.46), "LitterBlue": (0.08, 0.18, 0.36)}
UNTEXTURED = ("Flower", "Fruit", "Litter", "LitterBlue")
# slots with their own texture (diffuse map in the MTL); everything else textured gets T_PlantLeaf
SLOT_TEX = {"Pad": "T_CactusPad", "Leaf": "T_Foliage", "LeafDark": "T_Foliage", "Salt": "T_Foliage",
            "Stone": "T_Stone", "StoneLight": "T_Stone", "StoneDark": "T_Stone", "Concrete": "T_Stone"}


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
            f.write("# LowPolyPlants - %s (cm, Z up)\n" % comment)
            f.write(("o %s\n" % base) if FLIP_V else ("mtllib %s.mtl\no %s\n" % (base, base)))   # Unreal: no MTL, or the importer makes materials
            for p in self.v:
                f.write("v %.2f %.2f %.2f\n" % p)
            for t in self.vt:
                f.write("vt %.4f %.4f\n" % ((t[0], -t[1]) if FLIP_V else t))
            for n in self.vn:
                f.write("vn %.4f %.4f %.4f\n" % n)
            for slot in COLOURS:
                if slot in self.faces:
                    f.write("usemtl %s\n" % slot)
                    for face in self.faces[slot]:
                        f.write("f " + " ".join("%d/%d/%d" % c for c in face) + "\n")
        if FLIP_V:
            return
        with open(os.path.join(os.path.dirname(path), base + ".mtl"), "w") as f:
            for slot in COLOURS:
                if slot in self.faces:
                    r, g, b = (srgb(c) for c in COLOURS[slot])
                    f.write("newmtl %s\nKd %.4f %.4f %.4f\nKs 0 0 0\nd 1\nillum 1\n" % (slot, r, g, b))
                    if slot not in UNTEXTURED:
                        f.write("map_Kd %s_Surface.png\n" % SLOT_TEX.get(slot, "T_PlantLeaf"))
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


def blob(m, slot, c, r, rng, squash=0.8, jitter=0.18, tile=None, split=True):
    """Faceted foliage lump: an octahedron split once (32 faces), jittered. With tile (cm), UVs are scaled so the
    texture repeats every `tile` cm of surface, a whole number of times round the lump (no visible seam)."""
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

    F2 = [] if split else list(F)
    for a, b, cc in (F if split else ()):
        ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
        F2 += [(a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)]
    P = [add(c, (v[0] * r * (1 + rng.uniform(-jitter, jitter)), v[1] * r * (1 + rng.uniform(-jitter, jitter)),
                 v[2] * r * squash * (1 + rng.uniform(-jitter, jitter)))) for v in V]
    def uv(i):
        v = V[i]
        a = 0.5 + math.atan2(v[1], v[0]) / (2 * math.pi)
        if tile is None:
            return (a, 0.5 + 0.5 * v[2])
        tu = max(1, round(2 * math.pi * r / tile))
        return (a * tu, v[2] * r * squash / tile)
    for a, b, cc in F2:
        uva, uvb, uvc = uv(a), uv(b), uv(cc)
        # keep a face from wrapping the long way round the seam
        us = [uva[0], uvb[0], uvc[0]]
        span = 1 if tile is None else max(1, round(2 * math.pi * r / tile))
        if max(us) - min(us) > 0.5 * span:
            uva, uvb, uvc = [((x + span) if x < 0.5 * span else x, y) for x, y in (uva, uvb, uvc)]
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


def opuntia_pad(m, c, axis, side, length, width, thick=8.0, sides=12):
    """Plump obovate pad (Opuntia): wider towards its top, rounded, centred at c; long axis `axis`, broad face across
    `side`. A rim ring, an inner ring and a domed centre on each face. UVs are planar across the face
    (U across, V along the pad, 0.5 = centre) for the areole texture."""
    nrm = norm(cross(axis, side))
    def ring(scale):
        pts, uvs = [], []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ca, sa = math.cos(a), math.sin(a)
            f = (1 + 0.22 * ca) * (1 - 0.18 * max(0.0, -ca))       # broad top, narrower base
            pts.append(add(add(c, axis, ca * length / 2 * scale), side, sa * width / 2 * f * scale))
            uvs.append((0.5 + 0.48 * sa * f * scale, 0.5 + 0.48 * ca * scale))
        return pts, uvs
    rim, ruv = ring(1.0)
    inner, iuv = ring(0.58)
    top = add(c, axis, length * 0.06)
    for s_ in (1, -1):
        r_ = [add(p, nrm, s_ * thick * 0.35) for p in rim]
        i_ = [add(p, nrm, s_ * thick * 0.95) for p in inner]
        cc = add(top, nrm, s_ * thick * 1.25)
        for k in range(sides):
            k1 = (k + 1) % sides
            if s_ > 0:
                uvface(m, "Pad", [r_[k], r_[k1], i_[k1], i_[k]], [ruv[k], ruv[k1], iuv[k1], iuv[k]])
                uvface(m, "Pad", [i_[k], i_[k1], cc], [iuv[k], iuv[k1], (0.5, 0.53)])
            else:
                uvface(m, "Pad", [r_[k1], r_[k], i_[k], i_[k1]], [ruv[k1], ruv[k], iuv[k], iuv[k1]])
                uvface(m, "Pad", [i_[k1], i_[k], cc], [iuv[k1], iuv[k], (0.5, 0.53)])
    front = [add(p, nrm, thick * 0.35) for p in rim]
    back = [add(p, nrm, -thick * 0.35) for p in rim]
    for k in range(sides):
        k1 = (k + 1) % sides
        uvface(m, "Pad", [back[k], back[k1], front[k1], front[k]], [ruv[k], ruv[k1], ruv[k1], ruv[k]])
    return rim


def rotate(v, axis, ang):
    """Rodrigues rotation of v about a unit axis."""
    c_, s_ = math.cos(ang), math.sin(ang)
    k = axis
    kxv = cross(k, v)
    kdv = k[0] * v[0] + k[1] * v[1] + k[2] * v[2]
    return tuple(v[i] * c_ + kxv[i] * s_ + k[i] * kdv * (1 - c_) for i in range(3))


def prickly_pear(seed=32):
    """Bunny-ear style Opuntia: three tall pads from the ground, each sprouting one or two more off its top, fanning
    out mostly in the parent's plane - upright and narrow like a real clump, about 1.2 m tall."""
    rng = random.Random(seed)
    m = Mesh()
    stack = []
    for k in range(3):
        az = 2 * math.pi * k / 3 + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.08, 0.3)
        axis = norm((math.cos(az) * math.sin(lean), math.sin(az) * math.sin(lean), math.cos(lean)))
        side = norm(cross(axis, (math.cos(az + 1.57 + rng.uniform(-0.4, 0.4)), math.sin(az + 1.57), 0.0)))
        side = norm(cross(side, axis))
        stack.append(((math.cos(az) * 14, math.sin(az) * 14, -4.0), axis, side, 0))
    count = 0
    while stack and count < 13:
        base, axis, side, depth = stack.pop(0)
        L = rng.uniform(46, 58) * (1 - 0.12 * depth)
        W = L * rng.uniform(0.46, 0.54)
        c = add(base, axis, L / 2 - 4)
        opuntia_pad(m, c, axis, side, L, W)
        count += 1
        if depth < 2:
            for k in range(2 if depth == 0 else rng.choice([0, 1, 1, 1])):
                a = (rng.uniform(0.25, 0.75) if k == 0 else rng.uniform(-0.75, -0.25)) if depth == 0 else rng.uniform(-0.65, 0.65)   # where on the top rim it buds (both shoulders on a base pad)
                rim = add(add(c, axis, math.cos(a) * L / 2 * 0.9), side, math.sin(a) * W / 2 * 1.1 * 0.9)
                fan = math.copysign(rng.uniform(0.35, 0.8), a if abs(a) > 0.05 else rng.uniform(-1, 1))
                nrm = norm(cross(axis, side))
                nax = rotate(axis, nrm, -fan)                        # fan out in the parent's plane
                if nax[2] < 0.45:                                    # keep it growing upwards
                    nax = norm((nax[0], nax[1], 0.45))
                nside = norm(cross(cross(nax, rotate(side, nax, rng.uniform(-0.35, 0.35))), nax))
                stack.append((rim, nax, nside, depth + 1))
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
        P = blob(m, "Leaf" if k % 3 else "LeafDark", c, r, rng, squash=0.9, tile=200)
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
    """Low dry shrub (Atriplex): a woody base of forking twigs carrying lots of small silvery leaf clusters in a loose
    dome with gaps - reads as a bush rather than a boulder. About 1.1 m across, 0.6 m tall."""
    rng = random.Random(seed)
    m = Mesh()
    tips = []
    for k in range(7):                                               # main stems fanning out from the root crown
        az = 2 * math.pi * k / 7 + rng.uniform(-0.3, 0.3)
        tip = blade(m, "Stem", (0, 0, 0), az, math.radians(rng.uniform(30, 55)), rng.uniform(32, 42), 1.6, 3, segs=2, taper=0.6)
        tips.append((tip, az))
        for j in range(2):                                           # forks
            a2 = az + rng.uniform(-0.6, 0.6)
            t2 = blade(m, "Stem", tip, a2, math.radians(rng.uniform(15, 60)), rng.uniform(12, 20), 1.0, 2, segs=1, taper=0.0)
            tips.append((t2, a2))
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(14):                                              # leaf clusters on a loose dome
        t = (i + 0.5) / 14
        el = math.asin(t * 0.95)                                    # spread over the dome
        az = i * golden + rng.uniform(-0.2, 0.2)
        R, Hd = 45.0, 38.0
        c = (math.cos(az) * math.cos(el) * R, math.sin(az) * math.cos(el) * R, 14 + math.sin(el) * Hd + rng.uniform(-4, 4))
        blob(m, "Salt", c, rng.uniform(11, 16), rng, squash=0.75, jitter=0.3, tile=60)
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


def tussock(rng, m, at, h, slots, n=60):
    """One bushy tussock: a dense fountain of fine blades from a ~25 cm crown, arching out and over."""
    for i in range(n):
        az = rng.uniform(0, 2 * math.pi)
        r = 12 * math.sqrt(rng.uniform(0, 1))
        base = (at[0] + math.cos(az) * r, at[1] + math.sin(az) * r, 0.0)
        out = r / 12.0                                               # crown edge -> leans out more
        e = math.radians(rng.uniform(55, 85) - 25 * out)
        L = h * rng.uniform(0.6, 1.1)
        blade(m, rng.choice(slots), base, az + rng.uniform(-0.25, 0.25), e, L, rng.uniform(1.4, 2.0),
              L * rng.uniform(0.25, 0.6) * (0.6 + out), segs=2, taper=0.9)


def grass_tussock(seed=44):
    """Tufty dry roadside grass: 4-5 bushy pale straw tussocks 40-70 cm tall in a ~1.4 m patch."""
    rng = random.Random(seed)
    m = Mesh()
    for i, at in enumerate(clump_spots(rng, 5, 60)):
        tussock(rng, m, at, rng.uniform(40, 70), ["Tussock", "Tussock", "TussockPale", "StrawPale"])
    return m


def stones(rng, m, n, rmin, rmax, radius, slots=("Stone", "Stone", "StoneLight", "StoneDark")):
    """Half-buried faceted stones scattered over a disc."""
    for _ in range(n):
        a, d = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.uniform(0, 1))
        r = rng.uniform(rmin, rmax)
        sq = rng.uniform(0.45, 0.75)
        blob(m, rng.choice(slots), (math.cos(a) * d, math.sin(a) * d, r * sq * 0.2), r, rng, squash=sq * 0.8,
             jitter=0.25, tile=40, split=r > 5)


def flake(rng, m, slot, at, size):
    """Flat bit of litter (paper / plastic) lying on the ground, slightly crumpled."""
    a = rng.uniform(0, math.pi)
    c, s_ = math.cos(a), math.sin(a)
    w, l = size * rng.uniform(0.5, 1.0), size
    pts = [(-l, -w), (l, -w * 0.8), (l * 0.9, w), (-l * 0.8, w * 0.9)]
    P = [(at[0] + x * c - y * s_, at[1] + x * s_ + y * c, 0.6 + rng.uniform(0, 1.5)) for x, y in pts]
    uvface(m, slot, P, [(0, 0), (1, 0), (1, 1), (0, 1)])


def rocks_scatter(seed=51):
    """Loose stones over ~1.8 m: lots of pebbles and fist-sized stones, a couple of bigger ones."""
    rng = random.Random(seed)
    m = Mesh()
    stones(rng, m, 16, 3, 9, 90)
    stones(rng, m, 3, 12, 22, 70)
    return m


def rocks_rubble(seed=52):
    """Builders' rubble: broken concrete and block chunks with stones, ~1.4 m."""
    rng = random.Random(seed)
    m = Mesh()
    for _ in range(9):
        a, d = rng.uniform(0, 2 * math.pi), 55 * math.sqrt(rng.uniform(0, 1))
        r = rng.uniform(9, 22)
        blob(m, rng.choice(["Concrete", "Concrete", "StoneLight"]), (math.cos(a) * d, math.sin(a) * d, r * 0.3), r, rng,
             squash=rng.uniform(0.5, 0.8), jitter=0.4, tile=40, split=False)
    stones(rng, m, 10, 3, 8, 75)
    return m


def rocks_litter(seed=53):
    """Stones with roadside litter: scraps of paper and plastic, ~1.8 m."""
    rng = random.Random(seed)
    m = Mesh()
    stones(rng, m, 11, 3, 10, 85)
    for _ in range(5):
        a, d = rng.uniform(0, 2 * math.pi), 80 * math.sqrt(rng.uniform(0, 1))
        flake(rng, m, rng.choice(["Litter", "Litter", "LitterBlue"]), (math.cos(a) * d, math.sin(a) * d), rng.uniform(6, 14))
    return m


ITEMS = [("SM_Plant_Agave", agave), ("SM_Plant_PricklyPear", prickly_pear), ("SM_Plant_Oleander", oleander),
         ("SM_Plant_Saltbush", saltbush), ("SM_Grass_Tuft", grass_tuft), ("SM_Grass_Seed", grass_seed),
         ("SM_Grass_Dead", grass_dead), ("SM_Grass_Tussock", grass_tussock), ("SM_Rocks_Scatter", rocks_scatter),
         ("SM_Rocks_Rubble", rocks_rubble), ("SM_Rocks_Litter", rocks_litter)]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, f in ITEMS:
        m = f()
        m.write(os.path.join(OUT, name + ".obj"), name)
        print(name, m.tris())
