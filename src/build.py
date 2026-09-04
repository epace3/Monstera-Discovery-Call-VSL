# -*- coding: utf-8 -*-
"""
Assemble the funnel pages: inline the CSS, the co-branded lockup, the review
wall, and the tracking blocks.

Produces three pages:
  vsl_registration_page.html          pixel base + PageView, no conversion
  vsl_confirmation_qualified.html     pixel base + PageView + Schedule  -> /booked
  vsl_confirmation_unqualified.html   pixel base + PageView, NO conversion -> /confirmed

Privacy and terms are NOT built here. The real policies live on monstera.ca and
every page links out to them; netlify.toml 301s /privacy and /terms there.

WHY THE UNQUALIFIED PAGE NOW CARRIES THE PIXEL
Earlier it carried nothing at all. That kept it out of the conversion count,
which was the point, but it also made these leads invisible: with no PageView
there is no audience to exclude them from, so ad spend keeps chasing people who
already booked with the team. The base pixel plus PageView fixes that. The
conversion event is still the gate, and it exists on the qualified page only.
"""
import base64, pathlib, re
import wall

# ============================================================================
# ONE PLACE TO CHANGE THE PIXEL.
# Dataset ID, confirmed by Emma in Events Manager (Sept 2026).
# ============================================================================
PIXEL_ID = '1828499953929219'

CSS    = pathlib.Path('shared.css').read_text()
NGLOGO = 'data:image/webp;base64,' + base64.b64encode(pathlib.Path('ng-real-logo.webp').read_bytes()).decode()

PIXEL_BLOCK = f'''<!-- ============================================================
     META PIXEL - base code. Pixel / dataset ID {PIXEL_ID}.
     ============================================================ -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{PIXEL_ID}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={PIXEL_ID}&ev=PageView&noscript=1" alt=""/></noscript>
<!-- End Meta Pixel Code -->'''

NO_PIXEL_BLOCK = '''<!-- No analytics on this page by design. -->'''

# DEDUPLICATION. The GHL workflow also sends Schedule to the Meta Conversions
# API from the Calendly invitee.created webhook. Two Schedule events for one
# booking double-count unless both carry the SAME eventID, so this passes
# Calendly's invitee UUID as the eventID; the GHL CAPI call must send that same
# UUID as its event_id.
#
# When the UUID is present the browser event carries it as eventID and
# deduplicates cleanly. When it is absent the event still fires, because landing
# on this page means a booking happened and Emma would rather report it than lose
# it. A sessionStorage guard stops a refresh or a back-button return firing a
# second time in the same tab.
#
# OPEN RISK, flagged to Emma Sept 2026: the guard is per-tab. It does NOT
# deduplicate the browser event against the server-side CAPI event, which is a
# different source. While "Pass event details to your redirect page" is OFF in
# the Calendly event, a booking with no invitee_uuid is reported twice: once by
# the browser with no eventID and once by CAPI. Turning that setting ON is what
# actually closes this.
SCHEDULE_BLOCK = '''<script>
(function () {
  if (typeof fbq !== 'function') return;

  // The booking happens inside Calendly's iframe inside Typeform's iframe, so this
  // page cannot observe it directly. It does not need to: Ending B is only reachable
  // through the required Calendly question, so landing here means a booking happened.
  // Guarded so a refresh or a back-button return cannot fire it twice.
  var KEY = 'mdhb_schedule_fired';
  try {
    if (sessionStorage.getItem(KEY)) return;
    sessionStorage.setItem(KEY, '1');
  } catch (e) { /* private mode: storage unavailable, fire once and move on */ }

  var p = new URLSearchParams(window.location.search);
  var inviteeId = p.get('invitee_uuid') || p.get('invitee_id');
  if (inviteeId) {
    fbq('track', 'Schedule', {}, { eventID: inviteeId });
  } else {
    fbq('track', 'Schedule');
  }
})();
</script>'''

# ============================================================================
# LEGAL AND CONTACT LINKS — ONE PLACE, SHARED BY EVERY PAGE.
# The real policies live on monstera.ca and already cover this funnel: lead
# forms, Meta Pixel, SMS consent and opt-out, the GoHighLevel CRM, sharing with
# North Group, retention and access requests. Duplicating them here would create
# two policies for one act of data collection, which is worse than none, so
# these link out instead. netlify.toml also 301s /privacy and /terms there so
# older links do not 404.
# The SMS link matters: the booking form takes a phone number and the lead is
# then called and texted, so the opt-in and opt-out terms must be one click away.
# ============================================================================
LEGAL_LINKS = (
    '<a href="https://monstera.ca/privacy" target="_blank" rel="noopener">Privacy Policy</a> &middot; '
    '<a href="https://monstera.ca/terms" target="_blank" rel="noopener">Terms of Service</a> &middot; '
    '<a href="https://monstera.ca/privacy#sms" target="_blank" rel="noopener">SMS Disclosure</a><br>'
    '<a href="mailto:emma.pace@monstera.ca">emma.pace@monstera.ca</a> &middot; '
    '<a href="tel:+16476437037">647-643-7037</a>'
)

TITLE_QUALIFIED   = "You're Booked with Emma | North Group Real Estate"
TITLE_UNQUALIFIED = "You're Booked | North Group Real Estate"

# (source, output, needs review wall, pixel block, schedule block, title)
TARGETS = [
    ('registration.src.html', 'vsl_registration_page.html',      True,  PIXEL_BLOCK, None, None),
    ('confirmation.src.html', 'vsl_confirmation_qualified.html', False, PIXEL_BLOCK, SCHEDULE_BLOCK, TITLE_QUALIFIED),
    ('confirmation-unqualified.src.html', 'vsl_confirmation_unqualified.html',
                                                                 False, PIXEL_BLOCK, '', TITLE_UNQUALIFIED),
]


for src, out, needs_reviews, pixel, schedule, title in TARGETS:
    h = pathlib.Path(src).read_text()
    for token in ['__SHARED_CSS__', '__NG_LOGO__'] + (['__REVIEWS__'] if needs_reviews else []):
        assert token in h, f'{src} is missing {token}'
    h = (h.replace('__SHARED_CSS__', CSS).replace('__NG_LOGO__', NGLOGO)
           .replace('__LEGAL_LINKS__', LEGAL_LINKS))
    if needs_reviews:
        h = (h.replace('__REVIEWS__', wall.render(None))
               .replace('__REVIEW_COUNT__', str(wall.COUNT)))
    if schedule is not None:
        h = h.replace('__PIXEL_BLOCK__', pixel).replace('__SCHEDULE_BLOCK__', schedule)
        h = h.replace('__PAGE_TITLE__', title)
    pathlib.Path(out).write_text(h)

    # --- hard guarantees, checked on every build ---
    tracked = re.findall(r"fbq\('track',\s*'(\w+)'", h)
    assert f"fbq('init', '{PIXEL_ID}')" in h, f'{out} lost the pixel base code'
    if 'unqualified' in out or 'registration' in out:
        assert tracked == ['PageView'], f'{out} must fire PageView only, found {tracked}'
    else:
        # Two literal Schedule calls appear in the source: the if/else branches
        # for "invitee id present" and "absent". Exactly one RUNS. Counting text
        # occurrences cannot tell you that, so this asserts the shape of the
        # block and the live runtime test proves the count.
        assert tracked[0] == 'PageView', f'{out} must fire PageView first, found {tracked}'
        assert set(tracked) == {'PageView', 'Schedule'}, f'{out} fires unexpected events: {tracked}'
        n = h.count("fbq('track', 'Schedule'")
        assert n == 2, f'{out} should hold exactly the two Schedule branches, found {n}'
        assert 'eventID' in h, f'{out} Schedule must carry an eventID when the invitee id is present'
        assert 'mdhb_schedule_fired' in h, f'{out} Schedule is missing the repeat-fire guard'
    # The confirmation pages describe a phone call, never a video meeting.
    # 'zoom-in' / 'zoom-out' are CSS cursor keywords in shared.css, not a
    # reference to Zoom, so they are excluded rather than renamed.
    if 'confirmation' in out:
        prose = h.lower().replace('zoom-in', '').replace('zoom-out', '')
        assert 'zoom' not in prose, f'{out} still mentions zoom'
    for must in ('monstera.ca/privacy', 'monstera.ca/terms', 'monstera.ca/privacy#sms'):
        assert must in h, f'{out} is missing the {must} link'
    assert '__LEGAL_LINKS__' not in h, f'{out} left the legal-links token unreplaced'
    print(f'{out:36} {len(h):>7,} bytes   {"+".join(tracked)}')

