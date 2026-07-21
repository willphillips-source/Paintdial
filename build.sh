#!/usr/bin/env bash
# PaintDial build — Netlify runs this on every push. Rebuilds the full site from source.
# The GitHub web upload flattened folders, so this script reconstructs them at build time.
set -euo pipefail

echo "--- deps ---"
pip install --quiet --disable-pip-version-check numpy pillow

echo "--- reconstruct fonts/ from the flat font files ---"
mkdir -p fonts
cp fraunces.ttf archivo.ttf fonts/

echo "--- reconstruct netlify/edge-functions/ from the flat strip-html.js ---"
mkdir -p netlify/edge-functions
cp strip-html.js netlify/edge-functions/strip-html.js

echo "--- generate pages ---"
cp paints-fixed.json paints.json
python gen_pages.py

echo "--- generate share images ---"
python make_share.py

echo "--- add homepage + robots into publish dir ---"
cp index.html site/index.html
cp robots.txt site/robots.txt
echo "--- done ---"
