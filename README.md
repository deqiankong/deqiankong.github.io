# deqiankong.github.io

Personal site of Deqian Kong. Plain static HTML, one stylesheet, no JavaScript.

## Layout

- `src/` — page sources (`index`, `research`, `publications`); `src/drafts/` is not built or published
- `style.css`, `assets/` — stylesheet, fonts, figures, video
- `build.py` — writes each page to its URL path (`index.html`, `research/index.html`, …)
- the built pages are committed, so GitHub Pages serves them with no build step

## Edit and rebuild

    python3 build.py              # needs matplotlib, for the math
    python3 -m http.server        # then open http://localhost:8000

Write math as `<span class="tex">x^2</span>`; the build typesets it as an inline SVG.

## Status

Still a draft: each page carries a one-line "draft" note until the text is final.
Not yet on the site: a CV link, a Scholar link, and a Writing section. A sample
post layout (math, figure, video, code, margin notes) is kept in `src/drafts/post.html`;
to publish a post, move it into `src/`, add it to `PAGES` and `NAV` in `build.py`, and rebuild.
