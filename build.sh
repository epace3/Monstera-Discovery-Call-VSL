#!/usr/bin/env bash
# Netlify build. Regenerates every page from src/ and drops them into site/.
# Run it locally the same way before pushing if you want to eyeball the output.
set -euo pipefail
cd src
python3 build.py
mkdir -p ../site/booked ../site/confirmed ../site/privacy ../site/terms
cp vsl_registration_page.html        ../site/index.html
cp vsl_confirmation_qualified.html   ../site/booked/index.html
cp vsl_confirmation_unqualified.html ../site/confirmed/index.html
cp privacy.html                      ../site/privacy/index.html
cp terms.html                        ../site/terms/index.html
echo "built ok"
