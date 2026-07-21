# PaintDial — git + Netlify auto-deploy (one-time setup)

This repo is the **~1 MB of source** for paintdial.co.uk. Netlify rebuilds the full
~285 MB site (6,448 pages + 5,582 share images) from it on **every push**, so the big
zip never has to move between a chat, a machine, or a download again. Whichever computer
you're on, you (or Claude) just push a change and the live site updates itself.

## What's in here
- `gen_pages.py` — the generator (all colour pages, brand libraries, alternatives, dupes,
  research pages, sitemap). Includes your 20 July prose fixes.
- `make_share.py` — builds the per-colour social share images.
- `paints-fixed.json` — master paint data (5,582 paints, 9 brands). **Source of truth.**
- `index.html` — hand-maintained homepage (the generator does not touch it).
- `fonts/` — Fraunces + Archivo, needed by the share-image build.
- `netlify.toml` — build command, publish dir, Python version, subdomain 301, edge function.
- `netlify/edge-functions/strip-html.js` — clean-URL 301s.
- `robots.txt`, `build.sh`, `.gitignore`.

The build **output** (`site/`, `paints.json`, any `*.zip`) is git-ignored on purpose —
Netlify regenerates it. Only source is tracked.

## Setup — do this once

### 1. Create the GitHub repo and push
```bash
cd paintdial-repo
git init
git add -A
git commit -m "PaintDial source: git + Netlify auto-build"
# create an EMPTY repo on github.com first (no README), then:
git remote add origin https://github.com/<you>/paintdial.git
git branch -M main
git push -u origin main
```

### 2. Connect it to your EXISTING Netlify site (important)
Link the repo to the **current paintdial.co.uk site** — do NOT create a brand-new site,
or you'll get another orphan subdomain competing for crawl budget.

- Netlify → your paintdial.co.uk site → **Site configuration → Build & deploy →
  Continuous deployment → Link repository** → pick the GitHub repo.
- Netlify reads `netlify.toml` automatically, so build command (`bash build.sh`),
  publish dir (`site`), and Python 3.12 are already set — you shouldn't need to type them.
- Trigger a deploy. First build takes roughly **5–6 minutes** (installs numpy/Pillow,
  generates the pages, then the 5,582 images).

### 3. From then on
Any push to `main` auto-builds and deploys. No zip, no download, no 30 MiB limit,
not tied to any one laptop.

## Housekeeping (from your project notes)
- Delete the stray orphan Netlify site `helpful-phoenix-363162` — it's a crawlable duplicate.
- The `storied-cassata-d25ad3.netlify.app` → apex 301 stays valid only while the repo is
  linked to the same existing site (that's why step 2 says link, don't recreate).

## If you'd rather Claude do the push for you
Enable the GitHub connector in Claude settings (or paste a GitHub token in the chat) and
Claude can create the repo and push directly — then you only do step 2 in Netlify.
