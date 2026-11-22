#!/usr/bin/env python3
"""Build the site's text font: Latin Modern Roman 10 with every stroke thickened.

    python3 tools/make_font.py --src DIR

DIR holds the Latin Modern 2.004 OpenType files (lmroman10-regular.otf,
lmroman10-italic.otf, lmroman10-bold.otf), from
https://www.gust.org.pl/projects/e-foundry/latin-modern or any TeX distribution.

The amount is GAIN in thicken.py, in thousandths of an em. Each outline moves
outward by GAIN/2, so stems go from 69 to 69+GAIN and hairlines from 31 to
31+GAIN. Letter widths, spacing and kerning stay exactly as in Latin Modern,
so line breaks do not change. A gain of 0 gives Latin Modern back.

Writes assets/fonts/<Family>-<style>.woff2, cut down to the site's character
set. With --full DIR it also writes complete .otf files, for check_font.py.

The result carries its own family name and says in its name records that it is
a modified version. After changing GAIN, run this and then build.py.
Needs fontTools and brotli.
"""
import argparse, math, pathlib, sys

from fontTools import subset
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from thicken import EPS, GAIN, norm, sub, thicken_glyph

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAMILY = "Kong Modern"
STYLES = {"regular": ("lmroman10-regular.otf", "Regular"),
          "italic": ("lmroman10-italic.otf", "Italic"),
          "bold": ("lmroman10-bold.otf", "Bold")}

# The characters the site's fonts carry: Latin with accents, common punctuation.
CHARSET = ("0020-007E 00A0-0137 0139-0148 014A-0165 0168-017F 018E 0192 01A0-01A1 01AF-01B0 "
           "01CD-01D4 01D7-01DD 01E6-01E7 01EA-01EB 01F0 01F4-01F5 01FA-0201 0204-0205 0208-0209 "
           "020C-020D 0210-0211 0214-0215 0218-021B 0237 2010-2011 2013-2014 2016 2018-201A "
           "201C-201E 2020-2022 2026 2030-2031 2039-203B 203D 203F 2190 2192 2212")


def charset():
    out = []
    for part in CHARSET.split():
        lo, _, hi = part.partition("-")
        out.extend(range(int(lo, 16), int(hi or lo, 16) + 1))
    return out


def contours_of(glyph):
    """Closed contours as lists of segments: ('L', p0, p1) or ('C', p0, p1, p2, p3)."""
    rec = RecordingPen()
    glyph.draw(rec)
    out, cur, start, pt = [], None, None, None
    for op, args in rec.value:
        if op == "moveTo":
            cur, start, pt = [], args[0], args[0]
        elif op == "lineTo":
            if norm(sub(args[0], pt)) > EPS:
                cur.append(("L", pt, args[0]))
            pt = args[0]
        elif op == "curveTo":
            if len(args) != 3:
                raise ValueError("unexpected curve with %d points" % len(args))
            cur.append(("C", pt, args[0], args[1], args[2]))
            pt = args[2]
        elif op in ("closePath", "endPath"):
            if norm(sub(start, pt)) > EPS:
                cur.append(("L", pt, start))
            if cur:
                out.append(cur)
            cur = None
        else:
            raise ValueError(op)
    return out


def draw(contours, pen):
    for c in contours:
        if not c:
            continue
        pen.moveTo(c[0][1])
        for s in c:
            if s[0] == "L":
                pen.lineTo(s[2])
            else:
                pen.curveTo(s[2], s[3], s[4])
        pen.closePath()


def thicken(font, gain):
    d = gain / 2.0
    glyphs = font.getGlyphSet()
    cff = font["CFF "].cff
    top = cff[cff.fontNames[0]]
    private, gsubrs = top.Private, cff.GlobalSubrs
    new = {}
    for name in font.getGlyphOrder():
        g = glyphs[name]
        pen = T2CharStringPen(g.width, glyphs)
        draw(thicken_glyph(contours_of(g), d), pen)
        new[name] = pen.getCharString(private=private, globalSubrs=gsubrs)
    for name, cs in new.items():
        top.CharStrings[name] = cs
    # the stem hints describe the old outlines; widen what they record
    g = int(round(gain))
    up = math.ceil(d)
    for key in ("StdHW", "StdVW"):
        if getattr(private, key, None) is not None:
            setattr(private, key, getattr(private, key) + g)
    for key in ("StemSnapH", "StemSnapV"):
        if getattr(private, key, None):
            setattr(private, key, [v + g for v in getattr(private, key)])
    blues = getattr(private, "BlueValues", None)
    if blues:   # first pair is the baseline zone (moves down), the rest are tops (move up)
        private.BlueValues = [v - up if i < 2 else v + up for i, v in enumerate(blues)]
    if getattr(private, "OtherBlues", None):
        private.OtherBlues = [v - up for v in private.OtherBlues]


def rename(font, family, style, gain):
    ps = family.replace(" ", "") + "-" + style
    full = family if style == "Regular" else family + " " + style
    note = ("%s is a modified version of Latin Modern Roman 10 (GUST e-foundry, v2.004): "
            "every stroke thickened by %g/1000 em. It is not Latin Modern and is not "
            "supported by its authors." % (family, gain))
    name = font["name"]
    for rec in list(name.names):
        if rec.nameID in (1, 16): rec.string = family
        elif rec.nameID in (2, 17): rec.string = style
        elif rec.nameID == 3: rec.string = "%s;gain%g" % (ps, gain)
        elif rec.nameID == 4: rec.string = full
        elif rec.nameID == 6: rec.string = ps
        elif rec.nameID == 10: rec.string = note
        elif rec.nameID in (18, 21, 22):
            name.names.remove(rec)
    if not any(r.nameID == 10 for r in name.names):
        name.setName(note, 10, 3, 1, 0x409)
    cff = font["CFF "].cff
    top = cff[cff.fontNames[0]]
    cff.fontNames[0] = ps
    top.FullName = full
    top.FamilyName = family


def web_subset(font):
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.hinting = True
    opts.desubroutinize = True
    opts.flavor = "woff2"
    s = subset.Subsetter(opts)
    s.populate(unicodes=charset())
    s.subset(font)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True, help="folder with the Latin Modern .otf files")
    ap.add_argument("--gain", type=float, default=GAIN, help="default: GAIN in thicken.py (%g)" % GAIN)
    ap.add_argument("--family", default=FAMILY)
    ap.add_argument("--out", default=str(ROOT / "assets" / "fonts"))
    ap.add_argument("--full", help="also write complete .otf files here, for check_font.py")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    stem = a.family.replace(" ", "")
    for style, (source, style_name) in STYLES.items():
        font = TTFont(pathlib.Path(a.src) / source, recalcTimestamp=False)   # same input, same bytes out
        thicken(font, a.gain)
        rename(font, a.family, style_name, a.gain)
        if a.full:
            pathlib.Path(a.full).mkdir(parents=True, exist_ok=True)
            font.save(pathlib.Path(a.full) / ("%s-%s.otf" % (stem, style)))
        web_subset(font)
        font.flavor = "woff2"
        web = out / ("%s-%s.woff2" % (stem, style))
        font.save(web)
        print("%-8s gain %-4g %d glyphs  %5.1f kB  %s" % (
            style, a.gain, len(TTFont(web).getGlyphOrder()), web.stat().st_size / 1000, web.name))


if __name__ == "__main__":
    main()
