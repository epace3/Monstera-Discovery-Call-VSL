# -*- coding: utf-8 -*-
"""
Assemble the funnel pages: inline the CSS, the co-branded lockup, the review
wall, and the tracking blocks.

Produces three pages:
  vsl_registration_page.html          pixel base only, no conversion event
  vsl_confirmation_qualified.html     pixel base + Schedule conversion
  vsl_confirmation_unqualified.html   NO pixel at all, not one byte

The qualified/unqualified split is the traffic gate. Because the unqualified
page carries no pixel code whatsoever, an under-threshold lead cannot fire a
conversion, cannot land in a retargeting audience, and cannot be counted, no
matter how they arrive. That is stronger than gating on a URL parameter.
"""
import base64, pathlib
import wall

# ============================================================================
# ONE PLACE TO CHANGE THE PIXEL.
# Dataset ID, confirmed by Emma in Events Manager (Sept 2026).
# Changing it here updates the registration page and the qualified
# confirmation page together. The unqualified page never receives it.
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

# IMPORTANT: this comment SHIPS in the served HTML, so it must not describe
# the segmentation. A visitor can view-source their own confirmation page, and
# "you were routed here because you are under the price threshold" is the last
# thing they should read. The full explanation lives here in the build script,
# which is never served:
#   This is the UNQUALIFIED confirmation page. Leads under the price threshold
#   are routed here and book with a different agent. It carries no pixel base
#   code, no PageView and no conversion event, so an unqualified booking can
#   never be counted as a conversion or land in a retargeting audience.
#   Never add tracking here "just for visibility".
NO_PIXEL_BLOCK = '''<!-- No analytics on this page by design. -->'''

# Notes for whoever edits this next (kept out of the served HTML):
#   Only qualified traffic reaches this page, so the page itself is the gate;
#   no URL parameter is needed. DEDUPLICATION: the GHL workflow also sends
#   Schedule to the Meta Conversions API from the Calendly invitee.created
#   webhook. Two Schedule events for one booking double-count unless both
#   carry the SAME eventID, so this passes Calendly's invitee UUID as the
#   eventID; configure the GHL CAPI call to send that same UUID as its
#   event_id. To keep Schedule server-side only, delete SCHEDULE_BLOCK.
SCHEDULE_BLOCK = '''<script>
(function () {
  if (typeof fbq !== 'function') return;
  var p = new URLSearchParams(window.location.search);
  var inviteeId = p.get('invitee_uuid') || p.get('invitee_id');
  if (inviteeId) {
    fbq('track', 'Schedule', {}, { eventID: inviteeId });
  } else {
    fbq('track', 'Schedule');
  }
})();
</script>'''

TITLE = "You're In. Watch This Before We Talk | North Group Real Estate"

# (source, output, needs review wall, pixel block, schedule block)
TARGETS = [
    ('registration.src.html', 'vsl_registration_page.html', True, PIXEL_BLOCK, None),
    ('confirmation.src.html', 'vsl_confirmation_qualified.html', False, PIXEL_BLOCK, SCHEDULE_BLOCK),
    ('confirmation.src.html', 'vsl_confirmation_unqualified.html', False, NO_PIXEL_BLOCK, ''),
]

for src, out, needs_reviews, pixel, schedule in TARGETS:
    h = pathlib.Path(src).read_text()
    for token in ['__SHARED_CSS__', '__NG_LOGO__'] + (['__REVIEWS__'] if needs_reviews else []):
        assert token in h, f'{src} is missing {token}'
    h = h.replace('__SHARED_CSS__', CSS).replace('__NG_LOGO__', NGLOGO)
    if needs_reviews:
        h = (h.replace('__REVIEWS__', wall.render(None))
               .replace('__REVIEW_COUNT__', str(wall.COUNT)))
    if schedule is not None:
        h = h.replace('__PIXEL_BLOCK__', pixel).replace('__SCHEDULE_BLOCK__', schedule)
        h = h.replace('__PAGE_TITLE__', TITLE)
    pathlib.Path(out).write_text(h)

    # hard guarantee: the unqualified page must contain no tracking whatsoever
    if 'unqualified' in out:
        for banned in ('fbq', 'facebook.net', 'facebook.com/tr', PIXEL_ID):
            assert banned not in h, f'{out} must not contain {banned!r}'
        print(f'{out:36} {len(h):>7,} bytes   NO PIXEL (verified)')
    else:
        print(f'{out:36} {len(h):>7,} bytes   pixel {PIXEL_ID}')
