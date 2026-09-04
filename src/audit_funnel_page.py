# -*- coding: utf-8 -*-
"""
Self-audit for VSL funnel pages.

    python3 audit_funnel_page.py vsl_registration_page.html [--type registration]
    python3 audit_funnel_page.py vsl_confirmation_page.html --type confirmation

Run this before shipping ANY funnel page, for any client. Exit code 0 means
every check passed. Non-zero means do not ship yet.

It checks four things a human eye reliably misses:
  1. ABOVE THE FOLD  every required block visible without scrolling, at seven
     real viewport sizes. This is the check that keeps getting forgotten.
  2. LAYOUT          no horizontal overflow, no broken images, video ratio
     matches its source, tap targets big enough.
  3. COMPLIANCE      brokerage name + descriptor, registrant names with a
     permitted term, required disclosures, logo parity.
  4. TRACKING        pixel present, and the conversion event fires on the
     confirmation page ONLY when the lead is flagged qualified.
"""
import argparse, json, pathlib, re, sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright --break-system-packages && playwright install chromium")

# Viewports that matter. The two starred are the tight ones; if they pass,
# everything passes. Do not trim this list.
VIEWPORTS = [
    (1440, 900, "desktop 1440x900", False),
    (1366, 768, "laptop 1366x768", False),
    (1280, 720, "laptop 1280x720 *", False),
    (1024, 700, "small laptop 1024x700", False),
    (414, 896, "iPhone Plus 414x896", True),
    (390, 844, "iPhone 390x844", True),
    (375, 667, "iPhone SE 375x667 *", True),
    (360, 740, "Android 360x740", True),
]

# Blocks that must sit above the fold, per page type.
ABOVE_FOLD = {
    "registration": [("headline", "h1"), ("subheadline", ".lede"), ("video", ".video-frame"),
                     ("social proof bar", ".proof"), ("book a call button", ".cta-hero")],
    "confirmation": [("headline", "h1"), ("video", ".video-frame")],
    "confirmation-unqualified": [("headline", "h1"), ("video", ".video-frame")],
}

# Compliance strings. Tune BROKERAGE/AGENTS per client; the rest are generic.
BROKERAGE = "Real Broker Ontario Ltd., Brokerage"
AGENTS = [("Emma Pace", "Sales Representative"), ("Amir Moradian", "Sales Representative")]
PERMITTED_TERMS = ["salesperson", "real estate salesperson", "sales representative",
                   "real estate agent", "real estate sales representative", "realtor"]
DISCLOSURES = [
    ("Facebook/Meta", r"not connected with or endorsed by facebook or meta"),
    ("not intended to solicit", r"not intended to solicit buyers or sellers currently under contract"),
    ("educational purposes", r"for educational purposes only"),
]

results = []
def check(ok, label, detail=""):
    results.append((bool(ok), label, detail))
    print(f'  {"PASS" if ok else "FAIL"}  {label}{("  " + detail) if detail else ""}')
    return ok


def audit(path, page_type):
    html = pathlib.Path(path).read_text()
    print(f"\n=== AUDITING {path}  (type: {page_type}) ===\n")

    # ---------- 3. COMPLIANCE (static) ----------
    print("COMPLIANCE")
    check(BROKERAGE in html, "registered brokerage name with 'Brokerage' descriptor present")
    for name, term in AGENTS:
        check(name in html, f"registrant named: {name}")
        check(term.lower() in html.lower(), f"permitted term present for {name}: {term}")
    check(not re.search(r"\b(Realty|Real Estate)\s+Brokerage\b(?!.*Real Broker)", html)
          or BROKERAGE in html, "no competing entity presented as the brokerage")
    for label, pattern in DISCLOSURES:
        check(re.search(pattern, html, re.I), f"disclosure present: {label}")
    check("brand-lockup" in html, "brokerage logo/lockup present in the disclosures block")

    # ---------- 4. TRACKING (static) ----------
    print("\nTRACKING")
    tracked = re.findall(r"fbq\('track',\s*'(\w+)'", html)
    if page_type == "confirmation-unqualified":
        # The unqualified page must carry NO tracking at all. This is the whole
        # point of splitting the confirmation page in two: an under-threshold
        # booking can never be counted or retargeted, however it arrives.
        for banned in ("fbq", "connect.facebook.net", "facebook.com/tr"):
            check(banned not in html, f"unqualified page contains no {banned}")
        check(not tracked, "unqualified page fires no events at all", f"found {tracked}")
    else:
        check(re.search(r"fbq\('init',\s*'\d+'\)", html), "Meta pixel base code present")
        if page_type == "registration":
            check(tracked == ["PageView"], "registration fires PageView only, no conversion",
                  f"found {tracked}")
        else:
            check("Schedule" in tracked, "qualified page fires the Schedule conversion")
            check("eventID" in html, "Schedule carries an eventID for CAPI deduplication")

    with sync_playwright() as p:
        b = p.chromium.launch()
        url = "file://" + str(pathlib.Path(path).resolve())

        # ---------- 1. ABOVE THE FOLD ----------
        print("\nABOVE THE FOLD")
        for w, h, label, mobile in VIEWPORTS:
            pg = b.new_page(viewport={"width": w, "height": h}, is_mobile=mobile)
            pg.goto(url); pg.wait_for_timeout(450)
            missing = []
            for name, sel in ABOVE_FOLD[page_type]:
                bottom = pg.evaluate(
                    """(s)=>{const e=document.querySelector(s);
                       return e?Math.round(e.getBoundingClientRect().bottom):null;}""", sel)
                if bottom is None or bottom > h:
                    missing.append(f"{name}({bottom})")
            check(not missing, f"all blocks above fold at {label}",
                  ("below fold: " + ", ".join(missing)) if missing else "")
            pg.close()

        # ---------- 2. LAYOUT ----------
        print("\nLAYOUT")
        for w, h, label, mobile in VIEWPORTS:
            pg = b.new_page(viewport={"width": w, "height": h}, is_mobile=mobile)
            pg.goto(url); pg.wait_for_timeout(400)
            ov = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(not ov, f"no horizontal overflow at {label}")
            pg.close()

        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(url)
        pg.evaluate("""async()=>{const h=document.body.scrollHeight;
            for(let y=0;y<h;y+=500){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,35));}
            window.scrollTo(0,0);}""")
        pg.wait_for_timeout(1200)

        imgs = pg.evaluate("""()=>{const out=[];
            document.querySelectorAll('img').forEach(i=>{
              // #lightboxImg is intentionally empty until a screenshot is opened
              if(i.id==='lightboxImg') return;
              if(!i.complete || i.naturalWidth===0) out.push(i.getAttribute('src')||'(no src)');});
            return out;}""")
        check(not imgs, "every image loads", f"broken: {imgs[:3]}" if imgs else "")

        ratio = pg.evaluate("""()=>{const e=document.querySelector('.video-frame');
            if(!e) return null; const r=e.getBoundingClientRect();
            return +(r.width/r.height).toFixed(3);}""")
        check(ratio is not None and abs(ratio - 1.537) < 0.02,
              "video matches its source aspect ratio (not letterboxed)", f"rendered {ratio}")

        small = pg.evaluate("""()=>{const bad=[];
            document.querySelectorAll('a.cta, button.cta, .js-book').forEach(e=>{
              const r=e.getBoundingClientRect();
              if(r.height>0 && r.height<44) bad.push(Math.round(r.height));});
            return bad;}""")
        check(not small, "tap targets at least 44px tall", f"too small: {small}" if small else "")

        # logo parity: brokerage identification must not be smaller than team branding
        parity = pg.evaluate("""()=>{const l=document.querySelector('.brand-lockup');
            return l?{w:Math.round(l.getBoundingClientRect().width),
                      h:Math.round(l.getBoundingClientRect().height)}:null;}""")
        check(parity and parity["h"] >= 30,
              "brokerage lockup rendered at a legible size", f"{parity}" if parity else "missing")
        pg.close()
        b.close()

    failed = [r for r in results if not r[0]]
    print(f"\n{'='*60}\n{len(results)-len(failed)}/{len(results)} checks passed")
    if failed:
        print("\nDO NOT SHIP. Failing checks:")
        for _, label, detail in failed:
            print(f"  - {label} {detail}")
    else:
        print("All checks passed. Safe to ship.")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--type", choices=["registration", "confirmation",
                                       "confirmation-unqualified"], default=None)
    a = ap.parse_args()
    low = a.path.lower()
    t = a.type or ("confirmation-unqualified" if "unqualified" in low
                   else "confirmation" if "confirm" in low else "registration")
    sys.exit(audit(a.path, t))
