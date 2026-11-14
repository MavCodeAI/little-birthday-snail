#!/usr/bin/env python3
"""A small birthday, delivered slowly.

A snail carries a lit birthday cake up the hill at dusk. The candle is the only
warm light in the picture, so every surface leans toward it.

Every pixel is drawn here with plain Python: no network, no third party
packages, and no randomness beyond a fixed sequence, so two runs write
byte-identical files. The image goes to $MAKEFUN_OUTPUT_DIR (or /output inside
the grader) as entry.png.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

buf = bytearray(W * H * 3)

# the candle flame sits here; the shading of every rounded surface leans at it
LIGHT = (512.0, 332.0)


# ---------------------------------------------------------------------------
# canvas primitives
# ---------------------------------------------------------------------------


def _blend(i, r, g, b, a):
    if a <= 0.0:
        return
    if a >= 1.0:
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b
        return
    ia = 1.0 - a
    buf[i] = int(buf[i] * ia + r * a + 0.5)
    buf[i + 1] = int(buf[i + 1] * ia + g * a + 0.5)
    buf[i + 2] = int(buf[i + 2] * ia + b * a + 0.5)


def _add(i, r, g, b, a):
    if a <= 0.0:
        return
    v = buf[i] + r * a
    buf[i] = 255 if v > 255 else int(v)
    v = buf[i + 1] + g * a
    buf[i + 1] = 255 if v > 255 else int(v)
    v = buf[i + 2] + b * a
    buf[i + 2] = 255 if v > 255 else int(v)


def disc(cx, cy, rad, color, a=1.0):
    """Flat filled circle with one pixel of anti-aliasing."""
    r, g, b = color
    x0 = max(0, int(cx - rad - 1))
    x1 = min(W - 1, int(cx + rad + 1))
    y0 = max(0, int(cy - rad - 1))
    y1 = min(H - 1, int(cy + rad + 1))
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        base = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            cov = rad + 0.5 - math.sqrt(dx * dx + dy * dy)
            if cov <= 0.0:
                continue
            _blend(base + x * 3, r, g, b, (1.0 if cov > 1.0 else cov) * a)


def disc_shaded(cx, cy, rad, shade, a=1.0):
    """Circle whose colour is a function of position, so shapes melt together."""
    x0 = max(0, int(cx - rad - 1))
    x1 = min(W - 1, int(cx + rad + 1))
    y0 = max(0, int(cy - rad - 1))
    y1 = min(H - 1, int(cy + rad + 1))
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        base = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            cov = rad + 0.5 - math.sqrt(dx * dx + dy * dy)
            if cov <= 0.0:
                continue
            r, g, b = shade(x + 0.5, y + 0.5)
            _blend(base + x * 3, r, g, b, (1.0 if cov > 1.0 else cov) * a)


def capsule(cx0, cy0, cx1, cy1, rad, color, a=1.0):
    """Thick line with round ends."""
    r, g, b = color
    ax = cx1 - cx0
    ay = cy1 - cy0
    ll = ax * ax + ay * ay
    lo = max(0, int(min(cx0, cx1) - rad - 1))
    hi = min(W - 1, int(max(cx0, cx1) + rad + 1))
    to = max(0, int(min(cy0, cy1) - rad - 1))
    bo = min(H - 1, int(max(cy0, cy1) + rad + 1))
    for y in range(to, bo + 1):
        base = y * W * 3
        py = y + 0.5
        for x in range(lo, hi + 1):
            px = x + 0.5
            t = 0.0 if ll <= 1e-9 else ((px - cx0) * ax + (py - cy0) * ay) / ll
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            dx = px - (cx0 + ax * t)
            dy = py - (cy0 + ay * t)
            cov = rad + 0.5 - math.sqrt(dx * dx + dy * dy)
            if cov <= 0.0:
                continue
            _blend(base + x * 3, r, g, b, (1.0 if cov > 1.0 else cov) * a)


def capsule_shaded(cx0, cy0, cx1, cy1, rad, shade, a=1.0):
    ax = cx1 - cx0
    ay = cy1 - cy0
    ll = ax * ax + ay * ay
    lo = max(0, int(min(cx0, cx1) - rad - 1))
    hi = min(W - 1, int(max(cx0, cx1) + rad + 1))
    to = max(0, int(min(cy0, cy1) - rad - 1))
    bo = min(H - 1, int(max(cy0, cy1) + rad + 1))
    for y in range(to, bo + 1):
        base = y * W * 3
        py = y + 0.5
        for x in range(lo, hi + 1):
            px = x + 0.5
            t = 0.0 if ll <= 1e-9 else ((px - cx0) * ax + (py - cy0) * ay) / ll
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            dx = px - (cx0 + ax * t)
            dy = py - (cy0 + ay * t)
            cov = rad + 0.5 - math.sqrt(dx * dx + dy * dy)
            if cov <= 0.0:
                continue
            r, g, b = shade(px, py)
            _blend(base + x * 3, r, g, b, (1.0 if cov > 1.0 else cov) * a)


def glow(cx, cy, rad, color, strength):
    """Soft additive light."""
    r, g, b = color
    x0 = max(0, int(cx - rad))
    x1 = min(W - 1, int(cx + rad))
    y0 = max(0, int(cy - rad))
    y1 = min(H - 1, int(cy + rad))
    inv = 1.0 / rad
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        base = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            t = 1.0 - math.sqrt(dx * dx + dy * dy) * inv
            if t <= 0.0:
                continue
            _add(base + x * 3, r, g, b, strength * t * t)


def fill_below(edge, color, alpha=1.0, rim=None):
    """Fill every row under a per-column edge line, with a soft one pixel rim."""
    r, g, b = color
    for x in range(W):
        top = int(edge[x])
        if top < 0:
            top = 0
        if top > H:
            continue
        frac = edge[x] - top
        col = x * 3
        if rim is not None and top < H:
            _blend(top * W * 3 + col, rim[0], rim[1], rim[2], 1.0 - frac)
        start = top + 1
        if alpha >= 1.0:
            for y in range(start, H):
                i = y * W * 3 + col
                buf[i] = r
                buf[i + 1] = g
                buf[i + 2] = b
            if start - 1 >= 0:
                _blend((start - 1) * W * 3 + col, r, g, b, frac)
        else:
            for y in range(start, H):
                _blend(y * W * 3 + col, r, g, b, alpha)


def polyfill(pts, color, a=1.0):
    """Polygon fill, 4x vertical supersampling for the edges."""
    r, g, b = color
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1 + 1):
        spans = []
        for s in range(4):
            sy = y + (s + 0.5) / 4.0
            xcross = []
            for i in range(n):
                xa, ya = pts[i]
                xb, yb = pts[(i + 1) % n]
                if (ya <= sy < yb) or (yb <= sy < ya):
                    t = (sy - ya) / (yb - ya)
                    xcross.append(xa + (xb - xa) * t)
            xcross.sort()
            for i in range(0, len(xcross) - 1, 2):
                spans.append((xcross[i], xcross[i + 1]))
        if not spans:
            continue
        spans.sort()
        merged = [list(spans[0])]
        for s in spans[1:]:
            if s[0] <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], s[1])
            else:
                merged.append(list(s))
        for xa, xb in merged:
            for x in range(max(0, int(xa)), min(W - 1, int(xb)) + 1):
                w = min(xb, x + 1) - max(xa, x)
                if w > 0:
                    _blend(y * W * 3 + x * 3, r, g, b, min(1.0, w) * a)


def rounded_rect(x0, y0, x1, y1, rad, color, a=1.0):
    pts = []
    for cx, cy, start in ((x1 - rad, y0 + rad, -math.pi / 2), (x1 - rad, y1 - rad, 0.0),
                          (x0 + rad, y1 - rad, math.pi / 2), (x0 + rad, y0 + rad, math.pi)):
        for i in range(9):
            ang = start + (math.pi / 2) * (i / 8.0)
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    polyfill(pts, color, a)


# ---------------------------------------------------------------------------
# deterministic pseudo random
# ---------------------------------------------------------------------------

_seed = 20261114


def rnd():
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed / 2147483648.0


def rrange(a, b):
    return a + (b - a) * rnd()


# ---------------------------------------------------------------------------
# sky and land
# ---------------------------------------------------------------------------

SKY = [
    (0.00, (0x0B, 0x11, 0x28)),
    (0.28, (0x1B, 0x29, 0x54)),
    (0.48, (0x3A, 0x3B, 0x72)),
    (0.62, (0x74, 0x49, 0x73)),
    (0.71, (0xCC, 0x67, 0x59)),
    (0.79, (0xF6, 0xA4, 0x5F)),
]


def sky():
    for y in range(H):
        t = y / (H - 1.0)
        c0, c1, lt = SKY[0][1], SKY[-1][1], 1.0
        for i in range(len(SKY) - 1):
            if SKY[i][0] <= t <= SKY[i + 1][0]:
                c0, c1 = SKY[i][1], SKY[i + 1][1]
                lt = (t - SKY[i][0]) / (SKY[i + 1][0] - SKY[i][0])
                break
        r = int(c0[0] + (c1[0] - c0[0]) * lt)
        g = int(c0[1] + (c1[1] - c0[1]) * lt)
        b = int(c0[2] + (c1[2] - c0[2]) * lt)
        row = bytearray()
        for x in range(W):
            n = ((x * 7 + y * 13 + (x * y) % 11) % 3) - 1
            row += bytes((max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n))))
        buf[y * W * 3:(y + 1) * W * 3] = row


def stars():
    for _ in range(46):
        x, y = rrange(0, W), rrange(0, 430)
        fade = 1.0 - y / 470.0
        if fade <= 0:
            continue
        disc(x, y, rrange(0.9, 1.9), (255, 244, 220), 0.18 + 0.42 * fade * rnd())
    for x, y in ((150, 120), (836, 88), (268, 56)):
        glow(x, y, 14, (255, 240, 200), 0.16)
        disc(x, y, 2.4, (255, 252, 240), 0.8)


def hills():
    edge = [686 + 30 * math.sin((x / W) * 3.1 + 0.6) + 14 * math.sin((x / W) * 7.7 + 2.1) for x in range(W)]
    fill_below(edge, (0x22, 0x36, 0x4E), 1.0, rim=(0x4E, 0x6C, 0x77))

    edge = [778 + 24 * math.sin((x / W) * 2.2 + 2.4) + 11 * math.sin((x / W) * 5.3 + 1.0) for x in range(W)]
    fill_below(edge, (0x13, 0x29, 0x32), 1.0, rim=(0x2E, 0x54, 0x55))

    edge = [862 + 9 * math.sin((x / W) * 4.0 + 1.2) for x in range(W)]
    fill_below(edge, (0x0B, 0x1D, 0x22), 1.0, rim=(0x25, 0x41, 0x3D))


def horizon_haze():
    for y in range(600, 720):
        t = 1.0 - abs(y - 678) / 78.0
        if t <= 0.0:
            continue
        a = 0.16 * t * t
        row = y * W * 3
        for x in range(W):
            _blend(row + x * 3, 0xF7, 0xA0, 0x76, a)


def blade(x, y, h, lean, w, color, alpha=1.0, steps=5):
    px, py = x, y
    for s in range(1, steps + 1):
        t = s / steps
        nx = x + lean * t * t
        ny = y - h * t
        capsule(px, py, nx, ny, w * (1.0 - 0.8 * t), color, alpha)
        px, py = nx, ny


def meadow():
    for i in range(12):
        cx = rrange(0, W)
        cy = 900 + rrange(-10, 14)
        for j in range(7):
            blade(cx + rrange(-34, 34), cy + rrange(-4, 10), rrange(26, 64),
                  rrange(-16, 16), rrange(3.5, 6.5), (0x10, 0x26, 0x26), 0.8, 4)
    for _ in range(110):
        x = rrange(0, W)
        base = 868 + 9 * math.sin((x / W) * 4.0 + 1.2)
        blade(x, base + rrange(0, 26), rrange(14, 46), rrange(-14, 14),
              rrange(1.5, 2.8), (0x15, 0x31, 0x31), 0.95)
    for _ in range(24):
        x = rrange(0, W)
        base = 866 + 9 * math.sin((x / W) * 4.0 + 1.2)
        blade(x, base + rrange(0, 24), rrange(26, 62), rrange(-18, 18),
              rrange(1.8, 3.2), (0x1D, 0x3D, 0x37), 0.9)



def fireflies(count):
    for _ in range(count):
        x, y = rrange(60, W - 60), rrange(500, 830)
        glow(x, y, rrange(20, 34), (255, 212, 120), rrange(0.14, 0.26))
        disc(x, y, rrange(1.6, 2.6), (255, 246, 190), 0.8)


# ---------------------------------------------------------------------------
# the snail
# ---------------------------------------------------------------------------

BODY_TOP = (0xFD, 0xF1, 0xDC)
BODY_BOTTOM = (0xC8, 0x9C, 0x6E)
BODY_DARK = (0xA8, 0x76, 0x4F)
SHELL_C = (506.0, 604.0)
SHELL_R = 142.0


def body_shade(x, y):
    """Creamy body, darker underneath, warmed by the candle above it."""
    t = (y - 620.0) / 260.0
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    r = 0xFF + (0xAE - 0xFF) * t
    g = 0xF0 + (0x7C - 0xF0) * t
    b = 0xD6 + (0x4E - 0xD6) * t
    dx = (x - LIGHT[0]) / 430.0
    dy = (y - LIGHT[1]) / 430.0
    warm = 1.0 - (dx * dx + dy * dy)
    if warm > 0.0:
        r += 26 * warm
        g += 18 * warm
        b += 8 * warm
    return (min(255, int(r)), min(255, int(g)), min(255, int(b)))



def snail_trail():
    """The silver path it came in on, catching a little of the candle light."""
    pts = []
    for i in range(60):
        t = i / 59.0
        x = 20 + 210 * t
        y = 902 - 34 * t + 12 * math.sin(t * 5.2)
        pts.append((x, y))
    for i in range(len(pts) - 1):
        capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 5.4 - 2.0 * (i / 59.0),
                (0x9F, 0xC8, 0xC4), 0.12)
    for i in range(len(pts) - 1):
        capsule(pts[i][0], pts[i][1] - 2, pts[i + 1][0], pts[i + 1][1] - 2,
                1.8 - 0.8 * (i / 59.0), (0xE6, 0xF8, 0xF0), 0.16)


def snail_shadow():
    cx, cy = 520.0, 872.0
    for i in range(14):
        rad = 250 - i * 16
        a = 0.05
        x0 = int(cx - rad)
        x1 = int(cx + rad)
        for y in range(int(cy) - 10, int(cy) + 14):
            dy = (y + 0.5 - cy) / 16.0
            if abs(dy) > 1.0:
                continue
            span = rad * math.sqrt(1.0 - dy * dy)
            for x in range(max(0, int(cx - span)), min(W - 1, int(cx + span)) + 1):
                dx = (x + 0.5 - cx) / span if span else 2.0
                if abs(dx) <= 1.0:
                    _blend(y * W * 3 + x * 3, 0x04, 0x0C, 0x10, a)


SPINE = [
    (248, 840, 14), (262, 837, 22), (278, 833, 30), (296, 828, 37),
    (316, 823, 43), (338, 818, 47), (362, 814, 50), (390, 811, 52),
    (420, 809, 54), (452, 808, 55), (484, 807, 56), (516, 807, 56),
    (548, 806, 56), (578, 804, 57), (606, 800, 58), (632, 793, 61),
    (656, 782, 64), (676, 766, 68), (692, 746, 71), (702, 722, 74),
    (708, 696, 76), (710, 670, 77), (709, 646, 77), (705, 624, 72),
    (700, 606, 62),
]


def contact_shadow():
    for i in range(18):
        x = 240 + i * 30
        w = 34 + 10 * math.sin(i * 0.7)
        for y in range(846, 884):
            t = 1.0 - abs(y - 862) / 26.0
            if t <= 0:
                continue
            for xx in range(int(x - w), int(x + w)):
                if 0 <= xx < W:
                    _blend(y * W * 3 + xx * 3, 0x05, 0x0F, 0x12, 0.16 * t)


def snail_body():
    """One smooth tube: coverage is unioned first, then shaded once, so the
    joins between segments never leave a seam."""
    x0, y0, x1, y1 = 225, 460, 800, 900
    bw = x1 - x0
    cov = bytearray(bw * (y1 - y0))

    def add_cap(ax, ay, bx, by, rad):
        dx = bx - ax
        dy = by - ay
        ll = dx * dx + dy * dy
        lo = max(0, int(min(ax, bx) - rad - 1) - x0)
        hi = min(bw - 1, int(max(ax, bx) + rad + 1) - x0)
        lo_y = max(0, int(min(ay, by) - rad - 1) - y0)
        hi_y = min(y1 - y0 - 1, int(max(ay, by) + rad + 1) - y0)
        for yy in range(lo_y, hi_y + 1):
            py = yy + y0 + 0.5
            base = yy * bw
            for xx in range(lo, hi + 1):
                px = xx + x0 + 0.5
                t = 0.0 if ll <= 1e-9 else ((px - ax) * dx + (py - ay) * dy) / ll
                if t < 0.0:
                    t = 0.0
                elif t > 1.0:
                    t = 1.0
                ddx = px - (ax + dx * t)
                ddy = py - (ay + dy * t)
                c = rad + 0.5 - math.sqrt(ddx * ddx + ddy * ddy)
                if c <= 0.0:
                    continue
                if c > 1.0:
                    c = 1.0
                v = int(c * 255.0)
                if v > cov[base + xx]:
                    cov[base + xx] = v

    for i in range(len(SPINE) - 1):
        ax, ay, ar = SPINE[i]
        bx, by, br = SPINE[i + 1]
        add_cap(ax, ay, bx, by, (ar + br) * 0.5)

    # eye stalks
    add_cap(694, 590, 672, 492, 13)
    add_cap(724, 592, 754, 502, 13)

    for yy in range(y1 - y0):
        base = yy * bw
        py = yy + y0 + 0.5
        for xx in range(bw):
            c = cov[base + xx]
            if not c:
                continue
            px = xx + x0 + 0.5
            r, g, b = body_shade(px, py)
            _blend((int(py - 0.5)) * W * 3 + (int(px - 0.5)) * 3, r, g, b, c / 255.0)

    # form: shade toward the silhouette so the tube reads as round
    for xx in range(bw):
        top = None
        bottom = None
        for yy in range(y1 - y0):
            if cov[yy * bw + xx] > 120:
                if top is None:
                    top = yy
                bottom = yy
        if top is None:
            continue
        px = xx + x0
        for d in range(34):
            yy = bottom - d
            if yy <= top:
                break
            a = 0.42 * (1.0 - d / 34.0) ** 1.5
            _blend((yy + y0) * W * 3 + px * 3, 0x8A, 0x5C, 0x36, a)
        for d in range(12):
            yy = top + d
            if yy >= bottom:
                break
            a = 0.30 * (1.0 - d / 12.0) ** 1.3
            _blend((yy + y0) * W * 3 + px * 3, 0xFF, 0xF6, 0xE2, a)

    # eyes
    for ex, ey in ((672, 486), (754, 496)):
        disc(ex, ey, 23, (0xFF, 0xFF, 0xFF), 1.0)
        disc(ex - 1, ey - 2, 13, (0x2B, 0x22, 0x34), 1.0)
        disc(ex + 2.5, ey - 7, 4.4, (0xFF, 0xFF, 0xFF), 0.95)
        disc(ex - 6.5, ey + 1, 2.2, (0xFF, 0xFF, 0xFF), 0.45)
        capsule(ex - 18, ey - 20, ex + 14, ey - 14, 3.2, BODY_DARK, 0.38)

    # blush, kept soft
    disc(644, 662, 32, (0xF2, 0x8C, 0x8C), 0.10)
    disc(644, 662, 18, (0xF2, 0x8C, 0x8C), 0.10)
    disc(788, 664, 28, (0xF2, 0x8C, 0x8C), 0.10)

    # smile
    pts = []
    for i in range(17):
        ang = math.pi * (0.18 + 0.62 * (i / 16.0))
        pts.append((710 + 34 * math.cos(ang), 676 + 21 * math.sin(ang)))
    for i in range(len(pts) - 1):
        capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 3.4, BODY_DARK, 0.9)



def shell_shade(x, y):
    cx, cy = SHELL_C
    dx = (x - cx) / SHELL_R
    dy = (y - cy) / SHELL_R
    # light from the upper left, plus the candle above
    lit = 0.5 - 0.42 * dy - 0.30 * dx
    if lit < 0.0:
        lit = 0.0
    elif lit > 1.0:
        lit = 1.0
    r = 0xC6 + (0xF8 - 0xC6) * lit
    g = 0x74 + (0xCB - 0x74) * lit
    b = 0x4A + (0x96 - 0x4A) * lit
    return (int(r), int(g), int(b))


def shell():
    cx, cy = SHELL_C
    disc_shaded(cx, cy, SHELL_R, shell_shade)

    # spiral, kept inside the shell and thinning to a point at the centre
    turns = 3.05
    total = turns * 2 * math.pi
    a0 = 6.0
    b0 = (SHELL_R - 20.0 - a0) / total
    steps = 320
    prev = None
    for i in range(steps + 1):
        t = i / steps
        ang = t * total + 0.9
        rad = a0 + b0 * (t * total)
        px = cx + rad * math.cos(ang)
        py = cy + rad * math.sin(ang)
        width = 2.5 + 20.5 * t
        if (i // 26) % 2 == 0:
            col = (0x9C, 0x46, 0x33)
        else:
            col = (0xF9, 0xD2, 0x9E)
        if prev is None:
            disc(px, py, width * 0.5, col, 0.9)
        else:
            capsule(prev[0], prev[1], px, py, width * 0.5, col, 0.9)
        prev = (px, py)

    disc(cx, cy, 7.0, (0xF9, 0xD2, 0x9E), 0.9)

    # warm light caught on the crown of the shell, where the flame reaches it
    for i in range(52):
        t = i / 51.0
        ang = math.pi * (-0.95 + 0.95 * t)
        px = cx + (SHELL_R - 6) * math.cos(ang)
        py = cy + (SHELL_R - 6) * math.sin(ang)
        disc(px, py, 5.0 - 2.2 * t, (0xFF, 0xC9, 0x8A), 0.10)
        disc(px, py, 2.4 - 1.1 * t, (0xFF, 0xF0, 0xD2), 0.22)



def cake():
    cream = (0xFF, 0xF1, 0xD9)
    icing = (0xF7, 0x99, 0xAE)
    icing_deep = (0xDD, 0x71, 0x8A)
    sponge_top = (0xFA, 0xE2, 0xBA)
    sponge_bot = (0xE2, 0xB4, 0x7C)
    bx = int(SHELL_C[0])
    base = int(SHELL_C[1] - SHELL_R + 8)

    # shadow the plate casts on the shell
    for i in range(9):
        disc(bx, base + 20 + i, 96 - i * 5, (0x7A, 0x3F, 0x2C), 0.05)

    # plate
    rounded_rect(bx - 72, base - 2, bx + 72, base + 10, 6, cream, 0.95)
    rounded_rect(bx - 64, base + 6, bx + 64, base + 15, 5, (0xE3, 0xC0, 0x95), 0.85)

    # bottom tier
    tier1_top, tier1_bot = base - 74, base - 2
    for y in range(tier1_top, tier1_bot):
        t = (y - tier1_top) / float(tier1_bot - tier1_top)
        r = int(sponge_top[0] + (sponge_bot[0] - sponge_top[0]) * t)
        g = int(sponge_top[1] + (sponge_bot[1] - sponge_top[1]) * t)
        b = int(sponge_top[2] + (sponge_bot[2] - sponge_top[2]) * t)
        for x in range(bx - 72, bx + 73):
            _blend(y * W * 3 + x * 3, r, g, b, 1.0)
    rounded_rect(bx - 74, tier1_top, bx + 74, tier1_bot, 8, sponge_top, 1.0)

    # icing cap and drips on the bottom tier
    rounded_rect(bx - 76, tier1_top - 8, bx + 76, tier1_top + 14, 9, icing, 1.0)
    for dx, length in ((-58, 16), (-34, 26), (-7, 20), (20, 28), (46, 18), (64, 12)):
        capsule(bx + dx, tier1_top + 8, bx + dx, tier1_top + 8 + length, 9.5, icing, 1.0)
        disc(bx + dx, tier1_top + 8 + length, 9.5, icing, 1.0)

    # contact shadow under the bottom tier
    rounded_rect(bx - 72, tier1_bot - 4, bx + 72, tier1_bot + 3, 4, (0xBF, 0x8F, 0x5F), 0.5)

    # top tier
    tier2_top, tier2_bot = base - 142, base - 70
    rounded_rect(bx - 50, tier2_top, bx + 50, tier2_bot, 8, cream, 1.0)
    for y in range(tier2_top + 36, tier2_bot):
        for x in range(bx - 50, bx + 51):
            _blend(y * W * 3 + x * 3, 0xF3, 0xDF, 0xC4, 0.35)
    rounded_rect(bx - 52, tier2_top - 8, bx + 52, tier2_top + 12, 8, icing, 1.0)
    for dx, length in ((-36, 18), (-9, 24), (16, 20), (38, 14)):
        capsule(bx + dx, tier2_top + 6, bx + dx, tier2_top + 6 + length, 8.5, icing, 1.0)
        disc(bx + dx, tier2_top + 6 + length, 8.5, icing, 1.0)
    rounded_rect(bx - 52, tier2_top + 8, bx + 52, tier2_top + 13, 3, icing_deep, 0.45)

    # sprinkles sitting on the icing
    for i in range(20):
        sx, sy = bx + rrange(-60, 60), tier1_top + rrange(-6, 6)
        disc(sx, sy, rrange(1.6, 2.6), (0xFF, 0xE2, 0x8A) if i % 3 else (0x9A, 0xD8, 0xCE), 0.9)
    for i in range(12):
        sx, sy = bx + rrange(-38, 38), tier2_top + rrange(-6, 4)
        disc(sx, sy, rrange(1.4, 2.2), (0xFF, 0xE2, 0x8A) if i % 2 else (0xF4, 0x8F, 0xB1), 0.85)

    # contact shadow of the top tier
    rounded_rect(bx - 48, tier2_bot - 4, bx + 48, tier2_bot + 3, 4, (0xCB, 0x9A, 0x6C), 0.45)

    # candle
    top = tier2_top - 8
    rounded_rect(bx - 6, top - 44, bx + 6, top + 2, 4, (0xFC, 0xF4, 0xE9), 1.0)
    for i in range(3):
        y = top - 38 + i * 12
        capsule(bx - 5, y, bx + 5, y - 6, 3.0, icing_deep, 0.9)

    # flame
    fx, fy = bx, top - 52
    polyfill([(fx, fy - 28), (fx + 10, fy - 2), (fx + 6, fy + 10), (fx - 6, fy + 10), (fx - 10, fy - 2)],
             (0xFF, 0xB2, 0x46), 1.0)
    disc(fx, fy + 4, 8.0, (0xFF, 0xB2, 0x46), 1.0)
    polyfill([(fx, fy - 12), (fx + 4.5, fy + 1), (fx + 2.5, fy + 8), (fx - 2.5, fy + 8), (fx - 4.5, fy + 1)],
             (0xFF, 0xF6, 0xC2), 1.0)
    glow(fx, fy + 4, 250, (255, 172, 90), 0.26)
    glow(fx, fy + 4, 96, (255, 226, 160), 0.24)



def front_fireflies():
    for x, y, r in ((300, 760, 26), (836, 700, 22), (392, 636, 18)):
        glow(x, y, r + 12, (255, 214, 130), 0.22)
        disc(x, y, 2.2, (255, 248, 200), 0.85)


def confetti():
    cols = [(0xFF, 0xD1, 0x66), (0xF4, 0x8F, 0xB1), (0x8E, 0xD1, 0xC8), (0xA8, 0xB4, 0xF0)]
    bx = SHELL_C[0]
    by = SHELL_C[1] - SHELL_R - 90
    for i in range(44):
        ang = rrange(-math.pi * 0.98, -math.pi * 0.02)
        dist = rrange(60, 200)
        x = bx + math.cos(ang) * dist * 1.45
        y = by + math.sin(ang) * dist * 0.75 + rrange(-30, 60)
        if x < 70 or x > W - 70 or y < 40:
            continue
        size = rrange(5, 9)
        rot = rrange(0, math.pi)
        ca = math.cos(rot) * size
        sa = math.sin(rot) * size * 0.5
        polyfill([(x - ca, y - sa), (x + sa * 0.7, y - ca * 0.7),
                  (x + ca, y + sa), (x - sa * 0.7, y + ca * 0.7)],
                 cols[i % len(cols)], 0.88)



def foreground_grass():
    for _ in range(12):
        blade(rrange(-10, 150), 1030, rrange(120, 250), rrange(-20, 30), rrange(3, 5.5),
              (0x06, 0x12, 0x15), 1.0, 6)
    for _ in range(12):
        blade(rrange(W - 150, W + 10), 1030, rrange(120, 250), rrange(-30, 20), rrange(3, 5.5),
              (0x06, 0x12, 0x15), 1.0, 6)
    for _ in range(9):
        blade(rrange(140, W - 140), 1006, rrange(60, 130), rrange(-16, 16), rrange(2.4, 4.0),
              (0x08, 0x17, 0x1A), 0.95, 6)


def vignette():
    cx, cy = W * 0.5, H * 0.52
    maxd = math.sqrt(cx * cx + cy * cy)
    for y in range(H):
        dy = y + 0.5 - cy
        base = y * W * 3
        for x in range(W):
            dx = x + 0.5 - cx
            d = math.sqrt(dx * dx + dy * dy) / maxd
            if d < 0.58:
                continue
            k = (d - 0.58) / 0.42
            f = 1.0 - 0.40 * k * k
            i = base + x * 3
            buf[i] = int(buf[i] * f)
            buf[i + 1] = int(buf[i + 1] * f)
            buf[i + 2] = int(buf[i + 2] * f)


def png_bytes():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    sky()
    stars()
    hills()
    horizon_haze()
    fireflies(16)
    meadow()
    snail_shadow()
    snail_trail()
    contact_shadow()
    snail_body()
    shell()
    cake()
    front_fireflies()
    confetti()
    foreground_grass()
    vignette()

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes()
    with open(os.path.join(out_dir, "entry.png"), "wb") as fh:
        fh.write(data)
    print("wrote entry.png", len(data), "bytes")


if __name__ == "__main__":
    main()
