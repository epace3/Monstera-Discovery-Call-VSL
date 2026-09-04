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
# If the UUID is missing there is no dedupe key, so this fires NOTHING and lets
# the server-side event be the single report. Firing without an id double-counts;
# firing nothing loses nothing. (Turn on "Pass event details to your redirect
# page" in the Calendly event so the UUID actually arrives.)
SCHEDULE_BLOCK = '''<script>
(function () {
  if (typeof fbq !== 'function') return;
  var p = new URLSearchParams(window.location.search);
  var inviteeId = p.get('invitee_uuid') || p.get('invitee_id');
  // No id means no dedupe key. Fire nothing and let the server-side CAPI
  // event be the single report. Firing without an id double-counts;
  // firing nothing loses nothing.
  if (!inviteeId) return;
  fbq('track', 'Schedule', {}, { eventID: inviteeId });
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
        assert tracked == ['PageView', 'Schedule'], f'{out} must fire PageView then Schedule, found {tracked}'
        assert 'eventID' in h, f'{out} Schedule must carry an eventID'
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

