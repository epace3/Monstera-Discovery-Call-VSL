# Monstera / North Group — Discovery Call VSL Funnel

Live at **discoverycall.monstera.ca** (Netlify).

## Routes and tracking

| Route | Page | Meta Pixel `1828499953929219` |
|---|---|---|
| `/` | Registration / VSL | base code + `PageView` only |
| `/booked` | Confirmation — **qualified** | base code + `Schedule` (with `eventID` for CAPI dedupe) |
| `/confirmed` | Confirmation — **unqualified** | **nothing — not one byte** |

The qualified/unqualified split *is* the tracking gate. `/confirmed` contains no
pixel code at all, so an under-threshold booking can never fire a conversion or
land in a retargeting audience, however the visitor arrives. That is stronger
than gating on a URL parameter, and it is enforced by an assertion in the build.

Both confirmation URLs are deliberately neutral. A lead routed to `/confirmed`
should have no idea they were segmented — which is why it is not called
something like `/not-a-fit`.

Calendly routing (this is the part that must be right before spend):

- Emma's 15-minute event → redirect to `https://discoverycall.monstera.ca/booked`
- The newer agent's event → redirect to `https://discoverycall.monstera.ca/confirmed`

In both Calendly events turn ON **"Pass event details to your redirect page"**.
That passes `invitee_uuid`, which `/booked` uses as the Meta `eventID` so the
browser `Schedule` deduplicates against the one GHL sends via the Conversions API.

## Layout of this repo

```
site/    what Netlify publishes (netlify.toml sets publish = "site")
src/     the sources everything is generated from — edit these, never site/
```

`site/` is build output. Editing it directly gets your change overwritten on the
next build.

## Making a change

```bash
cd src
python3 build.py                                     # regenerates all three pages
python3 audit_funnel_page.py vsl_registration_page.html
python3 audit_funnel_page.py vsl_confirmation_qualified.html
python3 audit_funnel_page.py vsl_confirmation_unqualified.html
```

`audit_funnel_page.py` is the self-review step. It runs 32–34 checks in four
groups across eight real viewport sizes and **exit code 0 means ship**:

1. **Above the fold** — every required block visible without scrolling, at all
   eight viewports. On the registration page that is headline, subheadline,
   video, social-proof bar *and* the book-a-call button. This is the check that
   keeps getting forgotten, so it is the first one that runs.
2. **Layout** — no horizontal overflow, no broken images, video matches its true
   source ratio (1.537:1, not 16:9), tap targets ≥ 44px.
3. **Compliance** — registered brokerage name with the "Brokerage" descriptor,
   each registrant named with a permitted term, required disclosures present,
   brokerage lockup at a legible size.
4. **Tracking** — pixel present where it belongs and, critically, *absent* where
   it does not.

Then copy the three outputs into `site/` (`index.html`, `booked/index.html`,
`confirmed/index.html`) and push. Netlify builds on push.

## Standards these pages are built to

**Above the fold is not negotiable.** Headline, subheadline, video, proof and the
booking CTA all land above the fold on a 375×667 phone and a 1280×720 laptop. The
video is sized by constraining its *width* from viewport height
(`width: min(880px, 100%, calc(48vh * 1.537))`) — never by capping its height,
which fights `aspect-ratio` and squashes the player.

**Stacked, never side-by-side.** Headline, then subheadline, then video, then
proof. One column at every width.

**Section order is fixed** for both page types and lives in the `.src.html`
files as commented section markers.

## RECO / TRESA compliance

Advertising here follows RECO Bulletins 5.1–5.4:

- The registered brokerage — **Real Broker Ontario Ltd., Brokerage** — is named
  with its legal descriptor on every page.
- Monstera Real Estate and North Group Real Estate are **team names**. They are
  not registered brokerages and are not registered to trade in real estate.
  Monstera Real Estate has officially merged with North Group Real Estate.
- Registrants are named with a permitted term: Emma Pace, Sales Representative;
  Amir Moradian, Sales Representative.
- The co-branded lockup is the brokerage's own approved mark, so team and
  brokerage carry equal visual weight. **If a team-only or personal logo is ever
  swapped in, the brokerage identification must be the same size beside it.**
- Testimonials are real Google reviews, shown as screenshots, quoted verbatim.
  Deal facts are stated separately in Emma's own voice, never put in a reviewer's
  mouth. Anything naming a specific property's price or terms needs the written
  consent Bulletin 5.4 requires before it goes up.

## Still to do

- [ ] Fill in the Calendly fallback URL in `src/registration.src.html` — two
      `REPLACE-` segments. The link stays hidden until they are filled.
- [ ] Four breakout clips for "Questions you might have before our call"
      (`src/confirmation.src.html`, section 4). Delete any card you have no clip
      for rather than shipping an empty placeholder.
- [ ] **Book a real appointment from a real phone on cellular**, all the way
      through the Calendly step. Calendly inside Typeform inside the page is the
      documented highest-priority mobile risk.
- [ ] Confirm "Emma Pace" matches the RECO registration exactly.
