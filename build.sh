#!/usr/bin/env bash
# Netlify build. Regenerates the funnel pages from src/ and drops them into site/.
# Privacy and terms are not built: they live on monstera.ca and netlify.toml
# redirects /privacy and /terms there.
set -euo pipefail
cd src
python3 build.py
mkdir -p ../site/booked ../site/confirmed
cp vsl_registration_page.html        ../site/index.html
cp vsl_confirmation_qualified.html   ../site/booked/index.html
cp vsl_confirmation_unqualified.html ../site/confirmed/index.html
echo "built ok"
