"""Build the site: pages in src/ are written to their URL paths in the repo root.

    python3 build.py

Each page gets the shared masthead and footer, and every
<span class="tex">...</span> is typeset as an inline SVG (no JavaScript needed).
Needs matplotlib. Preview with:  python3 -m http.server  then open localhost:8000
"""
import base64
import html as htmllib
import io
import pathlib
import re

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser

root = pathlib.Path(__file__).parent
src = root / "src"  # src/drafts/ is not built

# source file -> URL path it is served at
PAGES = {
    "index.html": "/",
    "research.html": "/research/",
    "publications.html": "/publications/",
}
NAV = [  # label, target, key
    ("Home", "index.html", "home"),
    ("Research", "research.html", "research"),
    ("Publications", "publications.html", "publications"),
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
    W, H = w, h + 2 * PAD  # pad vertically only, so inline math sits tight against punctuation
    fig = plt.figure(figsize=(W / 72, H / 72))
    fig.text(0, (depth + PAD) / H, expr, fontproperties=prop, color=INK)
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", transparent=True, metadata={"Date": None})
    plt.close(fig)
    uri = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
    style = f"width:{W / PT:.3f}em;vertical-align:{-(depth + PAD) / PT:.3f}em"
    return f'<img class="tex" src="{uri}" style="{style}" alt="{htmllib.escape(source, quote=True)}">'


for name, url in PAGES.items():
    page = (src / name).read_text()
    page = re.sub(r"<!--masthead:(\w+)-->", masthead, page)
    page = page.replace("<!--footer-->", FOOTER)
    page = page.replace('href="style.css"', 'href="/style.css"')
    page = re.sub(r'<span class="tex">(.*?)</span>', tex, page, flags=re.S)
    page = re.sub(r'(src|poster)="(assets/[^"]+)"', r'\1="/\2"', page)
    for s, u in PAGES.items():
        page = page.replace(f'href="{s}"', f'href="{u}"')
    out = root / url.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"{url:45s} {out.stat().st_size / 1024:5.0f} KB")
