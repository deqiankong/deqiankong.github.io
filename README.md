# deqiankong.github.io

Personal site of Deqian Kong. Plain static HTML, one stylesheet, no JavaScript.

## Layout

- `src/` — page sources (`index`, `research`, `publications`, one sample post)
- `style.css`, `assets/` — stylesheet, fonts, figures, video
- `build.py` — writes each page to its URL path (`index.html`, `research/index.html`, …)
- the built pages are committed, so GitHub Pages serves them with no build step

## Edit and rebuild

    python3 build.py              # needs matplotlib, for the math
    python3 -m http.server        # then open http://localhost:8000

Write math as `<span class="tex">x^2</span>`; the build typesets it as an inline SVG.

## Status

Still a draft. Every page carries a "mockup" banner because the copy, the news list
and the sample post are placeholders. Remove the banners once the text is final.
