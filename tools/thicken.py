"""Thicken outlines: every stroke gains the same amount of weight.

This is the geometry behind the site's text font and its equations. An outline
is moved outward by a fixed distance on the ink's side, so a stroke becomes
thicker by twice that distance while its skeleton stays where it was.

    GAIN            the one dial, in font units (thousandths of an em)
    thicken_glyph   for a font glyph (used by make_font.py)
    thicken_path    for a drawing in matplotlib's path form (used by build.py)

Plain Python, no dependencies.
"""
import math

GAIN = 11   # stems of Latin Modern go from 69 to 80, hairlines from 31 to 42; 0 gives Latin Modern back

EPS = 1e-9
MITER_REACH = 2.0     # a corner's tip may move at most this many offsets away; sharper tips are cut flat
SPLIT_ANGLE = math.radians(50)   # curves that turn more than this are split before being moved


# ---------- small vector helpers ----------
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, s): return (a[0] * s, a[1] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def norm(a): return math.hypot(a[0], a[1])
def unit(a):
    n = norm(a)
    return (a[0] / n, a[1] / n) if n > EPS else None
def right(t): return (t[1], -t[0])      # normal to the right of the direction of travel



def tangents(seg):
    """Unit direction leaving the start and arriving at the end of a segment."""
    pts = seg[1:]
    t0 = t1 = None
    for q in pts[1:]:
        t0 = unit(sub(q, pts[0]))
        if t0: break
    for q in reversed(pts[:-1]):
        t1 = unit(sub(pts[-1], q))
        if t1: break
    return t0, t1


def split(seg):
    _, p0, p1, p2, p3 = seg
    m = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    a, b, c = m(p0, p1), m(p1, p2), m(p2, p3)
    d, e = m(a, b), m(b, c)
    f = m(d, e)
    return ("C", p0, a, d, f), ("C", f, e, c, p3)


def flat_enough(seg, depth):
    """A curve is offset well when it turns only a little."""
    if depth >= 5:
        return True
    _, p0, p1, p2, p3 = seg
    legs = [unit(sub(b, a)) for a, b in ((p0, p1), (p1, p2), (p2, p3))]
    legs = [l for l in legs if l]
    turn = 0.0
    for a, b in zip(legs, legs[1:]):
        turn += abs(math.atan2(cross(a, b), dot(a, b)))
    return turn <= SPLIT_ANGLE


def prepared(contour):
    out = []
    def push(seg, depth=0):
        if seg[0] == "L" or flat_enough(seg, depth):
            out.append(seg)
        else:
            a, b = split(seg)
            push(a, depth + 1); push(b, depth + 1)
    for seg in contour:
        if tangents(seg)[0] is None:     # a segment with no extent
            continue
        push(seg)
    return out


def offset_segment(seg, d):
    t0, t1 = tangents(seg)
    n0, n1 = right(t0), right(t1)
    if seg[0] == "L":
        return ("L", add(seg[1], mul(n0, d)), add(seg[2], mul(n0, d)))
    _, p0, p1, p2, p3 = seg
    q0, q3 = add(p0, mul(n0, d)), add(p3, mul(n1, d))
    # A curve moved outward by d has handles scaled by (1 + d * curvature), with
    # curvature positive where the path turns left (away from the offset side).
    def scale(handle, k_num):
        h = norm(handle)
        if h < EPS:
            return 1.0
        k = (2.0 / 3.0) * k_num / h ** 3
        return min(max(1.0 + d * k, 0.05), 3.0)
    bend = lambda a, b, c: cross(sub(b, a), sub(c, b))
    s0 = scale(sub(p1, p0), bend(p0, p1, p2))
    s1 = scale(sub(p3, p2), bend(p1, p2, p3))
    q1 = add(q0, mul(sub(p1, p0), s0))
    q2 = add(q3, mul(sub(p2, p3), s1))
    return ("C", q0, q1, q2, q3)


def line_hit(p, t, q, u):
    """Where the line through p along t meets the line through q along u."""
    den = cross(t, u)
    if abs(den) < 1e-7:
        return None
    s = cross(sub(q, p), u) / den
    return add(p, mul(t, s))


def offset_contour(contour, d):
    if d == 0:
        return contour                                # nothing to do
    segs = prepared(contour)
    if not segs:
        return segs
    n = len(segs)
    offs = [offset_segment(s, d) for s in segs]
    tans = [tangents(s) for s in segs]
    out = []
    for i in range(n):
        j = (i + 1) % n
        out.append(offs[i])
        end, start = offs[i][-1], offs[j][1]
        if norm(sub(end, start)) < 1e-6:
            continue                                  # smooth join
        corner = segs[i][-1]
        t_out, t_in = tans[i][1], tans[j][0]
        turn = cross(t_out, t_in)
        if turn * d > 1e-7:                           # outward corner: there is a gap to fill
            tip = line_hit(end, t_out, start, t_in)
            reach = MITER_REACH * abs(d)
            if tip is not None and norm(sub(tip, corner)) <= reach:
                out.append(("L", end, tip)); out.append(("L", tip, start))
            elif tip is not None:
                b = unit(sub(tip, corner))            # cut the tip flat, square to the corner's axis
                a1 = add(end, mul(t_out, (reach - dot(sub(end, corner), b)) / dot(t_out, b)))
                a2 = add(start, mul(t_in, (reach - dot(sub(start, corner), b)) / dot(t_in, b)))
                out.append(("L", end, a1)); out.append(("L", a1, a2)); out.append(("L", a2, start))
            else:
                out.append(("L", end, start))
        else:                                         # inward corner: the two pieces cross
            out.append(("L", end, start))             # the small overlap is filled anyway
    # tidy: drop empty lines, merge lines that continue in the same direction
    tidy = []
    for s in out:
        if s[0] == "L":
            if norm(sub(s[2], s[1])) < 1e-6:
                continue
            if tidy and tidy[-1][0] == "L":
                a = unit(sub(tidy[-1][2], tidy[-1][1])); b = unit(sub(s[2], s[1]))
                if a and b and abs(cross(a, b)) < 1e-6 and dot(a, b) > 0:
                    tidy[-1] = ("L", tidy[-1][1], s[2])
                    continue
        tidy.append(s)
    return tidy


def flatten(contour, steps=8):
    pts = []
    for s in contour:
        if s[0] == "L":
            pts.append(s[1])
        else:
            _, p0, p1, p2, p3 = s
            for k in range(steps):
                t = k / steps; u = 1 - t
                pts.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                            u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return pts


def winding(point, polygons):
    x, y = point
    w = 0
    for poly in polygons:
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            if y0 <= y < y1 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                w += 1
            elif y1 <= y < y0 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
                w -= 1
    return w


def ink_side(contour, polygons):
    """+1 if the ink lies to the left of this contour, -1 if to the right, 0 if on both sides."""
    votes = 0
    longest = sorted(contour, key=lambda s: -norm(sub(s[-1], s[1])))[:3]
    for s in longest:
        if s[0] == "L":
            mid = mul(add(s[1], s[2]), 0.5); t = unit(sub(s[2], s[1]))
        else:
            _, p0, p1, p2, p3 = s
            mid = ((p0[0] + 3*p1[0] + 3*p2[0] + p3[0]) / 8, (p0[1] + 3*p1[1] + 3*p2[1] + p3[1]) / 8)
            t = unit(sub(add(p2, p3), add(p0, p1)))
        if t is None:
            continue
        n = right(t)
        left = winding(sub(mid, mul(n, 0.37)), polygons) != 0
        rgt = winding(add(mid, mul(n, 0.37)), polygons) != 0
        votes += (1 if left and not rgt else -1 if rgt and not left else 0)
    return (votes > 0) - (votes < 0)


def thicken_glyph(contours, d):
    if d == 0:
        return contours
    polygons = [flatten(c) for c in contours]
    out = []
    for c in contours:
        side = ink_side(c, polygons)
        out.append(offset_contour(c, d * side) if side else c)
    return out


def thicken_path(vertices, codes, d):
    """The same thickening for a drawing given as points and matplotlib path codes
    (1 move, 2 line, 3 quadratic, 4 cubic, 79 close). Units are font units.
    Used for equations, so that math and text gain exactly the same weight."""
    contours, cur, start, pt, i = [], None, None, None, 0
    def close():
        nonlocal cur
        if cur is not None:
            if norm(sub(start, pt)) > EPS:
                cur.append(("L", pt, start))
            if cur:
                contours.append(cur)
        cur = None
    while i < len(codes):
        c, v = codes[i], tuple(vertices[i])
        if c == 1:
            close(); cur, start, pt = [], v, v; i += 1
        elif c == 2:
            if norm(sub(v, pt)) > EPS:
                cur.append(("L", pt, v))
            pt = v; i += 1
        elif c == 3:                                   # a quadratic curve, written as a cubic
            q, e = v, tuple(vertices[i + 1])
            c1 = (pt[0] + 2 / 3 * (q[0] - pt[0]), pt[1] + 2 / 3 * (q[1] - pt[1]))
            c2 = (e[0] + 2 / 3 * (q[0] - e[0]), e[1] + 2 / 3 * (q[1] - e[1]))
            cur.append(("C", pt, c1, c2, e)); pt = e; i += 2
        elif c == 4:
            cur.append(("C", pt, v, tuple(vertices[i + 1]), tuple(vertices[i + 2])))
            pt = tuple(vertices[i + 2]); i += 3
        elif c == 79:
            close(); i += 1
        else:
            raise ValueError("path code %r" % c)
    close()
    verts, out = [], []
    for c in thicken_glyph(contours, d):
        if not c:
            continue
        verts.append(c[0][1]); out.append(1)
        for seg in c:
            if seg[0] == "L":
                verts.append(seg[2]); out.append(2)
            else:
                verts.extend(seg[2:]); out.extend([4, 4, 4])
        verts.append(c[0][1]); out.append(79)
    return verts, out
