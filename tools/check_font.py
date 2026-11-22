#!/usr/bin/env python3
"""Check a thickened font against its source, glyph by glyph.

    python3 tools/make_font.py --src DIR --full /tmp/full
    python3 tools/check_font.py DIR/lmroman10-regular.otf /tmp/full/KongModern-regular.otf 11

Each glyph is drawn at one pixel per font unit, before and after. The new
shape must contain everything within gain/2 of the old one, and must not
reach further than a mitred corner can. Prints the glyphs that fail.
Needs fontTools, numpy, scipy and matplotlib.
"""
import sys
import numpy as np
from scipy import ndimage
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen

TOL = 1.0   # pixels = font units


def mpl_path(glyph):
    rec = RecordingPen(); glyph.draw(rec)
    verts, codes = [], []
    for op, a in rec.value:
        if op == "moveTo": verts.append(a[0]); codes.append(Path.MOVETO)
        elif op == "lineTo": verts.append(a[0]); codes.append(Path.LINETO)
        elif op == "curveTo": verts.extend(a); codes.extend([Path.CURVE4] * 3)
        elif op in ("closePath", "endPath"): verts.append((0, 0)); codes.append(Path.CLOSEPOLY)
    return Path(verts, codes) if verts else None


def raster(path, box):
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    r = RendererAgg(w, h, 72)
    gc = r.new_gc(); gc.set_antialiased(False); gc.set_linewidth(0)
    r.draw_path(gc, path, Affine2D().translate(-x0, -y0), (0, 0, 0, 1))
    return np.asarray(r.buffer_rgba())[:, :, 3] > 127


def main():
    src, new, gain = TTFont(sys.argv[1]), TTFont(sys.argv[2]), float(sys.argv[3])
    d = gain / 2
    gs, gn = src.getGlyphSet(), new.getGlyphSet()
    bad, worst_miss, worst_reach, n, widths = [], 0, 0.0, 0, 0
    for name in src.getGlyphOrder():
        if gs[name].width != gn[name].width:
            widths += 1
        pa, pb = mpl_path(gs[name]), mpl_path(gn[name])
        if pa is None:
            if pb is not None: bad.append((name, "new outline where there was none"))
            continue
        if pb is None:
            bad.append((name, "outline lost")); continue
        bp = BoundsPen(gs); gs[name].draw(bp)
        x0, y0, x1, y1 = bp.bounds
        m = int(4 * d + 12)
        box = (int(x0) - m, int(y0) - m, int(x1) + m, int(y1) + m)
        a, b = raster(pa, box), raster(pb, box)
        dist = ndimage.distance_transform_edt(~a)        # distance of every pixel from the old ink
        missing = int(np.count_nonzero((dist <= d - TOL) & ~b))
        reach = float(dist[b].max()) if b.any() else 0.0
        beyond = int(np.count_nonzero(b & (dist > d + TOL)))
        ink = int(np.count_nonzero(a))
        n += 1
        worst_miss = max(worst_miss, missing); worst_reach = max(worst_reach, reach)
        why = []
        if missing > 3: why.append("%d px not thickened" % missing)
        limit = 5 ** 0.5 * d      # the far corner of a tip cut flat at twice the offset
        if reach > limit + TOL: why.append("reaches %.1f (limit %.1f)" % (reach, limit))
        if beyond > 0.02 * ink + 40: why.append("%d px beyond the offset (ink %d)" % (beyond, ink))
        if why: bad.append((name, "; ".join(why)))
    print("%s: %d glyphs checked, %d flagged, %d width changes, worst missing %d px, furthest reach %.1f units"
          % (sys.argv[2].split("/")[-1], n, len(bad), widths, worst_miss, worst_reach))
    for name, why in bad[:40]:
        print("   ", name, "—", why)
    return len(bad)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
