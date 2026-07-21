#!/usr/bin/env bash
# PaintDial build — run by Netlify on every push (see netlify.toml).
# Regenerates the full ~285 MB site from the ~1 MB of source in this repo.
set -euo pipefail

echo "--- installing Python deps ---"
pip install --quiet --disable-pip-version-check numpy pillow

echo "--- generating HTML pages (gen_pages.py) ---"
cp paints-fixed.json paints.json
python gen_pages.py

echo "--- generating share images (make_share.py) ---"
python make_share.py

echo "--- adding homepage, robots.txt into publish dir ---"
cp index.html site/index.html
cp robots.txt site/robots.txt

echo "--- build complete ---"
echo "pages in site/colours: $(find site/colours -name '*.html' | wc -l)"
echo "share images: $(find site/share -name '*.jpg' | wc -l)"
