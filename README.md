# deqiankong.github.io

Personal site of Deqian Kong. Plain static HTML, one stylesheet, no JavaScript.

## Layout

- `src/` — page sources (`index`, `research`, `publications`, `writing`, and one sample post)
- `style.css`, `assets/` — stylesheet, fonts, figures, video
- `build.py` — writes each page to its URL path (`index.html`, `research/index.html`, …)
- `tools/` — the text font: `thicken.py` (the geometry and the one dial, `GAIN`),
  `make_font.py` (builds the font), `check_font.py` (checks it glyph by glyph)
- the built pages are committed, so GitHub Pages serves them with no build step

## Edit and rebuild

    python3 build.py              # needs matplotlib, for the math
    python3 -m http.server        # then open http://localhost:8000

Write math as `<span class="tex">x^2</span>`; the build typesets it as an inline SVG.

## The font

The text is set in Kong Modern: Latin Modern Roman 10 with every stroke made thicker
by the same amount, `GAIN` thousandths of an em (now 11). Widths and kerning are
Latin Modern's, so nothing reflows. The equations are thickened by the same amount.
To change the weight, edit `GAIN` in `tools/thicken.py`, then:

    python3 tools/make_font.py --src DIR    # DIR: the Latin Modern .otf files; needs fontTools, brotli
    python3 build.py

`GAIN = 0` gives plain Latin Modern. Licences and the list of changes are in
`assets/fonts/NOTICE.txt`.

## Status

Not yet on the site: a CV link and a Scholar link. The one post under Writing is a
layout sample (math, figure, video, code, margin notes), not finished writing.
To add a post, copy `src/post.html`, add it to `PAGES` in `build.py` and to the list
in `src/writing.html`, and rebuild.
