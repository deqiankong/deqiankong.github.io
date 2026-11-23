"""Build the site: pages in src/ are written to their URL paths in the repo root.

    python3 build.py

Each page gets the shared masthead and footer, and every
<span class="tex">...</span> is typeset as an inline SVG (no JavaScript needed).
The math is thickened by the same amount as the text font (GAIN in tools/thicken.py).
Needs matplotlib. Preview with:  python3 -m http.server  then open localhost:8000
"""
import base64
import hashlib
import html as htmllib
import io
import pathlib
import re
import sys

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D

root = pathlib.Path(__file__).parent
src = root / "src"
sys.path.insert(0, str(root / "tools"))
from thicken import GAIN, thicken_path  # the stroke weight shared by the text font and the math

# source file -> URL path it is served at
PAGES = {
    "index.html": "/",
    "research.html": "/research/",
    "publications.html": "/publications/",
    "writing.html": "/writing/",
    "post.html": "/writing/planning-follows-a-straight-path/",
}
NAV = [  # label, target, key
    ("Home", "index.html", "home"),
    ("Research", "research.html", "research"),
    ("Publications", "publications.html", "publications"),
    ("Writing", "writing.html", "writing"),
]
TAGLINE = "understanding how networks represent, reason, and learn"
FOOTER = """<footer>
  © 2026 Deqian Kong
  <span class="sep">·</span>deqiankong AT ucla.edu
  <span class="sep">·</span><a href="https://github.com/deqiankong">GitHub</a>
</footer>"""

plt.rcParams.update({"mathtext.fontset": "cm", "svg.fonttype": "path", "svg.hashsalt": "site"})
PT = 10.0  # math is typeset at 10pt, then scaled so that 10pt == 1em
PAD = 1.0
INK = "#161513"  # keep in step with --ink in style.css


def masthead(match: re.Match) -> str:
    current = match.group(1)
    mark = ' aria-current="page"'
    links = "\n".join(
        f'      <a href="{href}"{mark if key == current else ""}>{label}</a>'
        for label, href, key in NAV
    )
    return f"""<header class="masthead">
  <div class="column">
    <a class="name" href="index.html">Deqian Kong</a>
    <p class="tagline">{TAGLINE}</p>
    <nav>
{links}
    </nav>
  </div>
</header>"""


def tex(match: re.Match) -> str:
    source = htmllib.unescape(match.group(1)).strip()
    expr = f"${source}$"
    prop = FontProperties(size=PT, math_fontfamily="cm")
    w, h, depth, *_ = MathTextParser("path").parse(expr, dpi=72, prop=prop)
    edge = GAIN / 2000 * PT  # thickened outlines reach this far past the glyph edges
    W, H = w + 2 * edge, h + 2 * PAD  # pad vertically only, so inline math sits tight against punctuation
    fig = plt.figure(figsize=(W / 72, H / 72))
    if GAIN:
        # Thicken the math exactly as tools/make_font.py thickens the text font: move the
        # outlines themselves. (A stroke drawn around them comes out too heavy on screen.)
        outline = TextPath((0, 0), expr, size=PT, prop=prop)
        k = 1000 / PT  # points to font units
        verts, codes = thicken_path([(x * k, y * k) for x, y in outline.vertices], list(outline.codes), GAIN / 2)
        path = Path([(round(x) / k, round(y) / k) for x, y in verts], codes)  # whole font units, as in the font
        place = Affine2D().translate(edge, depth + PAD).scale(1 / 72) + fig.dpi_scale_trans
        fig.add_artist(PathPatch(path, transform=place, facecolor=INK, edgecolor="none", linewidth=0))
    else:
        fig.text(0, (depth + PAD) / H, expr, fontproperties=prop, color=INK)
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", transparent=True, metadata={"Date": None})
    plt.close(fig)
    uri = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
    style = f"width:{W / PT:.3f}em;vertical-align:{-(depth + PAD) / PT:.3f}em"
    return f'<img class="tex" src="{uri}" style="{style}" alt="{htmllib.escape(source, quote=True)}">'


# The address of the stylesheet changes whenever its content does, so a browser
# never shows a new page with an old, cached stylesheet.
CSS_VERSION = hashlib.sha256((root / "style.css").read_bytes()).hexdigest()[:8]

for name, url in PAGES.items():
    page = (src / name).read_text()
    page = re.sub(r"<!--masthead:(\w+)-->", masthead, page)
    page = page.replace("<!--footer-->", FOOTER)
    page = page.replace('href="style.css"', f'href="/style.css?v={CSS_VERSION}"')
    page = re.sub(r'<span class="tex">(.*?)</span>', tex, page, flags=re.S)
    page = re.sub(r'(src|poster)="(assets/[^"]+)"', r'\1="/\2"', page)
    for s, u in PAGES.items():
        page = page.replace(f'href="{s}"', f'href="{u}"')
    out = root / url.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"{url:45s} {out.stat().st_size / 1024:5.0f} KB")
