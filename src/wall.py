# -*- coding: utf-8 -*-
"""Generate the screenshot review wall markup from the processed images."""
import html
import reviews as R

# slug, reviewer-name-in-reviews.py, width, height  (strongest first)
SHOTS = [
    ("madeline-walden",      "Madeline Walden (Maddy &amp; Derek)", 620, 700),
    ("winnie",               "Winnie",                              620, 455),
    ("natasja",              "Natasja",                             620, 577),
    ("greg-bellec",          "Greg Bellec",                         620, 548),
    ("jose-antonio-sanchez", "Jose Antonio Sanchez",                620, 537),
    ("samten-dolker",        "Samten Dolker",                       620, 715),
    ("karen-alvarenga",      "Karen Alvarenga",                     620, 425),
    ("osasuyi-ojomo",        "Osasuyi Ojomo",                       620, 668),
    ("christopher-smith",    "Christopher Smith (Ali &amp; Chris)", 620, 419),
    ("mona-nasr",            "Mona Nasr",                           620, 891),
    ("md-te-meron",          "MD Te (Meron)",                       620, 855),
    ("prasanth-pahi",        "Prasanth Pahi",                       620, 612),
    ("fw-kong",              "FW Kong",                             620, 469),
    ("lukas-grey",           "Lukas Grey",                          620, 386),
    ("aidan-shankman",       "Aidan Shankman",                      620, 369),
    ("aashti-vijh",          "Aashti Vijh",                         620, 346),
    ("js",                   "JS",                                  620, 221),
]

BY_NAME = {w: t for (w, m, t) in R.REVIEWS}


def _alt(who, text):
    """Plain-text alt: the reviewer and their words, so the wall is
    readable to screen readers and search engines even though the
    review itself is an image."""
    plain = html.unescape(who) + ' — 5 stars. "' + html.unescape(text) + '"'
    return html.escape(plain, quote=True)


def render(limit=None):
    rows = SHOTS if limit is None else SHOTS[:limit]
    out = []
    for slug, who, w, h in rows:
        out.append(
f'''      <button class="shot" type="button" data-src="review-images/{slug}.webp">
        <img src="review-images/{slug}.webp" width="{w}" height="{h}" loading="lazy" decoding="async"
             alt="{_alt(who, BY_NAME[who])}">
      </button>''')
    return "\n\n".join(out)


COUNT = len(SHOTS)
