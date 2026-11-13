#!/usr/bin/env python3
"""
PaintDial page generator (definitive; brands are whatever BRAND_ORDER lists).
Regenerates: all colour pages, redesigned brand library pages,
/colours/ index, sitemap.xml. Run from /home/claude.
"""
import json, math, os, re, unicodedata, html as H
import numpy as np
from collections import Counter
import colorsys

DOMAIN = "https://www.paintdial.co.uk"
import datetime as _dt
TODAY = _dt.date.today().strftime("%B %Y")

# Brand counts as words, COMPUTED from the library. These were previously hardcoded
# ("nine UK brands", "the other eight brands") and had to be hand-edited every time a
# brand was added -- exactly the kind of silent staleness that survives a rebuild,
# because regenerating the site cannot fix a literal. Never hardcode a count again.
_NUMW = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven',
         8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven', 12: 'twelve', 13: 'thirteen',
         14: 'fourteen', 15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
         19: 'nineteen', 20: 'twenty'}
def numword(n):
    return _NUMW.get(n, f'{n}')
# The shortlist (save, compare two, email) is shared by the homepage tool and every colour
# page. Its CSS and script are read from index.html at build time, so there is one copy to
# edit rather than two kept in step by hand.
_IDX = open('index.html', encoding='utf-8').read()
_m_css = re.search(r'/\* ---- shortlist CSS \(gen_pages\.py reads this block[^*]*\*/\n(.*?)\n/\* ---- end shortlist CSS ---- \*/', _IDX, re.S)
_m_js = re.search(r'(/\* ---------- PaintDial shortlist: save paints on this device.*?\}\)\(\);)\s*</script>', _IDX, re.S)
assert _m_css and _m_js, 'shortlist CSS/JS markers not found in index.html'
SHORTLIST_CSS = _m_css.group(1) + '\n'
SHORTLIST_JS = _m_js.group(1) + '\n'

import json as _json

def _breadcrumb(trail):
    """trail = [(name, url_path_or_None)]; last item usually current page (no url needed but we include it)."""
    items=[]
    for pos,(nm,pth) in enumerate(trail, start=1):
        it={"@type":"ListItem","position":pos,"name":nm}
        if pth: it["item"]=DOMAIN+pth
        items.append(it)
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items}

def _color_seo(name, brand, hexv, slug, desc):
    """A DefinedTerm: a named colour within a brand's defined range.
       NOT a Product - PaintDial does not sell paint. A Product node without
       offers/review/aggregateRating is invalid (GSC flagged this 27 Jul 2026) and
       was never eligible for a product rich result anyway; all three fields Google
       asks for would have to be fabricated, so the TYPE is the thing to fix.
       'color' and 'additionalProperty' are Product-only and are dropped with it."""
    return {"@context":"https://schema.org","@type":"DefinedTerm",
            "name":f"{name} by {brand}",
            "inDefinedTermSet":{"@type":"DefinedTermSet","name":f"{brand} paint colours"},
            "termCode":hexv,
            "image":f"{DOMAIN}/share/{slug}.jpg","url":f"{DOMAIN}/colours/{slug}",
            "description":desc}

def _itemlist(entries):
    """entries = [(name, url_path)] in ranked order -> ItemList of links actually shown on the page."""
    return {"@context":"https://schema.org","@type":"ItemList",
            "itemListElement":[{"@type":"ListItem","position":n,"url":DOMAIN+u,"name":nm}
                               for n,(nm,u) in enumerate(entries, start=1)]}

def heart(name, brand, hexv):
    nm=H.escape(name, quote=True); br=H.escape(brand, quote=True)
    return (f'<button class="pd-heart" data-name="{nm}" data-brand="{br}" data-hex="{hexv}" '
            f'aria-label="Save {nm} to your shortlist" title="Save to shortlist">'
            '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg></button>')

# ---------- full-screen compare view ----------
# The behaviour lives in pd-compare.js (one file, shared with the homepage so the two
# can't drift). Pages only carry the trigger button and the small CSS that styles it,
# inline so the button never flashes unstyled before the deferred script arrives.
# The button sits BESIDE the card's link, never inside it (a button inside an anchor is
# invalid HTML, the same lesson as the shortlist heart) and above the stretched link.
COMPARE_BTN_CSS = ('.pd-cmp-btn{position:absolute;top:8px;left:8px;display:inline-flex;align-items:center;gap:5px;height:30px;padding:0 11px 0 9px;border:1px solid rgba(33,31,27,.14);border-radius:999px;background:rgba(255,255,255,.92);backdrop-filter:blur(3px);box-shadow:0 1px 2px rgba(33,31,27,.08);cursor:pointer;font-family:inherit;font-size:11.5px;font-weight:600;letter-spacing:.01em;line-height:1;color:#211F1B;white-space:nowrap;z-index:2;transition:transform .12s,box-shadow .12s}'
                   '.pd-cmp-btn:hover{transform:translateY(-1px);box-shadow:0 3px 8px rgba(33,31,27,.14)}'
                   '.pd-cmp-btn:focus-visible{outline:2px solid #5E7E8B;outline-offset:1px}'
                   '.pd-cmp-btn svg{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex:none}'
                   '@media(max-width:560px){.pd-cmp-btn{height:27px;font-size:11px;padding:0 10px 0 8px}}'
                   # The big swatch at the top of a colour or alternatives page is itself a button
                   # that opens the colour full screen (openSolo in pd-compare.js). It covers the
                   # swatch and sits under the shortlist heart, as a sibling, never around it.
                   '.hero-sw{position:relative}'
                   '.pd-solo{position:absolute;inset:0;width:100%;height:100%;border:0;padding:0;margin:0;background:none;cursor:zoom-in;z-index:1;font:inherit;-webkit-tap-highlight-color:transparent}'
                   '.pd-solo:focus-visible{outline:2px solid #5E7E8B;outline-offset:-5px}'
                   '.pd-solo i{position:absolute;top:8px;left:8px;width:30px;height:30px;border-radius:50%;background:rgba(255,255,255,.82);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;color:#8C8578;transition:transform .12s,color .12s}'
                   '.pd-solo:hover i{transform:scale(1.12);color:#5E7E8B}'
                   '.pd-solo svg{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}'
                   '@media(max-width:560px){.pd-solo i{width:27px;height:27px}}')
COMPARE_SCRIPT = '<script src="/pd-compare.js" defer></script>'
_CMP_SVG = '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>'

def solo_btn(p, chip=True):
    """Covers a hero swatch and opens that colour full screen. chip = show the small
       expand icon in the corner (left off on the narrow alternatives-page swatch)."""
    nm=H.escape(p['name'], quote=True); br=H.escape(p['brand'], quote=True)
    icon = f'<i aria-hidden="true">{_CMP_SVG}</i>' if chip else ''
    return (f'<button class="pd-solo" type="button" data-hex="{p["hex"]}" data-name="{nm}" data-brand="{br}" '
            f'aria-label="See {nm} full screen" title="See it full screen">{icon}</button>')

def cmp_btn(a, b, word):
    """Trigger for the full-screen compare view. a = the colour being matched (shown on
       the left), b = the match (right); word = the closeness word shown in the view."""
    an=H.escape(a['name'], quote=True); ab=H.escape(a['brand'], quote=True)
    bn=H.escape(b['name'], quote=True); bb=H.escape(b['brand'], quote=True)
    return (f'<button class="pd-cmp-btn" type="button" data-ahex="{a["hex"]}" data-aname="{an}" data-abrand="{ab}" '
            f'data-bhex="{b["hex"]}" data-bname="{bn}" data-bbrand="{bb}" data-word="{H.escape(word, quote=True)}" '
            f'aria-label="Compare {an} with {bn} full screen" title="See the pair full screen">{_CMP_SVG}<span>Compare</span></button>')

def _ldjson(*objs):
    return "".join(f'<script type="application/ld+json">{_json.dumps(o, ensure_ascii=False, separators=(",",":"))}</script>' for o in objs)
AWIN_AFFID = "2971455"
# Freshlick (Awin #101923) retailer route for brands with no direct programme (Crown, Little Greene).
# DORMANT while None -> direct links. Set to 101923 once Freshlick approves you, then regenerate.
FRESHLICK_MID = None
FRESHLICK_BRANDS = {"Little Greene", "Crown"}
# buy-links.json holds a direct link per colour for brands whose links can't be built
# from the name: Valspar (its tester pot on B&Q), Johnstone's (its colour page) and Lick
# (its product page with the sample selected). Keyed by colour code, or name where the
# brand has no codes. Each brand's _source says where the links came from.
_BL = json.load(open('buy-links.json', encoding='utf-8'))
BUY_LINKS = {b: v['links'] for b, v in _BL.items() if not b.startswith('_')}
# Colours the brand's own site no longer has a page for: no button rather than a link
# that lands on the wrong page.
UNLISTED = {b: set(v.get('unlisted', [])) for b, v in _BL.items() if not b.startswith('_')}
# Decorating Centre Online (Awin advertiser 105177): retailer route for the brands/colours it
# stocks. dco-links.json (brand -> {code-or-name: raw DCO deep link}) is built by
# build_dco_links.py from DCO's Awin product feed. Takes priority over a brand-direct link
# because DCO pays commission and the brand sites (F&B, Dulux...) don't. Dormant if the file
# is absent; only colours DCO stocks get a link, the rest keep their brand link.
DCO_MID = "105177"
try:
    _dco = json.load(open('dco-links.json', encoding='utf-8'))
    DCO_LINKS = {b: v for b, v in _dco.items() if not b.startswith('_')}
except FileNotFoundError:
    DCO_LINKS = {}
# Crown Paints (Awin advertiser 122260, approved 10 Nov 2026): brand-direct programme. Its own
# crownpaints.com colour URLs are wrapped with Awin to earn commission; dormant if None.
CROWN_MID = "122260"
# Farrow & Ball colours Decorating Centre Online sells only as a 750ml tin, with no sample pot
# (link audit, 10 Nov 2026). The button says "Order a tester", so these go to farrow-ball.com,
# whose colour pages are sample-pot pages, and give up the commission.
DCO_NO_SAMPLE = {'Farrow & Ball': {'No.13', 'No.15', 'No.2009', 'No.253', 'No.290', 'No.44', 'No.49', 'No.60', 'No.95',
                                   'No.CC8', 'No.W101', 'No.W40', 'No.W5', 'No.W53', 'No.W55', 'No.W7', 'No.W92', 'No.W93'},
                 # These two open on a 2.5L tin and a 250ml pot there; the brands' own pages sell a sample.
                 'Dulux Heritage': {'True White'}, 'Paint & Paper Library': {'New Black'}}
# dco-stock.json: colours whose tester was out of stock at Decorating Centre Online at the last
# check (its _checked date). An out-of-stock tester is a dead end for the visitor and earns
# nothing, so these go to the brand's own page until a later check finds them back in stock.
try:
    _dst = json.load(open('dco-stock.json', encoding='utf-8'))
    for _b, _v in _dst.items():
        if not _b.startswith('_'):
            DCO_NO_SAMPLE.setdefault(_b, set()).update(_v)
except FileNotFoundError:
    pass
BRAND_ORDER = ['Farrow & Ball', 'Little Greene', 'Craig & Rose', 'Dulux', "Johnstone's", 'Valspar', 'Lick', 'Crown', 'COAT', 'Lakeland Paints',
               'Earthborn', 'Fired Earth', 'Paint & Paper Library', 'Edward Bulmer', 'Dulux Heritage', 'Zoffany', 'Mylands', 'Sanderson',
               'Benjamin Moore', 'Tikkurila']
# NOT A PUBLISHED VALUE. Every other brand's values are its own published swatches, and anything
# that says "each brand's own published swatch" must say where these differ, so the claim is built
# from SWATCH_SAMPLED and SOURCE_NOTE below rather than typed, and the brand and colour pages carry it.
# Zoffany (156, added 4 Nov 2026) publishes no colour values: zoffany.design shows each colour only
# as a JPEG swatch, and its product API has no colour field. From 7 Nov 2026 its values are read
# from those swatch images (the main product image on each colour's page, a flat field with no
# texture or shading; sampled at 7 points, every one identical, so the value is the image's own
# colour to within JPEG rounding of about 1). Until then they were the ones Brewers publishes for
# Zoffany, which turned out to run on a tone curve of their own: whites close, darks 15-16 L*
# darker than Zoffany's swatches, median dE00 8.1 across all 156, only 9 within 2. Eight sampled
# values were cross-checked against allpaintcolours.co.uk, which also reads Zoffany's swatches: all
# within 1. Will chose the switch on 7 Nov 2026. Names, codes (ZOP1001-1156) and links are Zoffany's.
# Sanderson (154, added 5 Nov 2026) is Zoffany's sister brand (Sanderson Design Group) on the same
# site platform, with the same gap: sanderson.design shows each colour only as a JPEG swatch. From
# 8 Nov 2026 its values are read from those swatch images the same way (flat fields, all 7 sample
# points identical on every one). Until then they were Brewers' values, which differ less than
# Zoffany's did (median dE00 3.3, 21 of 154 within 2, Sanderson's swatches about 2 L* lighter) but
# the same direction. Sanderson's own swatches are rougher in places: seven greys are exactly
# neutral (R=G=B) and Peony Pink reaches full red. Will chose the switch anyway, for one source
# across both sister brands and because it is what people choosing a Sanderson colour see; the
# site's job is a shortlist to order testers from. Names, codes (SAP1001-1154) and links are Sanderson's.
SWATCH_SAMPLED = {
    'Zoffany': 'https://www.zoffany.design/paint',
    'Sanderson': 'https://www.sanderson.design/paint',
    # Fired Earth (132, added 10 Nov 2026): no published values; firedearth.com shows each colour
    # as a flat swatch image (the uniform <name>.png product image, not the lifestyle photo),
    # sampled at 7 points, all identical. QA'd against Brewers (median dE00 ~1.2). Matt Emulsion
    # 2.5L £54.95. Names and links are Fired Earth's own.
    'Fired Earth': 'https://www.firedearth.com/paint',
}
# SOURCED FROM A STOCKIST, NOT THE BRAND: none at present. Kept so a brand can be added here with
# (stockist, url) and every source sentence picks it up. Brewers mirrors brand values exactly where
# a brand publishes its own (all 157 Mylands colours it lists match mylands.com), but did not for
# Zoffany or Sanderson, so check a stockist against the brand's own swatches before using it.
SOURCE_NOTE = {}
# Mylands (193, added 5 Nov 2026): the brand's own values. Each product page on mylands.com sets
# the colour as a CSS variable on its colour band (<div class="ux-pdp" style="--ux-band:#...">).
# Core range (No.1-297) plus the Beata Heuman (BH.01-24) and Jinny Blom (JB.01-12) collections,
# all Marble Matt Emulsion 2.5L £68. The Film, TV & Theatre (FTT) scenic range is left out: it is
# specialist stage and screen paint (CSO Green is chroma-key green), four of its 20 are metallics
# with no value, and one value (#0026FF) is not a credible paint swatch.
# Benjamin Moore (3,543, added 5 Nov 2026): the brand's own values from benjaminmoorepaint.co.uk,
# the UK distributor's site (Benjamin Moore UK Ltd). Its colour-collection pages set each tile's
# value in the tile's own script; colour pages show the same value (Hale Navy HC-154 = #434B56 on
# both). All six ranges sold in the UK: Affinity (AF), Colour Stories (CS), Off-White (OC),
# Historical (HC), Classic (001-1680) and Color Preview (2000-10 to 2175-70). 95 Classic rows repeat
# an Off-White or Historical colour exactly (same name and value) and are left out as duplicates.
# Links go to the colour's page on that site, which looks colours up by code (checked: a wrong
# name with a right code still resolves; a wrong code errors). Sold direct with UK delivery, from
# its Chelsea showroom and through Brewers. Priced on the US gallon (3.79L), the size it sells
# besides a quart: Regal Select Matte GBP 88.50 to Aura Matte GBP 106, so premium, like F&B.
# Tikkurila (377, added 5 Nov 2026): the brand's own values. tikkurila.co.uk sets each colour's
# swatch as an inline background-color on its colour listing. Named interior colours only; one
# transparent woodstain (Yellow Transpar) is left out, and a " Tvt" suffix on one name dropped.
# Sold direct, priced on its 3L tin (2.7L of paint): Optiva Matt 5 GBP 50.54 to Optiva Ceramic
# Super Matt 3 GBP 61.63, which per litre is Farrow & Ball money, hence premium tier, so it is
# never offered as a cheaper dupe.
# Valspar was expanded on 5 Nov 2026 from 284 to its full published UK range, 1,970 colours
# (valsparpaint.co.uk/all-colours/, 73 pages, each colour's chip background; 40 of 40 random colour
# pages agree with the listing; all 284 existing values unchanged).
# Dulux Heritage (113, added 4 Nov 2026) is Dulux's designer range with its own names, site and
# price (Velvet Matt 2.5L £45-47), so it is its own brand here rather than more Dulux rows. Values
# are the "rgb" field in duluxheritage.co.uk's page data, which the site renders its own swatches
# from; none of the 113 were in the main Dulux scrape. One pair shares a value on Dulux's side
# (Linen White / Roman White). Looked at the same day and left out, swatch images only:
# Little Knights (99 colours, PNG swatches) and Rust-Oleum (JPEG swatches).
# Earthborn (85, Claypaint 2.5L £61.50), Paint & Paper Library (187, Pure Flat Emulsion 2.5L £73)
# and Edward Bulmer (149, Emulsion 2.5L £70) were added Nov 2026, all premium. Values are each
# brand's own: Earthborn and P&PL set the colour as a CSS background on their own pages;
# Edward Bulmer's product gallery opens with a generated flat SVG swatch filled with the colour.
# Annie Sloan was looked at and left out: its swatches are PNG images with no published value.
# Lakeland Paints: small Cumbrian maker, sold direct only, one tin size (5L matt, £89.96 ex VAT
# = £107.95 inc, so £21.59/L, checked Nov 2026). Per litre that lands between Dulux and
# Farrow & Ball, hence mid-range, not premium: it is a specialist (zero-VOC) brand, not a
# luxury one. Its 265 colours are the brand's own on-screen swatches (the colour picker on
# lakelandpaints.co.uk), like Lick and COAT. No per-colour pages exist, so every Lakeland
# colour links to the matchpot page, where the picker lives.
TIER = {'Farrow & Ball': 3, 'Little Greene': 3, 'Craig & Rose': 3, 'Lick': 3, 'COAT': 3,
        'Earthborn': 3, 'Fired Earth': 3, 'Paint & Paper Library': 3, 'Edward Bulmer': 3, 'Dulux Heritage': 3, 'Zoffany': 3,
        'Mylands': 3, 'Sanderson': 3, 'Benjamin Moore': 3, 'Tikkurila': 3,
        'Dulux': 2, 'Crown': 2, 'Lakeland Paints': 2, "Johnstone's": 1, 'Valspar': 1}
TIER_WORD = {3: 'Premium', 2: 'Mid-range', 1: 'Value'}

paints = json.load(open('paints.json'))
N = len(paints)
NBRANDS = len({p['brand'] for p in paints})
BRANDS_WORD = numword(NBRANDS)          # e.g. "nine"  -> "{BRANDS_WORD} brands sold in the UK"
OTHERS_WORD = numword(NBRANDS - 1)      # e.g. "eight" -> "the other {OTHERS_WORD} brands"
assert {p['brand'] for p in paints} == set(BRAND_ORDER), \
    f"paints.json brands {sorted({p['brand'] for p in paints})} != BRAND_ORDER {sorted(BRAND_ORDER)}"
assert set(TIER) == set(BRAND_ORDER), "every brand in BRAND_ORDER needs a TIER"
# Buy and retailer links are looked up by colour code, so two colours sharing a code within a
# brand would send one colour's "Order a tester" to the other's page. That happened once:
# Stone Blue was coded No.85 (Oval Room Blue's number; Stone Blue is No.86) and its tester
# button went to Oval Room Blue at Decorating Centre Online, Nov 2026.
_codes = {}
for _p in paints:
    if _p.get('code'):
        _k = (_p['brand'], _p['code'])
        assert _k not in _codes, f"{_p['brand']} code {_p['code']} is on both {_codes[_k]} and {_p['name']}"
        _codes[_k] = _p['name']

# Price bands (£ / ££ / £££) come from the homepage's PRICING map and PRICE_BANDS, so the
# colour pages and the tool can never show a brand in two different bands. A band is the
# midpoint of the brand's typical per-litre price; the tier above is market position and
# can differ (Lick is premium but ££; Lakeland is mid-range but £££).
_pr = re.search(r'const PRICING=\{(.*?)\n\};', _IDX, re.S).group(1)
PRICING = {(m.group(1) or m.group(2)): [float(x) for x in m.group(3).split(',')]
           for m in re.finditer(r'^\s*(?:"([^"]+)"|\'([^\']+)\')\s*:\s*\[([\d.,\s]+)\]', _pr, re.M)}
PRICE_BANDS = [float(x) for x in re.search(r'const PRICE_BANDS=\[([\d.,\s]+)\];', _IDX).group(1).split(',')]
PRICE_TIN_L = float(re.search(r'const PRICE_TIN_L=([\d.]+);', _IDX).group(1))
assert set(PRICING) == set(BRAND_ORDER), f"PRICING in index.html {sorted(PRICING)} != BRAND_ORDER"
PRICE_CHECKED = re.search(r"const PRICE_CHECKED='([^']+)';", _IDX).group(1)
PRICE_TIN_WHY = dict(re.findall(r"^\s*'([^']+)':'([^']+)',\s*$", re.search(r'const PRICE_TIN_WHY=\{(.*?)\n\};', _IDX, re.S).group(1), re.M))
def price_line(brand):
    """One sentence giving the brand's typical price per litre, from the homepage's PRICING map
    and worded like the homepage's price note: the tin size behind the figure and the date are
    always stated, and nothing is compared with anything (no saving, no "cheaper")."""
    lo, hi, *tin = PRICING[brand]
    tin_l = tin[0] if tin else PRICE_TIN_L
    a, b = lo / tin_l, hi / tin_l
    fig = f'\u00a3{a:.2f}' if a == b else f'\u00a3{a:.2f} to \u00a3{b:.2f}'
    basis = f'a {tin_l:g}L tin mixed to your colour'
    if tin:
        basis += f' ({PRICE_TIN_WHY[brand]})'
    one_size = tin and 'only size' in PRICE_TIN_WHY[brand]
    return (f'{H.escape(brand)} is typically {fig} a litre, based on {basis}, checked {PRICE_CHECKED}. '
            + ('Retailers vary.' if one_size else 'Retailers vary, and bigger tins work out less per litre.'))
# ---------- Paint details: what each brand says about its own wall matt ----------
# One product per brand: its main matt for interior walls, the same product PRICING prices.
# Every figure is as the brand's own product page or data sheet states it (read Nov 2026; notes
# and sources in the Project doc paintdial-paint-details-research-nov26.md). A field the brand
# does not state is left out, never estimated: Johnstone's gives "32m2" with no tin size,
# Crown and Zoffany give no coverage, and Lick's only figure is on a retailer's listing.
# Nothing here compares one brand with another. Re-check with the prices.
PAINT_CHECKED = 'Nov 2026'
PAINT_INFO = {
 'Farrow & Ball': dict(product='Estate Emulsion', finish='Very flat matt, 2% sheen', coverage='Up to 14 m² a litre', coats='2',
    recoat='2 hours', tins='2.5L and 5L', note='Wipeable, not washable.', src='product page',
    url='https://www.farrow-ball.com/paint-finishes/estate-emulsion'),
 'Little Greene': dict(product='Absolute Matt Emulsion', finish='Matt, under 5% sheen', coverage='14 m² a litre', coats='2',
    recoat='4 hours', tins='250ml, 1L, 2.5L, 5L and 10L', src='data sheet', url=None),
 'Paint & Paper Library': dict(product='Pure Flat Emulsion', finish='Matt, under 5% sheen', coverage='15 m² a litre', coats='2',
    recoat='4 hours', tins='250ml, 750ml, 2.5L and 5L', src='data sheet', url=None),
 'Craig & Rose': dict(product='1829 Chalky Emulsion', finish='Matt', coverage='About 14 m² a litre', coats='2',
    recoat='4 hours', tins='750ml, 2.5L and 5L', src='data sheet', url=None),
 'Dulux': dict(product='Easycare Washable & Tough Matt', finish='Matt', coverage='Up to 13 m² a litre', coats='2',
    recoat='2 to 4 hours', tins='2.5L, 5L and 10L', src='product page',
    url='https://www.dulux.co.uk/en/products/dulux-easycare-washable-and-tough-matt'),
 'Dulux Heritage': dict(product='Velvet Matt', finish='Matt', coverage='13 m² a litre', coats='2',
    recoat='2 to 4 hours', tins='1L, 2.5L, 5L and 10L', note='Washable.', src='product page',
    url='https://www.duluxheritage.co.uk/en/products/details/dulux-heritage-velvet-matt'),
 "Johnstone's": dict(product='Wall and Ceiling Matt', finish='Matt', recoat='2 to 4 hours', tins='2.5L and 5L',
    note='Wipeable.', src='product page', url='https://www.johnstonespaint.com/wall-and-ceiling-matt-paint'),
 'Valspar': dict(product='Premium Walls & Ceilings', what='paint', finish='Matt, mid-sheen or silk', coverage='10 m² a litre',
    recoat='2 to 4 hours', tins='1L, 2.5L and 5L', src='product page',
    url='https://www.valsparpaint.co.uk/paint-products/walls-ceilings/premium-walls-ceilings'),
 'Crown': dict(product='Walls & Ceilings Matt Emulsion', finish='Matt', recoat='4 hours', tins='2.5L and 5L',
    src='product page', url='https://www.crownpaints.com/paint/walls-ceilings-matt-emulsion'),
 'COAT': dict(product='Flat Matt', finish='Very flat matt, 2% sheen', coverage='About 10 m² a litre', coats='2',
    recoat='2 to 4 hours', tins='1L, 2.5L and 5L', src='product page and data sheet', url='https://coatpaints.com/pages/flat-matt-paint'),
 'Lick': dict(product='Matt', finish='Matt, low sheen', coverage='10 to 12 m² a litre', coats='2', tins='2.5L',
    src='product pages', url='https://lick.com/'),
 'Earthborn': dict(product='Claypaint', finish='Very flat matt, about 2% sheen', coverage='About 10 m² a litre',
    recoat='6 to 12 hours', tins='2.5L and 5L', note='Highly breathable, and listed by Earthborn for lime plaster.', src='data sheet',
    url='https://earthbornpaints.co.uk/cdn/shop/files/Claypaint_Data_Sheet_2026_V1.pdf'),
 'Edward Bulmer': dict(product='Emulsion', finish='Dead matt, 2% sheen', coverage='12 m² a litre', coats='2',
    recoat='4 to 6 hours', tins='2.5L and 5L', note='Highly breathable, and suitable for new lime and gypsum plaster.', src='data sheet',
    url='https://www.edwardbulmerpaint.co.uk/app/uploads/2022/07/Emulsion-June-2022.pdf'),
 'Mylands': dict(product='Marble Matt Emulsion', finish='Very flat matt, 3% sheen', coverage='About 15 m² a litre',
    recoat='1 to 2 hours', note='Washable.', src='product page', url='https://mylands.com/marble-matt-emulsion'),
 'Sanderson': dict(product='Active Emulsion', finish='Matt, under 5% sheen', coverage='About 12 m² a litre', coats='2',
    recoat='2 to 4 hours', tins='2.5L and 5L', note='Wipeable and washable.', src='data sheet',
    url='https://www.sanderson.design/static/media/akeneo_connector/reference_entities/records/S/a/Sanderson_Active_Emulsion_Data_Sheet_April_2026_5ea7.pdf'),
 'Zoffany': dict(product='Elite Emulsion', what='emulsion', finish='Matt', tins='1L and 2.5L', src='product pages', url='https://www.zoffany.design/paint'),
 'Fired Earth': dict(product='Matt Emulsion', finish='Matt', coverage='14 m² a litre', coats='2',
    recoat='4 hours', tins='2.5L and 5L', note='Wipeable, not washable.', src='advice sheet', url=None),
 'Tikkurila': dict(product='Optiva Matt 5', finish='Matt', coverage='8 to 16 m² a litre', src='product page',
    url='https://www.tikkurila.co.uk/optiva-matt-5'),
 'Benjamin Moore': dict(product='Regal Select Matte', finish='Matt', coverage='37 to 42 m² from a 3.79L tin (a US gallon)',
    coats='2 on bare walls, 1 or 2 over paint', recoat='1 to 2 hours', src='data sheet',
    url='https://benjaminmoorepaint.co.uk/products/datasheet/technical/1010'),
 'Lakeland Paints': dict(product='Matt Wall Paint', finish='Flat matt', coverage='About 65 m² a coat from a 5L tin, on hard, non-porous walls',
    coats='2', recoat='2 hours', tins='5L', note='Washable.', src='tech help page', url='https://www.lakelandpaints.co.uk/tech-help'),
}
assert set(PAINT_INFO) == set(BRAND_ORDER), f"PAINT_INFO brands {sorted(set(PAINT_INFO) ^ set(BRAND_ORDER))} don't match BRAND_ORDER"
# ---------- Paint calculator ----------
# The calculator (/paint-calculator/, calc/tool.html) needs each brand's coverage as numbers.
# CALC_COV restates the PAINT_INFO coverage text as (lowest m², highest m², from how many litres),
# and the check below fails the build if a number here is not in that text, so the two cannot
# drift apart. A brand with no coverage in PAINT_INFO has no entry: the calculator then asks for
# the figure on the tin and estimates nothing (agreed with Will, 12 Nov 2026). No prices.
CALC_PATH = '/paint-calculator/'
CALC_COV = {
 'Farrow & Ball': (14, 14, 1), 'Little Greene': (14, 14, 1), 'Paint & Paper Library': (15, 15, 1),
 'Craig & Rose': (14, 14, 1), 'Dulux': (13, 13, 1), 'Dulux Heritage': (13, 13, 1), 'Valspar': (10, 10, 1),
 'COAT': (10, 10, 1), 'Lick': (10, 12, 1), 'Earthborn': (10, 10, 1), 'Edward Bulmer': (12, 12, 1),
 'Mylands': (15, 15, 1), 'Sanderson': (12, 12, 1), 'Fired Earth': (14, 14, 1), 'Tikkurila': (8, 16, 1),
 'Benjamin Moore': (37, 42, 3.79), 'Lakeland Paints': (65, 65, 5),
}
assert set(CALC_COV) == {b for b, d in PAINT_INFO.items() if d.get('coverage')}, \
    f"CALC_COV and PAINT_INFO disagree about which brands state a coverage: {sorted(set(CALC_COV) ^ {b for b, d in PAINT_INFO.items() if d.get('coverage')})}"
for _b, (_lo, _hi, _per) in CALC_COV.items():
    _nums = set(re.findall(r'\d+(?:\.\d+)?', PAINT_INFO[_b]['coverage'].replace('m²', '')))
    for _n in {_lo, _hi} | ({_per} if _per != 1 else set()):
        assert f'{_n:g}' in _nums, f"CALC_COV {_b}: {_n:g} is not in its PAINT_INFO coverage text ({PAINT_INFO[_b]['coverage']})"
    assert (_per == 1) == ('a litre' in PAINT_INFO[_b]['coverage']), f"CALC_COV {_b}: per-litre and the coverage text disagree"

def calc_data():
    rows = []
    for b in BRAND_ORDER:
        d = PAINT_INFO[b]
        tins = []
        for n, unit in re.findall(r'(\d+(?:\.\d+)?)\s*(ml|L)\b', d.get('tins', '')):
            litres = float(n) / 1000 if unit == 'ml' else float(n)
            if litres >= 0.75:      # 250ml pots are for samples and touching up, not for walls
                tins.append(litres)
        rows.append({'slug': base_slug(b), 'name': b.replace("'", '’'), 'product': d['product'], 'what': d.get('what', 'matt'),
                     'coverage': d.get('coverage'), 'cov': list(CALC_COV[b]) if b in CALC_COV else None,
                     'upto': (d.get('coverage') or '').startswith('Up to'), 'coats': d.get('coats'), 'tins': sorted(set(tins))})
    return rows
def paint_block(brand):
    d = PAINT_INFO[brand]
    b = H.escape(brand)
    poss = b if b.endswith(('’s', '&#x27;s')) else b + '’' if b.endswith('s') else b + '’s'
    rows = [('Finish', d.get('finish')), ('Coverage', d.get('coverage')), ('Coats', d.get('coats')),
            ('Second coat after', d.get('recoat')), ('Tins', d.get('tins'))]
    dl = ''.join(f'<div><dt>{k}</dt><dd>{H.escape(v)}</dd></div>' for k, v in rows if v)
    note = f' {H.escape(d["note"])}' if d.get('note') else ''
    src = (f'<a href="{d["url"]}" rel="nofollow noopener" target="_blank" style="color:inherit">{d["src"]}</a>'
           if d.get('url') else d['src'])
    tail = ' Coverage depends on the wall.' if d.get('coverage') else ''
    # Headed with the tin's own name ("Farrow & Ball Estate Emulsion"), like the page's other
    # headings, which say what is in the section. "The paint" read as a label, not a description.
    return (f'<h2>{b} {H.escape(d["product"])}</h2>'
            f'<p class="sub">{poss[0].upper() + poss[1:]} {d.get("what", "matt")} for walls and ceilings.{note}</p>'
            f'<dl class="pinfo">{dl}</dl>'
            f'<p class="afftext">From {poss} own {src}, checked {PAINT_CHECKED}.{tail} '
            f'<a href="{CALC_PATH}?brand={base_slug(brand)}">Work out how much you need</a>.</p>')

def price_band(brand):
    lo, hi, *tin = PRICING[brand]
    mid = (lo + hi) / 2 / (tin[0] if tin else PRICE_TIN_L)
    return 1 if mid < PRICE_BANDS[0] else 2 if mid < PRICE_BANDS[1] else 3
def band_html(brand):
    n = price_band(brand)
    return f'<span class="pband" aria-label="Price band {n} of 3">{"£" * n}<i aria-hidden="true">{"£" * (3 - n)}</i></span>'

def brand_list(sep=', ', last=' and ', esc=True):
    """'Farrow &amp; Ball, Little Greene, ... Crown and COAT' from BRAND_ORDER. Any copy that
    names the brands must use this, never a typed list: the old typed lists went stale
    twice (one missed Craig & Rose, Crown and COAT for a year)."""
    names = [b.replace("'", '’') for b in BRAND_ORDER]
    names = [H.escape(n, quote=False) if esc else n for n in names]
    return sep.join(names[:-1]) + last + names[-1]

assert set(SOURCE_NOTE) <= set(BRAND_ORDER), "SOURCE_NOTE names a brand not in BRAND_ORDER"
assert set(SWATCH_SAMPLED) <= set(BRAND_ORDER), "SWATCH_SAMPLED names a brand not in BRAND_ORDER"
assert not set(SWATCH_SAMPLED) & set(SOURCE_NOTE), "a brand can't be in both SWATCH_SAMPLED and SOURCE_NOTE"

def _swatch_brands():
    # Brands whose values are read from their own swatch images, in BRAND_ORDER.
    return [b for b in BRAND_ORDER if b in SWATCH_SAMPLED]

def _swatch_clause(html=True):
    # "Zoffany, which publishes no values, so they are read from the swatch images on its own
    # site" (or the plural form). '' if no brand is swatch-sampled.
    sw = _swatch_brands()
    if not sw:
        return ''
    names = [H.escape(b) if html else b for b in sw]
    if len(sw) == 1:
        place = (f'<a href="{SWATCH_SAMPLED[sw[0]]}" rel="nofollow noopener" target="_blank">its own site</a>'
                 if html else 'its own site')
        return f'{names[0]}, which publishes no values, so they are read from the swatch images on {place}'
    return f'{_and(names)}, which publish no values, so they are read from the swatch images on their own sites{_swatch_links(html)}'

def _swatch_links(html=True):
    # " (Zoffany, Sanderson)" linking each brand's paint listing, for the plural sentences; '' in
    # plain text, where the brands are already named.
    if not html or len(_swatch_brands()) < 2:
        return ''
    return ' (' + ', '.join(f'<a href="{SWATCH_SAMPLED[b]}" rel="nofollow noopener" target="_blank">{H.escape(b)}</a>'
                            for b in _swatch_brands()) + ')'

STOCKIST_HOME = {'Brewers': 'https://www.brewers.co.uk/'}

def _and(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]

def _by_stockist():
    # {stockist: [brands...]} in BRAND_ORDER, so one sentence covers every brand a stockist sources.
    out = {}
    for b in BRAND_ORDER:
        if b in SOURCE_NOTE:
            out.setdefault(SOURCE_NOTE[b][0], []).append(b)
    return out

def source_exception(html=True):
    # The clause that qualifies "each brand's own published swatch", or '' if every brand
    # publishes its own. Gives e.g. ", except Zoffany, which publishes no values, so they are read
    # from the swatch images on its own site; and Sanderson, which publishes none: its values are
    # the ones Brewers, its main UK stockist, publishes".
    if not SOURCE_NOTE and not SWATCH_SAMPLED:
        return ''
    bits = [_swatch_clause(html)] if SWATCH_SAMPLED else []
    for stockist, brands in _by_stockist().items():
        url = SOURCE_NOTE[brands[0]][1] if len(brands) == 1 else STOCKIST_HOME.get(stockist, SOURCE_NOTE[brands[0]][1])
        sname = (f'<a href="{url}" rel="nofollow noopener" target="_blank">{stockist}</a>' if html else stockist)
        names = [H.escape(b) if html else b for b in brands]
        if len(names) == 1:
            bits.append(f'{names[0]}, which publishes none: its values are the ones {sname}, its main UK stockist, publishes')
        else:
            bits.append(f'{_and(names)}, which publish none: their values are the ones {sname}, their main UK stockist, publishes')
    return ', except ' + '; and '.join(bits)

def source_short():
    # Short bracketed form for method notes: " (Zoffany's are read from the swatch images on its
    # own site, as it publishes no values; Sanderson's come from its stockist Brewers, as Sanderson
    # publishes none)". '' if every brand publishes its own.
    if not SOURCE_NOTE and not SWATCH_SAMPLED:
        return ''
    bits = []
    sw = [H.escape(b) for b in _swatch_brands()]
    if len(sw) == 1:
        bits.append(f'{sw[0]}’s are read from the swatch images on its own site, as it publishes no values')
    elif sw:
        bits.append(f'{_and([n + "’s" for n in sw])} are read from the swatch images on their own sites, '
                    f'as {"neither brand publishes" if len(sw) == 2 else "none of them publishes"} values')
    for s, brands in _by_stockist().items():
        names = [H.escape(b) for b in brands]
        if len(names) == 1:
            bits.append(f'{names[0]}’s come from its stockist {s}, as {names[0]} publishes none')
        else:
            poss = _and([n + '’s' for n in names])
            bits.append(f'{poss} come from their stockist {s}, as neither brand publishes any' if len(names) == 2
                        else f'{poss} come from their stockist {s}, as none of them publishes any')
    return ' (' + '; '.join(bits) + ')'

def source_line(brand):
    # Note for the brand and colour pages of a brand that is swatch-sampled or sourced from a
    # stockist; '' otherwise.
    if brand in SWATCH_SAMPLED:
        b = H.escape(brand)
        return (f'<p class="srcnote">{b} doesn’t publish digital colour values, so the values here are read '
                f'from the swatch images on <a href="{SWATCH_SAMPLED[brand]}" rel="nofollow noopener" '
                f'target="_blank">its own site</a>. Names and links are {b}’s own.</p>')
    if brand not in SOURCE_NOTE:
        return ''
    stockist, url = SOURCE_NOTE[brand]
    b = H.escape(brand)
    return (f'<p class="srcnote">{b} doesn’t publish digital colour values, so the values here are the ones '
            f'<a href="{url}" rel="nofollow noopener" target="_blank">{stockist}</a>, its main UK stockist, '
            f'publishes. Names and links are {b}’s own.</p>')

# ---------- colour maths ----------
def hex2rgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))

def rgb2lab(r, g, b):
    def inv(v):
        v /= 255
        return ((v+0.055)/1.055)**2.4 if v > 0.04045 else v/12.92
    R, G, B = inv(r), inv(g), inv(b)
    X = (R*0.4124+G*0.3576+B*0.1805)/0.95047
    Y = (R*0.2126+G*0.7152+B*0.0722)
    Z = (R*0.0193+G*0.1192+B*0.9505)/1.08883
    f = lambda t: t**(1/3) if t > 0.008856 else 7.787*t+16/116
    return (116*f(Y)-16, 500*(f(X)-f(Y)), 200*(f(Y)-f(Z)))

def srgb_lin(v):
    v = v/255
    return ((v+0.055)/1.055)**2.4 if v > 0.04045 else v/12.92

def rgb2oklab(r, g, b):
    R, G, B = srgb_lin(r), srgb_lin(g), srgb_lin(b)
    l = 0.4122214708*R+0.5363325363*G+0.0514459929*B
    m = 0.2119034982*R+0.6806995451*G+0.1073969566*B
    s = 0.0883024619*R+0.2817188376*G+0.6299787005*B
    l, m, s = l**(1/3), m**(1/3), s**(1/3)
    return (0.2104542553*l+0.7936177850*m-0.0040720468*s,
            1.9779984951*l-2.4285922050*m+0.4505937099*s,
            0.0259040371*l+0.7827717662*m-0.8086757660*s)

LAB = np.array([rgb2lab(*hex2rgb(p['hex'])) for p in paints])
L = LAB[:, 0]; C = np.hypot(LAB[:, 1], LAB[:, 2])
HUE = np.degrees(np.arctan2(LAB[:, 2], LAB[:, 1])) % 360
OK = np.array([rgb2oklab(*hex2rgb(p['hex'])) for p in paints])
OL = OK[:, 0]; OC = np.hypot(OK[:, 1], OK[:, 2])
OH = np.degrees(np.arctan2(OK[:, 2], OK[:, 1])) % 360
BRANDS = np.array([p['brand'] for p in paints])

def hdv(a, b):
    d = np.abs(a-b) % 360
    return np.where(d > 180, 360-d, d)

def dmatch(i):
    """Hue-weighted perceptual distance (OKLab) from paint i to every paint.
    Mirrors the tool's okDistM exactly: hue drift penalised x2 (a hue-shifted
    paint reads as a different colour), lightness discounted /1.3 (a step
    lighter/darker still reads as the same colour); x190 keeps the dE76 scale
    so all existing wording thresholds carry over."""
    dL = (OL - OL[i]) / 1.3
    dC = OC - OC[i]
    dh = np.radians(hdv(OH, OH[i]))
    dH = 2*np.sqrt(np.maximum(OC*OC[i], 0))*np.sin(dh/2)
    return 190*np.sqrt(dL*dL + dC*dC + 4*dH*dH)

def lrv(l): return ((l+16)/116)**3*100 if l > 8 else l/903.3*100

# ---------- slugs ----------
def base_slug(n):
    s = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()\
        .lower().replace('&', 'and').replace("'", "")
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

slugs = {}; used = set()
for i, p in enumerate(paints):
    s = base_slug(p['brand'])+'-'+base_slug(p['name'])
    if s in used: s = s+'-'+p['hex'][1:].lower()
    used.add(s); slugs[i] = s

def _awin_wrap(mid, dest):
    from urllib.parse import quote
    return f"https://www.awin1.com/cread.php?awinmid={mid}&awinaffid={AWIN_AFFID}&ued={quote(dest, safe='')}"

def buy_link(p):
    if (p.get('code') or p['name']) in UNLISTED.get(p['brand'], ()):
        return None
    # Retailer route (Freshlick) takes priority for its brands, once live.
    if FRESHLICK_MID and p['brand'] in FRESHLICK_BRANDS:
        from urllib.parse import quote
        dest = "https://www.freshlick.com/catalogsearch/result/?q=" + quote(f"{p['brand']} {p['name']}")
        return _awin_wrap(FRESHLICK_MID, dest)
    # Retailer route (Decorating Centre Online) for the colours it stocks. Before the
    # brand-direct link below: DCO pays commission, the brand sites don't.
    if DCO_MID and p['brand'] in DCO_LINKS:
        _dco_key = p.get('code') or p['name']
        _dco_url = DCO_LINKS[p['brand']].get(_dco_key)
        if _dco_url and _dco_key not in DCO_NO_SAMPLE.get(p['brand'], ()):
            return _awin_wrap(DCO_MID, _dco_url)
    # Brand-direct Awin route (Crown Paints): wrap its own colour URL to earn commission.
    if CROWN_MID and p['brand'] == 'Crown':
        return _awin_wrap(CROWN_MID, p.get('url') or f"https://www.crownpaints.com/{base_slug(p['name'])}")
    # COAT: every colour has its own sample page, <name>-sample, offering a stick-on sample
    # (the default) or a tester pot. The data holds the paint page, <name>-flat-matt, where the
    # sample is a click away, so the tester button goes to the sample page instead. All 142
    # were matched against coatpaints.com/products.json on 12 Nov 2026. A COAT colour whose
    # link does not end -flat-matt is left alone: check its sample page by hand.
    if p['brand'] == 'COAT' and (p.get('url') or '').endswith('-flat-matt'):
        return p['url'][:-len('-flat-matt')] + '-sample'
    if p.get('url'): return p['url']
    _bl = BUY_LINKS.get(p['brand'], {}).get(p.get('code') or p['name'])
    if _bl: return _bl
    s = base_slug(p['name'])
    if p['brand'] == 'Farrow & Ball':
        return f"https://www.farrow-ball.com/paint/{s}"
    if p['brand'] == 'Little Greene':
        return f"https://www.littlegreene.com/{s}"
    if p['brand'] == 'Dulux':
        return f"https://www.dulux.co.uk/en/colour-details/{s}"
    if p['brand'] == 'Lick':
        fam = p['name'].split(' ')[0].lower()
        return f"https://www.lick.com/uk/products/paint/colour/{fam}"
    if p['brand'] == 'Crown':
        return f"https://www.crownpaints.com/{s}"
    if p['brand'] == 'COAT':
        return f"https://coatpaints.com/products/{s}-flat-matt"
    from urllib.parse import quote
    return "https://www.diy.com/search?term="+quote(f"{p['brand']} {p['name']} paint")

# Two checks from the 10 Nov 2026 link audit, which found seven tester buttons going to the
# wrong colour. All seven were bad data rows, and either check below would have stopped them.
# 1. Johnstone's has no codes of its own: its "code" is the colour name in capitals and the
#    tester link is looked up by it. Six rows had another colour's name as the code.
_key = lambda t: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower())
for _p in paints:
    if _p['brand'] == "Johnstone's":
        assert _key(_p['code']) == _key(_p['name']), \
            f"Johnstone's {_p['name']} has the code {_p['code']}: its tester link would go to another colour"
# 2. No two colours in a brand may share a destination. (Lakeland is the exception: one tester
#    page for every colour.) Dulux "Sapphire Splendor" was a duplicate of "Sapphire Splendour".
_dest = {}
for _p in paints:
    if _p['brand'] == 'Lakeland Paints': continue
    _u = buy_link(_p)
    if _u is None: continue
    _k = (_p['brand'], _u)
    assert _k not in _dest, f"{_p['brand']} {_dest[_k]} and {_p['name']} both link to {_u}"
    _dest[_k] = _p['name']

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23F7F5F0'/%3E"
           "%3Ccircle cx='16' cy='16' r='10' fill='none' stroke='%235E7E8B' stroke-width='4'/%3E"
           "%3Ccircle cx='16' cy='16' r='3.4' fill='%23211F1B'/%3E%3C/svg%3E\">")
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,600'
         '&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
         # Google's build of Fraunces only offers the looped ampersand. fraunces-amp.woff2 is a
         # 3 KB cut of the font holding just its plain ampersand (the ss01 alternate), still
         # variable so weight and optical size follow the main face. unicode-range means the
         # browser only fetches it when an & is on the page, and only the & uses it.
         '<style>@font-face{font-family:"Fraunces Amp";src:url(/fraunces-amp.woff2) format("woff2");'
         'font-weight:100 900;unicode-range:U+26;font-display:swap}'
         # Colour data (hex, LRV, lightness) in IBM Plex Mono so it reads as data, lines up,
         # and isn't one more line of the body face. Labels stay in Archivo.
         ':root{--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}'
         '.facts b,.hero-stats span:nth-child(-n+2),.a-hex,.hx,.uq span:not(.uq-near){font-family:var(--mono);font-weight:500;letter-spacing:0}'
         '.facts b{font-size:.95em}.hero-stats i{font-family:var(--sans)}</style>')
# Very wide screens (2800px and up, e.g. 4K at 100% scaling) get the whole page 10%
# bigger. Every page includes FONTS, so this one rule covers the lot; the same rule
# closes index.html's stylesheet, and pd-compare.js allows for the zoom when it tracks
# the pointer.
FONTS += '<style>@media(min-width:2800px){html{zoom:1.1}}</style>'
# The header gained a "Scheme planner" link on 13 Nov 2026. Below 900px there is no room for
# it and the "Open the colour tool" button, so the button goes: the logo already goes to the
# tool (Will's call). On a phone the planner link sits in the text row under the header (.mnav).
FONTS += ('<style>@media(max-width:900px){header nav a.nav-cta{display:none!important}}'
          # 561 to 700px (small tablets, phones on their side): four text links and the library
          # button only fit on one line without the button's four swatches.
          '@media(min-width:561px) and (max-width:700px){header .lib-swatches{display:none}header nav{gap:10px}}</style>')
HDR = '<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="head-nav" href="/research/">Research</a><a class="head-nav" href="/colour-scheme-planner/">Scheme planner</a><a class="lib-link" href="/colours/"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span>Colour library</a><a class="nav-cta" href="/"><span class="cta-wheel" aria-hidden="true"></span>Open the colour tool</a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/research/">Research</a><a href="/colour-scheme-planner/">Scheme planner</a></div>'
FOOT = ("<span class=\"foot-links\">"
        "<a href=\"/about/\">About</a> \u00b7 "
        "<a href=\"/how-it-works/\">How matching works</a> \u00b7 "
        "<a href=\"/research/\">Research</a> \u00b7 "
        "<a href=\"/match-paint-from-a-photo/\">Match from a photo</a> \u00b7 "
        "<a href=\"/paint-visualiser/\">Paint visualiser</a> \u00b7 "
        "<a href=\"/colour-scheme-planner/\">Scheme planner</a> \u00b7 "
        "<a href=\"/paint-calculator/\">Paint calculator</a> \u00b7 "
        "<a href=\"/contact/\">Contact</a> \u00b7 "
        "<a href=\"/privacy/\">Privacy</a> \u00b7 "
        "<a href=\"/colours/\">Colour library</a> \u00b7 "
        "<a href=\"/\">Colour tool</a>"
        "</span>"
        "<span class=\"foot-copy\">\u00a9 2026 PaintDial. All rights reserved.</span>"
        "No screen shows paint exactly, so get a tester before you buy. Colour values are each "
        "brand\u2019s published digital swatches" + source_exception(html=False) + "; LRV is estimated. Colour names are the property of their respective "
        "brands. PaintDial is free to use. If it "
        "saved you a tester pot, you can <a href=\"https://ko-fi.com/paintdial\" target=\"_blank\" rel=\"noopener\">buy Will a coffee</a>.")

# ---------- colour page CSS (current, with all layout fixes) ----------
CSS = """
.srcnote{font-size:12.5px;line-height:1.5;color:var(--muted);margin:10px 0 14px;max-width:62ch}.srcnote a{color:inherit}
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#665F54;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces Amp","Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.top-band{height:12px;background:var(--pc)}
.wrap{max-width:1160px;margin:0 auto;padding:0 32px 72px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--hairline)}
.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px;font-size:13px}
header nav a{font-family:var(--sans);font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:inline-flex;gap:3px}.lib-swatches i{width:13px;height:13px;border-radius:3px;display:inline-block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
.hero{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--hairline);border-radius:14px;overflow:hidden;background:var(--card);margin:28px 0}
@supports (background: color-mix(in srgb, red 10%, white)){.hero-body{background:color-mix(in srgb, var(--pc) 7%, #fff)}}
@media(max-width:640px){.hero{grid-template-columns:1fr}}
.hero-swatch{min-height:320px}
.hero-body{padding:26px 28px}
.eyebrow{font-size:10.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:34px;font-weight:600;letter-spacing:-.01em;line-height:1.1;margin:6px 0 2px}
/* The brand sits inside the colour page's h1, so the heading reads "Dulux Fallen Burr"
   to a search engine or screen reader, while looking exactly as it did when the brand
   was a separate label above the name. */
.hero-body h1{margin-top:0}
h1 .eyebrow{display:block;font-family:var(--sans);line-height:1.5;margin-bottom:8px}
.facts{display:flex;gap:6px 18px;margin:16px 0 20px;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;flex-wrap:wrap}
.hero-acts{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.hero-acts .btn{border:1px solid transparent}
.btn.btn-wall{background:#fff;color:var(--ink);border-color:var(--hairline);box-shadow:0 1px 2px rgba(33,31,27,.05)}.btn.btn-wall:hover{border-color:var(--muted)}
.facts b{color:var(--ink)}
.btn{display:inline-block;font-size:14px;font-weight:600;text-decoration:none;padding:11px 20px;border-radius:8px;background:var(--ink);color:var(--paper)}
h2{font-family:var(--serif);font-size:21px;font-weight:600;margin:34px 0 4px}
h2::after{content:'';display:block;width:34px;height:4px;border-radius:2px;background:var(--pc);margin-top:7px}
.sub{font-size:13px;color:var(--muted);margin-bottom:14px}.sub a{color:inherit;text-underline-offset:2px}.c-wn{white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}
.chip{border:1px solid var(--hairline);border-radius:14px;overflow:hidden;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06);text-decoration:none;color:var(--ink);transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column}
.chip:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(33,31,27,.1)}.chip{cursor:pointer}.chip:focus-within{outline:2px solid var(--pc);outline-offset:2px}.chip .c-name{text-decoration:none;color:inherit;outline:none}.chip .c-name::after{content:"";position:absolute;inset:0}
.c-swatch{height:74px;flex:none}
.c-body{padding:9px 11px 11px}
.c-name{display:block;font-family:var(--serif);font-size:14.5px;font-weight:600;line-height:1.2;text-wrap:pretty}
.c-brand{display:block;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:2px}
.pinfo{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:14px 0 4px}.pinfo div{background:var(--card,#fff);border:1px solid var(--hairline);border-radius:10px;padding:11px 14px}.pinfo dt{font-family:var(--sans);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.pinfo dd{font-size:14.5px;font-weight:600;margin:3px 0 0;line-height:1.3}
.c-de{display:block;font-size:11px;color:var(--muted);margin-top:5px;font-variant-numeric:tabular-nums}.pband{display:inline-block;background:#EEEAE2;border-radius:999px;padding:2px 8px;margin-right:6px;font-weight:600;letter-spacing:.04em;color:var(--ink)}.pband i{font-style:normal;opacity:.25}
.ladder{display:flex;border:1px solid var(--hairline);border-radius:14px;overflow-x:auto;background:var(--card)}
/* Matches and the lighter/darker scale share one block (.mx). Wider than a phone it is
   one grid: the two halves of the matches are display:contents, so all sixteen flow
   together, and the scale is ordered after them. On a phone the cards go two across
   and the scale sits after the first four, as on the homepage, instead of sixteen
   cards down where people missed it. */
.mx>.ladder-sec,.mx>.mx-alt{grid-column:1/-1;min-width:0}
.mx-alt .sub{margin-top:0!important}
.more-h{display:none}
/* Wider than a phone, the cross-brand cards stop at two full rows so Lighter & darker sits
   higher and no row is left with one or two cards in it. The rest are still in the page
   (links and all), a tap on "Show all" away. The counts below are 2 x the columns, less
   the four cards in the first .gpart: keep them in step with the column rules. */
.mx-all{font:inherit;font-weight:600;color:inherit;background:none;border:0;padding:0;margin-left:4px;text-decoration:underline;text-underline-offset:2px;cursor:pointer}
@media(max-width:640px){.mx-all{display:none}}
@media(min-width:641px) and (max-width:899px){.grid.mx{grid-template-columns:repeat(3,minmax(0,1fr))}.mx:not(.all)>.ladder-sec~.gpart>:nth-child(n+3){display:none}}
@media(min-width:900px) and (max-width:1159px){.grid.mx{grid-template-columns:repeat(4,minmax(0,1fr))}.mx:not(.all)>.ladder-sec~.gpart>:nth-child(n+5){display:none}}
@media(min-width:1160px) and (max-width:1399px){.grid.mx{grid-template-columns:repeat(5,minmax(0,1fr))}.mx:not(.all)>.ladder-sec~.gpart>:nth-child(n+7){display:none}}
@media(min-width:1400px) and (max-width:1899px){.mx:not(.all)>.ladder-sec~.gpart>:nth-child(n+9){display:none}}
@media(min-width:1900px){.mx:not(.all)>.ladder-sec~.gpart>:nth-child(n+15){display:none}}
@media(min-width:641px){.mx .gpart{display:contents}.mx>.mx-alt{order:1}.mx>.ladder-sec{order:2}.mx>.ladder-sec h2:first-child{margin-top:18px}}
@media(max-width:640px){.grid,.mx .gpart{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.grid.mx{display:block}.more-h{display:block}.mx-alt{margin-top:12px}}
.rung{flex:1 1 0;min-width:72px;text-decoration:none;color:var(--ink);display:flex;flex-direction:column}
.rung+.rung{border-left:1px solid var(--hairline)}
.rung .r-s{height:56px;flex:none}
.rung .r-b{padding:7px 8px 9px;min-height:58px;min-width:0}
.rung .r-n{font-family:var(--serif);font-size:11.5px;font-weight:600;line-height:1.2;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;height:28px}
.rung .r-br{font-size:9px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.cta{margin-top:40px;border:1px solid var(--hairline);border-radius:14px;background:var(--card);padding:24px 26px;text-align:center}
.cta p{font-size:14px;color:var(--muted);margin:6px 0 14px}.cta h2::after{margin:7px auto 0}
.afftext{font-size:11px;color:var(--muted);margin-top:12px}
.colour-summary{font-size:15px;color:var(--ink);max-width:72ch;margin:22px 0 2px;line-height:1.6}
.colour-summary a{color:var(--pc);text-decoration:none;font-weight:600}
.colour-summary a:hover{text-decoration:underline}
footer{margin-top:36px;padding-top:18px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
footer a{color:var(--muted)}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:11px;height:11px}
}

@media(max-width:640px){
.hero-swatch{min-height:200px}
.hero-body{padding:20px 20px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:4px 9px;border-radius:8px;box-shadow:none}header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}

/* ---- wide screens (colour pages and the 404) ----
   The column was capped at 1160px, so on a 27in 4K monitor at 100% the page sat in the
   middle third with small type. From 1500px it uses the homepage's column exactly (its
   --wide steps 1720 / 2000 / 2320 and 28px edge) and the homepage's header sizes, so the
   logo and the page edges don't move when you click through from the homepage. The
   eighteen matches (one per other brand) sit six across from 1400px, three full rows, and
   nine across from 1900px, two full rows; nine is too tight below that (150px cards at
   1536). Below 1400 the grid auto-fills. The four "Pairs well with" cards stay eight
   across. If the brand count changes, re-pick these so the rows still come out full.
   The type steps up with the column. html{zoom:1.1} from 2800px (in FONTS) scales on
   top of the last step. If the homepage widths change, change these too. */
@media(min-width:1400px){.grid.mx{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media(min-width:1500px){
.wrap{max-width:1720px;padding-left:28px;padding-right:28px}
.grid{grid-template-columns:repeat(8,minmax(0,1fr));gap:16px}.grid.mx{grid-template-columns:repeat(6,minmax(0,1fr))}
.c-swatch{height:96px}.c-body{padding:11px 13px 13px}
.c-name{font-size:15.5px}.c-brand{font-size:10.5px}.c-de{font-size:12px}
h1{font-size:40px}h2{font-size:23px;margin-top:40px}.sub{font-size:14px}.facts{font-size:14px}.eyebrow{font-size:11.5px}
.hero-swatch{min-height:360px}.btn{font-size:15px}.afftext{font-size:12px}
header{padding:22px 0 18px}.logo{font-size:30px}.logo .mark{width:27px;height:27px}
.rung .r-s{height:68px}.rung .r-n{font-size:12.5px;height:31px}.rung .r-br{font-size:9.5px}
.cta p{font-size:15px}footer{font-size:12.5px}.colour-summary{font-size:16px}
}
@media(min-width:1900px){
.wrap{max-width:2000px}
.grid{gap:18px}.grid.mx{grid-template-columns:repeat(9,minmax(0,1fr))}
.c-swatch{height:112px}.c-body{padding:12px 15px 15px}
.c-name{font-size:17px}.c-brand{font-size:11.5px}.c-de{font-size:13px}
h1{font-size:46px}h2{font-size:26px;margin-top:46px}.sub{font-size:15px;margin-bottom:16px}.facts{font-size:15.5px}.eyebrow{font-size:12.5px}
.hero-swatch{min-height:420px}.hero-body{padding:32px 36px}.btn{font-size:16px;padding:12px 22px}.afftext{font-size:12.5px}
.logo{font-size:34px}
.rung .r-s{height:80px}.rung .r-b{padding:9px 10px 11px}.rung .r-n{font-size:14px;height:34px}.rung .r-br{font-size:10.5px}
.cta p{font-size:16px}footer{font-size:13.5px}.colour-summary{font-size:17px}
.c-swatch .pd-cmp-btn{height:34px;font-size:13px;padding:0 13px 0 10px}.c-swatch .pd-heart,.hero-swatch .pd-heart,.hero-swatch .pd-solo i{width:34px;height:34px}
}
@media(min-width:2400px){
.wrap{max-width:2320px}
.grid{gap:20px}
.c-swatch{height:132px}.c-body{padding:14px 17px 17px}
.c-name{font-size:19px}.c-brand{font-size:12.5px}.c-de{font-size:14.5px}
h1{font-size:54px}h2{font-size:30px;margin-top:52px}.sub{font-size:16.5px;margin-bottom:18px}.facts{font-size:17px}.eyebrow{font-size:13.5px}
.hero-swatch{min-height:500px}.hero-body{padding:40px 44px}.btn{font-size:17px;padding:13px 24px}.afftext{font-size:13.5px}
.rung .r-s{height:96px}.rung .r-b{padding:10px 12px 12px}.rung .r-n{font-size:15.5px;height:38px}.rung .r-br{font-size:11.5px}
.cta p{font-size:17px}footer{font-size:14.5px}.colour-summary{font-size:18.5px}
.c-swatch .pd-cmp-btn{height:38px;font-size:14px;padding:0 15px 0 12px;top:10px;left:10px}.c-swatch .pd-heart,.hero-swatch .pd-heart{width:38px;height:38px;top:10px;right:10px}.hero-swatch .pd-solo i{width:38px;height:38px;top:10px;left:10px}
.hero-swatch{min-height:460px}
}
"""

def ladder_for(i):
    """A tonal ladder: the same colour stepped evenly from dark to light.

    Previously this binned the lightness range into 9 slices and picked the most
    hue-consistent paint WITHIN each slice, which meant a rung could sit anywhere in its
    bin. The steps came out badly uneven -- Sulking Room Pink's ladder had two rungs
    0.007 apart (visually one rung, one wasted slot) next to a 0.160 chasm: a 24x spread
    between smallest and largest step. Empty bins also silently dropped rungs.

    Now: 9 evenly spaced lightness TARGETS, and for each we take the paint that best trades
    off distance-from-target against hue/chroma consistency, with a hard minimum separation
    so two rungs can never collapse onto the same tone. The colour itself always claims its
    nearest step, so you can see where it sits on its own ladder.
    """
    STEPS = 9
    C0, H0 = OC[i], OH[i]
    neutral = C0 < 0.015
    hTol = min(30, max(11, 2.2/max(C0, 0.01)))
    if neutral:
        mask = OC < 0.02
    else:
        mask = (hdv(OH, H0) <= hTol) & (OC >= C0*0.35) & (OC <= min(C0*2.3, C0+0.045))
    mask = mask.copy()
    mask[i] = True                      # the colour always belongs on its own ladder
    idxs = np.where(mask)[0]
    if len(idxs) < 4: return []
    lo0, hi0 = float(OL[idxs].min()), float(OL[idxs].max())
    if hi0 - lo0 < 1e-6: return []

    # consistency cost: how far a candidate drifts in hue/chroma from the home colour
    cons = np.abs(OC-C0)*100 if neutral else hdv(OH, H0)*2 + np.abs(OC-C0)*200
    targets = [lo0 + s*(hi0-lo0)/(STEPS-1) for s in range(STEPS)]
    home_step = min(range(STEPS), key=lambda s: abs(targets[s]-OL[i]))
    chosen = {home_step: i}
    min_sep = (hi0-lo0)/(2*(STEPS-1))   # half a step: rungs can never visually collide

    for s in range(STEPS):
        if s in chosen: continue
        # distance from the target tone dominates; consistency breaks ties
        cost = np.where(mask, np.abs(OL-targets[s])*300 + cons, 1e9)
        for j in chosen.values():
            cost = np.where(np.abs(OL-OL[j]) < min_sep, 1e9, cost)
        j = int(np.argmin(cost))
        if cost[j] < 1e9: chosen[s] = j
    return sorted(chosen.values(), key=lambda j: OL[j])

def chip(j, home_lab=None, show_tier=False, home_i=None):
    q = paints[j]
    de = ''
    if home_lab is not None:
        d = float(dmatch(home_i)[j]) if home_i is not None else float(np.linalg.norm(LAB[j]-home_lab))
        if d < 2: word = 'near-identical'
        elif d < 5: word = 'very close'
        elif d < 10: word = 'close'
        else:
            word = 'related'
            if home_i is not None:
                _hd = abs(OH[j]-OH[home_i]) % 360
                _hd = min(_hd, 360-_hd)
                if IS_NEUTRAL[j] or IS_NEUTRAL[home_i]:
                    word = 'similar tone'
                else:
                    _minc = min(OC[j], OC[home_i])
                    _tol = 28 if _minc >= 0.12 else 22 if _minc >= 0.08 else 16
                    if _hd <= _tol:
                        word = 'same family'
        tierlab = band_html(q["brand"]) if show_tier else ''   # the pill's own margin separates it from the word
        # The number is the site's own match distance (dmatch), shown beside the word so the
        # word stays the headline. Explained on /how-it-works/#difference. Not called Delta E:
        # it is on that scale but weights hue and lightness its own way.
        num = f' \u00b7 <span class="c-num" title="Difference score: lower is closer">{d:.1f}</span>' if home_i is not None else ''
        # word and number stay together, so a narrow card wraps them as one piece
        de = f'<span class="c-de">{tierlab}<span class="c-wn">{word}{num}</span></span>'
    # Compare button only where there is a colour to compare against (the page's own
    # colour); the "pairs well with" chips are companions, not matches, so they get none.
    cmp = cmp_btn(paints[home_i], q, word) if home_i is not None else ''
    return (f'<div class="chip">'
            f'<div class="c-swatch" style="background:{q["hex"]}">{cmp}{heart(q["name"], q["brand"], q["hex"])}</div>'
            f'<div class="c-body"><a class="c-name" href="/colours/{slugs[j]}">{H.escape(q["name"])}</a>'
            f'<span class="c-brand">{H.escape(q["brand"])}</span>{de}</div></div>')

def a_an(w):
    """'a' or 'an' for a colour name, so 'Order an Etruria tester', not 'a Etruria'."""
    lw = w.lower()
    if lw[:1].isdigit():
        return 'an' if lw.startswith(('8', '11', '18')) else 'a'
    first = re.split(r'[\s\-]', w, 1)[0]
    # Initials are said letter by letter: an HMS, an LLB, an R and R, an XOXOXO.
    if (len(first) == 1 or (first.isupper() and first in ('HMS', 'LLB', 'XOXOXO'))) and first.isalpha() and first != 'A':
        return 'an' if first[0].upper() in 'AEFHILMNORSX' else 'a'
    # Vowel letter, consonant sound: a Unicorn, a Utopia, a Utah, a UFO, a Once, a Euro.
    if lw.startswith(('uni', 'use', 'usu', 'uti', 'uto', 'uta', 'ufo', 'eu', 'one', 'once')):
        return 'a'
    # Silent h: an Heirloom, an Honest, an Hour, an Honour.
    if lw.startswith(('heir', 'honest', 'hour', 'honour')):
        return 'an'
    return 'an' if lw[:1] in 'aeiou' else 'a'

def buy_cta(p):
    """The colour page's buy button: link, label and the line under it, worded from where
    buy_link() actually goes, so the button never promises more than the page offers."""
    url = buy_link(p)
    name = H.escape(p['name'])
    a = a_an(p['name'])
    brand = H.escape(p['brand'])
    if url is None:
        return None, None, f'{brand}’s website no longer has a page for this colour, so there’s no tester to link to.'
    brand_s = (brand if brand.endswith(('’s', "'s", '&#x27;s'))   # Johnstone's page
               else brand + '’' if brand.endswith('s')               # Mylands’ page
               else brand + '’s')
    if 'diy.com/departments/' in url:          # Valspar: the colour's tester pot at B&Q
        return url, f'Order {a} {name} tester →', 'Opens the tester pot on B&amp;Q’s site.'
    if 'diy.com' in url:                       # should not happen: the build warns about any
        return url, f'Find {name} at B&amp;Q →', 'Opens B&amp;Q’s search for it.'
    if 'valsparpaint.co.uk' in url:            # Valspar colours with no tester online
        return url, f'See {name} at Valspar →', 'Opens Valspar’s page for it, with where to buy.'
    if 'lick.com' in url and 'variant=' in url:
        # Lick's sample is a Peel & Stick one, not a pot (checked on lick.com, 12 Nov 2026).
        return url, f'Order {a} {name} sample →', 'Opens Lick’s page for it with the stick-on sample selected.'
    if 'coatpaints.com' in url and url.endswith('-sample'):
        return url, f'Order {a} {name} tester →', 'Opens COAT’s sample page for it: a stick-on sample or a tester pot.'
    if 'lakelandpaints.co.uk/testers/' in url:  # Lakeland has one tester page for every colour
        return url, f'Order {a} {name} tester →', f'Opens Lakeland’s tester page: choose {name} from its colour list.'
    if 'decoratingcentreonline' in url:
        # DCO sells some colours as a painted card, not a pot: Craig & Rose "colour patch",
        # Farrow & Ball Carte Blanche "paint sample swatch". Say so, the button must not
        # promise a tester pot the page doesn't have.
        if 'colour-patch' in url:
            return url, f'Order {a} {name} colour patch →', 'Opens Decorating Centre Online, which sells this colour as a painted colour patch, not a tester pot.'
        if 'sample-swatch' in url:
            return url, f'Order {a} {name} swatch →', 'Opens Decorating Centre Online, which sells this colour as a painted sample swatch, not a tester pot.'
        return url, f'Order {a} {name} tester →', 'Opens Decorating Centre Online, where you can order a tester or a full tin.'
    if 'crownpaints' in url:
        return url, f'Order {a} {name} tester →', 'Opens Crown Paints, where you can order a tester or a full tin.'
    if 'freshlick' in url or 'awin1.com' in url:
        return url, f'Order {a} {name} tester →', 'Opens Freshlick, where you can order a tester or a full tin.'
    return (url, f'Order {a} {name} tester →',
            f'Opens {brand_s} page, where you can order a tester or a full tin.')

def build_colour_page(i):
    p = paints[i]; lab = LAB[i]
    name = H.escape(p['name']); brand = H.escape(p['brand'])
    slug = slugs[i]
    d = dmatch(i)

    # cross-brand: closest from each OTHER brand, ranked by dE
    xmatch = []; no_match = []
    g = mdist(i)
    for b in BRAND_ORDER:
        if b == p['brand']: continue
        j = brand_match(i, b, d, g)
        if j is None:
            no_match.append(b)
        else:
            xmatch.append((j, d[j]))
    xmatch.sort(key=lambda t: t[1])
    assert len(xmatch) >= 3, f'{p["brand"]} {p["name"]}: fewer than 3 brands have a match'
    _num_note = (' The number is how far apart the two colours are: under 2 is near-identical. '
                 '<a href="/how-it-works/#difference">How it\u2019s worked out</a>.')
    mx_sub = 'One from each brand. The badge shows its price bracket.' + _num_note
    if no_match:
        mx_sub = (f'One from each brand that has something near it. The badge shows its price bracket. '
                  f'{_and([H.escape(b) for b in no_match])} {"has" if len(no_match) == 1 else "have"} '
                  f'nothing close enough to show.' + _num_note)
    # SEO: name the closest cross-brand match in title/meta (answers the dupe query in the SERP)
    _x0, _x0d = xmatch[0]
    seo_top = f"{H.escape(paints[_x0]['name'])} by {H.escape(paints[_x0]['brand'])}"
    seo_word = matchword(_x0d)
    seo_also = (f"{H.escape(paints[xmatch[1][0]]['name'])} by {H.escape(paints[xmatch[1][0]]['brand'])} "
                f"and {H.escape(paints[xmatch[2][0]]['name'])} by {H.escape(paints[xmatch[2][0]]['brand'])}")
    _depth, _fam = describe(i)
    buy_url, buy_label, buy_note = buy_cta(p)
    # Only tag a link rel="sponsored" when it's a real affiliate link that earns
    # commission (everything monetised routes through awin1.com: DCO, Crown, Freshlick).
    # Plain brand/retailer links (Fired Earth, B&Q, Lick, Lakeland, etc.) get nofollow,
    # matching the stockist links elsewhere, and must never claim to be sponsored.
    buy_rel = 'noopener sponsored' if (buy_url and 'awin1.com' in buy_url) else 'nofollow noopener'
    if buy_url and 'awin1.com' in buy_url:
        buy_note += ' I earn a small commission if you buy through this link, at no extra cost to you.'

    # "Open in the colour tool" opens the homepage tool on this colour (/#5B7E8F, read there)
    tool_url = '/#' + p['hex'][1:]
    _chips = [chip(j, home_lab=lab, show_tier=True, home_i=i) for j, _ in xmatch]
    hdr_tool = HDR.replace('<a class="nav-cta" href="/">',
                           '<a class="nav-cta" href="' + tool_url + '" title="Open ' + name + ' in the colour tool">', 1)
    assert hdr_tool != HDR, 'nav-cta link not found in HDR'
    rungs = ladder_for(i)
    rung_html = ''.join(
        f'<a class="rung" href="/colours/{slugs[j]}"><div class="r-s" style="background:{paints[j]["hex"]}"></div>'
        f'<div class="r-b"><span class="r-n">{H.escape(paints[j]["name"])}</span>'
        f'<span class="r-br">{H.escape(paints[j]["brand"])}</span></div></a>'
        for j in rungs)

    # pairs well with: 3 light neutrals (undertone-sympathetic) + 1 complementary accent
    H0, C0, L0 = HUE[i], C[i], L[i]
    nm = (C < 8) & (L > 82)
    nscore = np.where(C > 2, hdv(HUE, H0), 50.0)
    neutrals = [int(j) for j in np.argsort(np.where(nm, nscore, 1e9))[:3]]
    comp = (H0+180) % 360
    am = (C > 20) & (L > 35) & (L < 75)
    accents = [int(np.argmin(np.where(am, hdv(HUE, comp), 1e9)))]

    alt_link = (f'<p class="sub" style="margin-top:12px"><a href="/alternatives/{slug}" style="color:inherit;font-weight:600">'
                f'See all {name} alternatives, ranked \u2192</a>'
                f' &nbsp;\u00b7&nbsp; <a href="/dupes/{base_slug(p["brand"])}" style="color:inherit;font-weight:600">'
                f'All {brand} dupes, ranked \u2192</a></p>') if TIER[p['brand']] == 3 else ''
    img_url = f"{DOMAIN}/share/{slug}.jpg"
    page = f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand} {name} \u2014 colour match &amp; alternatives | PaintDial</title>
<meta name="description" content="{brand} {name} ({p['hex']}, LRV \u2248 {lrv(L0):.0f}). See its closest matches across {BRANDS_WORD} brands sold in the UK, lighter &amp; darker shades, and where to buy a tester.">
<link rel="canonical" href="{DOMAIN}/colours/{slug}">
{_ldjson(
   _color_seo(p['name'], p['brand'], p['hex'], slug,
     f"The closest match to {p['name']} by {p['brand']} from another brand is {paints[_x0]['name']} by {paints[_x0]['brand']}."),
   _breadcrumb([("Home","/"),("Colours","/colours/"),(p['brand'],f"/colours/{base_slug(p['brand'])}"),(p['name'],f"/colours/{slug}")]),
   _itemlist([(f"{paints[j]['name']} by {paints[j]['brand']}", f"/colours/{slugs[j]}") for j,_ in xmatch])
)}
<meta property="og:title" content="{name} by {brand} \u2014 closest match: {seo_top}">
<meta property="og:image" content="{img_url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img_url}">
{FAVICON}
{FONTS}<style>{CSS}.hero-swatch{{background:{p['hex']}}}{SHORTLIST_CSS}{COMPARE_BTN_CSS}{KOFI_STRIP_CSS}</style></head><body style="--pc:{p['hex']}"><div class="top-band"></div><div class="wrap">
{hdr_tool}
<div class="hero"><div class="hero-swatch">{solo_btn(p)}{heart(p['name'], p['brand'], p['hex'])}</div><div class="hero-body">
<h1><span class="eyebrow">{brand}</span> {name}</h1>
<div class="facts"><span>Hex <b>{p['hex']}</b></span><span>RGB <b>{int(p['hex'][1:3],16)}, {int(p['hex'][3:5],16)}, {int(p['hex'][5:7],16)}</b></span><span>LRV <b>\u2248\u2009{lrv(L0):.0f}</b></span><span>Lightness <b>{L0:.0f}/100</b></span></div>{source_line(p['brand'])}
<div class="hero-acts">{f'<a class="btn" href="{buy_url}" target="_blank" rel="{buy_rel}">{buy_label}</a>' if buy_url else ''}<a class="btn btn-wall" href="{VIS_PATH}?c={slug}">See it on your wall</a><a class="btn btn-wall" href="{SCHEME_PATH}?add={slug}">Plan a room with it</a></div>
{f'<p class="afftext">{buy_note}</p>' if buy_note else ''}
<p class="afftext">{price_line(p['brand'])}</p>
</div></div>
<p class="colour-summary">{name} is a {_depth} {_fam} from {brand}. Its closest match from another brand is <a href="/colours/{slugs[_x0]}">{seo_top}</a> ({seo_word}).</p>
<h2>Closest matches from other brands</h2>
<p class="sub">{mx_sub} <button class="mx-all" type="button" data-n="{len(_chips)}" hidden>Show all {len(_chips)}</button></p>
<div class="grid mx"><div class="gpart">{''.join(_chips[:4])}</div>
<section class="ladder-sec"><h2>Lighter &amp; darker</h2>
<p class="sub">This colour, stepped evenly from dark to light.</p>
<div class="ladder">{rung_html}</div>
<h2 class="more-h">More matches from other brands</h2></section>
<div class="gpart">{''.join(_chips[4:])}</div>{('<div class="mx-alt">' + alt_link + '</div>') if alt_link else ''}</div>
<h2>Pairs well with</h2>
<p class="sub">Neutrals for woodwork and ceilings, and one colour that contrasts.</p>
<div class="grid">{''.join(chip(j) for j in neutrals+accents)}</div>
{paint_block(p['brand'])}
<div class="cta"><h2 style="margin-top:0">Not quite right?</h2>
<p>Use the colour tool to find a lighter, darker, warmer or cooler version of this colour across all {N:,} paints.</p>
<a class="btn" href="{tool_url}">Open {name} in the colour tool \u2192</a></div>
{kofi_strip()}
<footer>{FOOT}</footer>
</div><div class="top-band"></div><script>{SHORTLIST_JS}</script>{COMPARE_SCRIPT}<script>(function(){{var g=document.querySelector('.grid.mx'),b=document.querySelector('.mx-all');if(!g||!b)return;function chk(){{var cut=[].some.call(g.querySelectorAll('.gpart>*'),function(e){{return getComputedStyle(e).display==='none'}});b.hidden=!cut&&!g.classList.contains('all')}}b.addEventListener('click',function(){{var a=g.classList.toggle('all');b.textContent=a?'Show fewer':'Show all '+b.dataset.n}});chk();addEventListener('resize',chk)}})();</script></body></html>"""
    return page

# ---------- brand library pages (redesigned: family-grouped tiles, fan banner) ----------
def hx2hsl(hx):
    hx = hx.lstrip('#')
    r, g, b = [int(hx[i:i+2], 16)/255 for i in (0, 2, 4)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h*360, s, l

# ---- Human-facing colour naming: ONE source of truth (family + describe both use this) ----
# The band edges below are OKLab hue angles. The previous edges (25/70/110/175/230/285/330)
# were HSL-wheel angles applied to OKLab hue, which is a different space -- they landed almost
# exactly ON the OKLab hue centres of the primaries instead of BETWEEN them, so every colour
# fell one bucket clockwise: pure red #FF0000 classified as "Oranges", pure orange as "Yellows",
# and in describe() pure blue #0000FF came out as "pink". Measured OKLab hue of the sRGB
# primaries/secondaries: red 29.2, orange 70.7, yellow 109.8, green 142.5, cyan 194.8,
# blue 264.1, magenta 328.4.
#
# Edges are fitted, not guessed: each edge is constrained to lie between the two primaries it
# separates (so the primaries can never misclassify), and within those bounds the edges are
# chosen to maximise BALANCED agreement with the manufacturers' own colour names across the
# 481 chromatic paints whose names state a single colour word ("Sap Green", "Stiffkey Blue").
# Balanced accuracy 0.735 vs 0.593 for naive midpoints; 5-fold CV confirms it generalises.
# Verified against 14 anchors (pure primaries, pink, brown, white, grey, black) that must
# always hold. Excluded from calibration: historical pigment names where the word does not
# describe the colour (Dutch Pink is a yellow lake, not a pink).
HUE_EDGES = [37.7, 74.2, 110.3, 165.0, 224.3, 268.6, 328.9]
HUE_NAMES = ['Reds', 'Oranges', 'Yellows', 'Greens', 'Teals', 'Blues', 'Purples']

def _ok_lch(hx):
    import math as _m
    L, A, B = rgb2oklab(*hex2rgb(hx))
    return L, _m.hypot(A, B), _m.degrees(_m.atan2(B, A)) % 360

def _hue_band(H):
    for edge, name in zip(HUE_EDGES, HUE_NAMES):
        if H < edge: return name
    return 'Reds'          # wraps past magenta back into red

def family(hx):
    L, C, H = _ok_lch(hx)
    # ---- Neutral gate ----
    # This is HUE-AWARE, and that asymmetry is real rather than a fudge: a pale WARM colour
    # reads as an off-white or cream (Tallow C=0.031 is a cream), while a pale COOL colour of
    # the same chroma reads as coloured (Little Greene's Sky Blue C=0.043 is plainly blue).
    # The previous gate used flat chroma cuts by lightness and swept pale blues, pinks and
    # greens into "Whites & neutrals" -- it classed Sky Blue as neutral, which is why the
    # research page's "about half is neutral" figure was overstated by ~19 points.
    # Chroma utilisation (C as a fraction of the sRGB maximum at that L and hue) does NOT
    # separate them either -- Tallow uses 52% of its available chroma, Confetti only 43%.
    # Fitted against the brands' own naming (237 neutral-named vs 693 colour-named paints),
    # with hard anchors in both directions: white/grey/black/Tallow/Lead Colour must be
    # neutral; the primaries/Sky Blue/Pale Wedgwood/Confetti/Marigold must not.
    # Balanced accuracy 0.885. The warm window starts at 50 (not 60) because Little Greene's
    # pale pink-beiges -- China Clay, Dorchester Pink, Light Peachblossom, Mochi -- sit at
    # H 50-59 and were landing in "Oranges" next to a vivid Marigold (C 0.166 vs C 0.028,
    # a 6x chroma spread inside one group). They read as greiges, not oranges.
    warm = 50.0 <= H < 105.0
    if warm:
        ncut = 0.070 if L > 0.78 else 0.040 if L > 0.45 else 0.020
    else:
        ncut = 0.020
    if C < ncut:
        if L > 0.80: return "Whites & neutrals"
        if L < 0.30: return "Blacks"
        return "Greys"
    # Near-black: dark AND barely chromatic reads as black regardless of hue. Purple Brown
    # (#271410, L=0.22 C=0.033) was "Reds" -- it has just enough colour to clear the neutral
    # gate above, but at that darkness the hue is invisible; it looks black. The C<0.05 floor
    # is deliberately tight so genuinely deep COLOURS keep their family: Thai Sapphire
    # (L=0.17 C=0.074), Deep Space Blue (C=0.075), Baked Cherry (C=0.112), Deep Aubergine
    # (C=0.073) all stay put -- brands named them for the colour and the eye still reads it.
    if L < 0.30 and C < 0.05:
        return "Blacks"
    # Pink is LIGHT red/magenta -- a lightness carve, not a hue slice. Lightness separates it:
    # true pinks sit above L 0.625 (Rangwali 0.64, Porphyry Pink 0.63) while Crimson Red (0.62),
    # Charlotte's Locks (0.62) and Book Room Red (0.58) fall below.
    # The chroma ceiling is HUE-DEPENDENT. On the magenta side a pink can be ferociously
    # chromatic (hot pink C 0.197), but on the red-orange side (H 20-37.7) high chroma means
    # coral/salmon, not pink -- a flat 0.22 ceiling wrongly made Orange Aurora (C 0.165) and
    # Bisque (C 0.135) "pinks". Real pinks there are muted: Sulking Room 0.036, Blooth 0.077.
    if (H >= HUE_EDGES[6] or H < HUE_EDGES[0]) and L > 0.625:
        pink_cmax = 0.10 if 20 <= H < HUE_EDGES[0] else 0.22
        if C < pink_cmax:
            return "Pinks"
    band = _hue_band(H)
    # Yellow is a LIGHT colour -- there is no such thing as a dark yellow. Darken it and it
    # becomes olive (green side) or brown (orange side). Without this the Yellows band ran
    # from L 0.29 to L 0.93, filing Invisible Green (L 0.29) and Olive Colour (L 0.37)
    # alongside a lemon like Trumpet (L 0.93).
    if band == 'Yellows' and L < 0.55:
        return 'Greens' if H >= 92 else 'Browns'
    # Browns: darker, low-mid chroma ORANGES only. There used to be a matching carve for
    # dark reds, but it did more harm than good -- it swallowed Brinjal and Pelt (both
    # aubergines), Preference Red, Eating Room Red, Picture Gallery Red and Singed Red,
    # to rescue only Deep Reddish Brown. Every genuine brown (Fox Red, Marmelo, Wainscot,
    # Tack Room Door, Broccoli Brown) arrives through the Oranges band anyway. Dropping it
    # raised balanced agreement with brand names from 0.735 to 0.754.
    if band == 'Oranges' and L < 0.63 and C < 0.13: return "Browns"
    return band

FAM_ORDER = ["Reds", "Pinks", "Oranges", "Browns", "Yellows", "Greens",
             "Teals", "Blues", "Purples", "Whites & neutrals", "Greys", "Blacks"]

# Facets for the library filter. Modelled on how Farrow & Ball's own site browses: a colour
# is not forced into ONE bucket. It carries its hue family AND, if it's muted enough, a
# "Neutral" tag -- exactly as F&B lists Broccoli Brown under both Brown and Neutral. This
# ends the "but that's not grey!" problem: a borderline colour appears under every facet a
# person would reasonably look for it, and is "wrong" in none. Plus a Light/Mid/Dark tone
# axis (F&B's "Tones" filter), which is the lightness dimension a single hue label can't carry.
HUE_FACETS = ["Reds", "Pinks", "Oranges", "Browns", "Yellows", "Greens", "Teals", "Blues", "Purples"]
_NEUTRAL_FAMS = {"Whites & neutrals", "Greys", "Blacks"}

# ---------- match gate: a colour is never matched to a grey, black or white ----------
# dmatch() alone lets a neutral win when a brand has nothing near a colour: a neutral has no
# hue, so it pays no hue penalty, while a real relative pays for being lighter. Little
# Greene's Dark Brunswick Green (#082F14) was being "matched" to Dulux Black, Smelt Black and
# twelve other blacks (reported by a reader, Nov 2026). So for a source that family() files
# under a colour, a neutral candidate is dropped when BOTH hold:
#   - it is not a close match anyway (d >= 10, past the site's "close" wording), and
#   - it has lost more than half the source's chroma.
# Close matches are never touched, so a muted colour keeps its slightly greyer twins.
# Mirrored in index.html (matchOK) for the homepage tool. The research pages use dmatch()
# directly and are deliberately left alone: their figures are distances, not offers.
IS_NEUTRAL = np.array([family(q['hex']) in _NEUTRAL_FAMS for q in paints])
GATE_D, GATE_CFRAC = 10.0, 0.5
# A brand whose best remaining colour is this far off AND in a different hue gets no card.
DROP_D, DROP_HUE = 20.0, 45.0

def mdist(i):
    """dmatch(i) with the paints that must not be offered as a match for i pushed out of
    reach (1e9). Use this wherever a match is SHOWN; dmatch() for raw distances."""
    d = dmatch(i)
    if IS_NEUTRAL[i]:
        return d
    return np.where(IS_NEUTRAL & (d >= GATE_D) & (OC < GATE_CFRAC*OC[i]), 1e9, d)

def brand_match(i, b, d=None, g=None):
    """The one colour from brand b to show against paint i, or None when the brand has
    nothing fit to show. Only a brand whose nearest colour was a gated neutral can lose its
    card, so pages the gate does not touch are unchanged."""
    d = dmatch(i) if d is None else d
    g = mdist(i) if g is None else g
    mask = BRANDS == b
    j0 = int(np.argmin(np.where(mask, d, 1e9)))
    j = int(np.argmin(np.where(mask, g, 1e9)))
    if g[j] >= 1e9:
        return None
    if j != j0 and g[j] >= DROP_D and float(hdv(OH[j], OH[i])) > DROP_HUE:
        return None
    return j

def colour_facets(hx):
    """Return (tone, [tags]). Tags are multi-membership: a hue family plus optional
    Neutral/White/Grey/Black. Tone is one of Light/Mid/Dark."""
    L, C, H = _ok_lch(hx)
    fam = family(hx)
    # Tone follows the LRV estimate shown on every colour page, banded the way decorators
    # talk about depth: Dark below LRV 25, Light above 55, Mid between. (The old OKLab cuts
    # of 0.35/0.70 were LRV ~4/~34: Hague Blue came out "Mid" and only 52 paints were "Dark".)
    lrv_est = lrv(rgb2lab(*hex2rgb(hx))[0])
    tone = "Light" if lrv_est > 55 else "Dark" if lrv_est < 25 else "Mid"
    tags = []
    if fam not in _NEUTRAL_FAMS:
        tags.append(fam)
    # "Neutral" is generous and lightness-scaled: the eye forgives more chroma the lighter
    # the colour, so a pale tint still reads as a neutral you could put anywhere.
    ncut = 0.065 if L > 0.70 else 0.05 if L > 0.45 else 0.045
    if C < ncut or fam in _NEUTRAL_FAMS:
        tags.append("Neutral")
    if fam == "Whites & neutrals": tags.append("White")
    if fam == "Greys": tags.append("Grey")
    if fam == "Blacks": tags.append("Black")
    return tone, tags

NAV_CSS = """
/* The same header as the homepage and colour pages: About, How it works, Research,
   Colour library, then the colour tool button. */
header nav{gap:16px}
.logo .mark{flex:none}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s;text-decoration:none}
.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
@media(max-width:640px){header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}}
@media(max-width:560px){header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%;box-shadow:none}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}
"""

WIDE_SHELL_CSS = """
/* Same outer column and header as the homepage and colour pages (see the 1500/1900/2400
   steps in CSS), so the logo, nav and page edges don't move as you click around the site.
   Appended to every page type's stylesheet; if the colour-page widths change, change these. */
.wrap{max-width:1160px}
@media(min-width:1500px){
.wrap{max-width:1720px;padding-left:28px;padding-right:28px}
header{padding-top:22px;padding-bottom:18px}
header a.logo{font-size:30px}.logo-dial{width:27px;height:27px}.logo .mark{width:27px;height:27px}
header nav a,.head-nav{font-size:14px}
h1{font-size:40px}h2{font-size:23px}
footer{font-size:12.5px}
}
@media(min-width:1900px){
.wrap{max-width:2000px}
header a.logo{font-size:34px}.logo-dial{width:30px;height:30px}.logo .mark{width:30px;height:30px}
header nav a,.head-nav{font-size:15px}
h1{font-size:46px}h2{font-size:26px}
footer{font-size:13.5px}
}
@media(min-width:2400px){
.wrap{max-width:2320px}
h1{font-size:54px}h2{font-size:30px}
footer{font-size:14.5px}
}
"""

PAGES_WIDE_CSS = """
/* Text pages on wide screens. Same outer edges as the homepage and colour pages; the width
   is filled with columns rather than one long strip of text:
   - "grid" pages (About, How it works, Contact, photo page): each section is a block, two
     across from 1100px and three from 1500px. Sections holding something wide (step cards,
     a long FAQ, a form) span the full row.
   - "split" pages (the two research studies): each finding is a row, text on the left third,
     its swatches or chart on the right two-thirds.
   Below 1100px everything stacks in one readable column, as before. */
.lead>p{max-width:68ch}
.lead h1{max-width:36ch}
.lead .pm-hero{max-width:1400px}
@media(min-width:1100px){
.lead{padding-top:10px}
.lead>p{font-size:16px}
.secs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:56px;row-gap:12px;margin-top:22px;align-items:start}
.sec{border-top:1px solid var(--hairline);padding-top:4px;min-width:0}
.sec>h2,.sec-text>h2{margin-top:20px}
.sec p,.sec ul{max-width:none}
.sec-wide{grid-column:1/-1}
.sec .kofi{max-width:none;margin:22px 0 10px}
.sec .faq{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:56px}
.sec .faq details:last-child{border-bottom:none}
.splits{margin-top:22px}
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);column-gap:56px;border-top:1px solid var(--hairline);padding:4px 0 26px}
.split .sec-fig{padding-top:24px;min-width:0}
.split .sec-fig>.pair:last-child,.split .sec-fig>.bars{margin-bottom:0}
.split .sec-text p,.split .sec-text ul{max-width:none}
.split .bignum{margin-top:0;font-size:44px}.split .bignum small{font-size:15px;margin-top:6px}
.rsch-cards{grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:22px}
.lead .rsch-cards{margin-top:30px}
a.rsch-card{padding:28px 30px}
a.rsch-card b{font-size:24px;line-height:1.25}
a.rsch-card span{font-size:15px}
.split .sec-note{padding-top:0}
.split .sec-note>h2{margin-top:20px}
}
@media(min-width:1500px){
.lead{padding-top:40px}
.lead>p{font-size:17px}
.secs{grid-template-columns:repeat(3,minmax(0,1fr));column-gap:64px;margin-top:30px}
.sec .faq{grid-template-columns:repeat(3,minmax(0,1fr));column-gap:64px}
.split{column-gap:64px}
p,li{font-size:16px}
aa.rsch-card{padding:34px 38px}.split .bignum{font-size:56px}.split .bignum small{font-size:16px}a.rsch-card b{font-size:28px}a.rsch-card span{font-size:16px}
}
@media(min-width:1900px){
.lead{padding-top:72px}
.lead>p{font-size:19px}
.secs{column-gap:76px;margin-top:40px}
.sec .faq{column-gap:76px}
.split{column-gap:76px}
p,li{font-size:17px}
.rsch-cards{gap:28px}.lead .rsch-cards{margin-top:44px}
.split .bignum{font-size:64px}.split .bignum small{font-size:17px}
a.rsch-card{padding:42px 46px}a.rsch-card b{font-size:33px}a.rsch-card span{font-size:17px}
}
@media(min-width:2400px){
.lead{padding-top:96px}
.lead>p{font-size:20px}
p,li{font-size:18px}
a.rsch-card b{font-size:38px}a.rsch-card span{font-size:18px}
}
"""


ALT_WIDE_CSS = """
.intro a:not(.pn){color:inherit}
@media(min-width:1500px){
.alts{grid-template-columns:repeat(3,minmax(0,1fr))}
.intro{font-size:16px;max-width:75ch}.verdict p{max-width:110ch}
}
@media(min-width:1900px){.alts{grid-template-columns:repeat(4,minmax(0,1fr))}.intro{font-size:17px}}
"""

LIB_CSS = """
.srcnote{font-size:13px;line-height:1.5;color:var(--muted);margin:10px 0 0;max-width:70ch}.srcnote a{color:inherit}
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#665F54;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces Amp","Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.wrap{max-width:1320px;margin:0 auto;padding:0 32px 80px}
header{padding:16px 0;border-bottom:1px solid var(--hairline);display:flex;justify-content:space-between;align-items:center}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
header .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:inline-flex;gap:3px}.lib-swatches i{width:13px;height:13px;border-radius:3px;display:inline-block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
.top{margin:34px 0 6px}
.eyebrow{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:40px;font-weight:600;letter-spacing:-.015em;line-height:1.05;margin:8px 0 0}
.lede{font-size:14.5px;color:var(--muted);max-width:52ch;margin-top:10px}
.fan{display:flex;height:64px;border-radius:14px;overflow:hidden;margin:22px 0 6px;box-shadow:0 1px 2px rgba(33,31,27,.08),0 10px 30px rgba(33,31,27,.09)}
.fan span{flex:1 1 0}
.jumpbar{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 8px}
.jump{display:inline-flex;align-items:center;gap:7px;font-family:var(--sans);font-size:12.5px;font-weight:600;
  color:var(--ink);text-decoration:none;padding:6px 11px 6px 8px;border:1px solid var(--hairline);border-radius:999px;background:var(--card);transition:border-color .12s}
.jump:hover{border-color:var(--ink)}
.jump i{width:13px;height:13px;border-radius:50%;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)}
.fam{margin:40px 0 0;scroll-margin-top:16px}
.fam-head{display:flex;align-items:baseline;gap:10px;margin:0 0 15px;padding-bottom:9px;border-bottom:1px solid var(--hairline)}
.fam-head h2{font-family:var(--serif);font-size:20px;font-weight:600;letter-spacing:-.01em}
.fam-head .n{font-family:var(--sans);font-size:12px;font-weight:500;color:var(--muted)}
.tier{margin:0 0 26px}
.filters{margin:8px 0 22px;border-top:1px solid var(--hairline);padding-top:18px}
.frow{display:flex;align-items:flex-start;gap:12px;margin-bottom:11px}
.frow .flab{flex:none;width:58px;font-size:10.5px;font-weight:700;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);padding-top:7px}
.fchips{display:flex;flex-wrap:wrap;gap:7px}
.fchip{font-family:var(--sans);font-size:12.5px;padding:6px 12px;border:1px solid var(--hairline);border-radius:999px;background:#fff;color:var(--ink);cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:background .12s,border-color .12s,color .12s}
.fchip:hover{border-color:var(--muted)}
.fchip.on{background:var(--pc);color:#fff;border-color:var(--pc)}
.fchip i{font-style:normal;font-size:10.5px;opacity:.6;font-variant-numeric:tabular-nums}
.fchip.on i{opacity:.85}
.fmeta{display:flex;align-items:center;gap:14px;margin-top:4px}
.fmeta #fcount{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.fclear{font-family:var(--sans);font-size:12px;color:var(--pc);background:none;border:none;cursor:pointer;font-weight:600;padding:0}
.fclear:hover{text-decoration:underline}
.sw .tags{display:block;font-size:9px;color:var(--muted);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(max-width:560px){.frow .flab{width:44px;font-size:9.5px}.fchip{font-size:12px;padding:5px 10px}}
.tier:last-child{margin-bottom:0}
.tier h3{font-family:var(--sans);font-size:10.5px;font-weight:700;letter-spacing:.13em;
  text-transform:uppercase;color:var(--muted);margin:0 0 11px;display:flex;align-items:center;gap:8px}
.tier h3::after{content:"";flex:1;height:1px;background:var(--hairline)}
.tier h3 i{font-style:normal;font-size:10px;font-weight:500;letter-spacing:.04em;order:1}
.swatches{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:13px}
.sw{display:block;text-decoration:none;color:inherit;border:1px solid var(--hairline);border-radius:14px;overflow:hidden;
  background:var(--card);transition:transform .13s ease,box-shadow .13s ease}
.sw:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(33,31,27,.13)}
.sw:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.sw .block{display:block;height:108px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.045)}
.sw .lab{display:block;padding:10px 12px 12px}
.sw .nm{display:block;font-family:var(--serif);font-size:14px;font-weight:600;line-height:1.25;text-wrap:pretty;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sw .br{display:block;font-family:var(--sans);font-size:9.5px;font-weight:600;letter-spacing:.06em;
  color:var(--muted);text-transform:uppercase;margin-top:3px}
.lib-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:20px;margin-top:30px}
.lib{display:block;border:1px solid var(--hairline);border-radius:14px;overflow:hidden;background:var(--card);
  text-decoration:none;color:inherit;transition:transform .13s ease,box-shadow .13s ease}
.lib:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(33,31,27,.13)}
.lib .l-fan{display:flex;height:150px}
.lib .l-fan span{flex:1 1 0}
.lib .l-body{display:flex;justify-content:space-between;align-items:baseline;padding:16px 20px 18px}
.lib .l-nm{font-family:var(--serif);font-size:21px;font-weight:600}
.lib .l-n{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--hairline);font-size:12px;color:var(--muted);line-height:1.6}.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:640px){
  h1{font-size:30px} .wrap{padding:0 16px 60px}
  .swatches{grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:10px}
  .sw .block{height:88px} .fan{height:52px}
  .lib-grid{grid-template-columns:1fr 1fr;gap:10px}.lib .l-fan{height:44px}.lib .l-nm{font-size:14px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:11px;height:11px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:4px 9px;border-radius:8px;box-shadow:none}header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}
"""
LIB_CSS += WIDE_SHELL_CSS


LIB_HDR = '<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="head-nav" href="/research/">Research</a><a class="head-nav" href="/colour-scheme-planner/">Scheme planner</a><a class="nav-cta" href="/"><span class="cta-wheel" aria-hidden="true"></span>Open the colour tool</a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/research/">Research</a><a href="/colour-scheme-planner/">Scheme planner</a></div>'

def anchor(fam): return 'f-'+re.sub(r'[^a-z0-9]+', '-', fam.lower().replace('&', 'and')).strip('-')

def build_brand_page(b):
    idxs = [i for i in range(N) if paints[i]['brand'] == b]
    dupes_link = (f'<p class="lede" style="margin-top:6px"><a href="/dupes/{base_slug(b)}" style="color:var(--pc);font-weight:600">See every {H.escape(b)} colour\u2019s best-value match, ranked \u2192</a></p>'
                  if TIER.get(b) == 3 else '')
    allc = sorted(idxs, key=lambda i: (hx2hsl(paints[i]['hex'])[0], -hx2hsl(paints[i]['hex'])[2]))
    step = max(1, len(allc)//64)
    fan = ''.join(f'<span style="background:{paints[i]["hex"]}"></span>' for i in allc[::step][:64])

    # Order colours for display: neutrals-only drift to the end, everything else sweeps the
    # hue wheel, lightest-first within a hue. Tags drive the filtering, order drives the flow.
    def sort_key(i):
        tone, tags = colour_facets(paints[i]['hex'])
        hue_tags = [t for t in tags if t in HUE_FACETS]
        pure_neutral = not hue_tags
        return (pure_neutral, HUE[i] if not pure_neutral else 0, -L[i])
    ordered = sorted(idxs, key=sort_key)

    # tag counts for the filter chips
    hue_counts = {h: 0 for h in HUE_FACETS}
    type_counts = {'Neutral': 0, 'White': 0, 'Grey': 0, 'Black': 0}
    tone_counts = {'Light': 0, 'Mid': 0, 'Dark': 0}
    for i in idxs:
        tone, tags = colour_facets(paints[i]['hex'])
        tone_counts[tone] += 1
        for t in tags:
            if t in hue_counts: hue_counts[t] += 1
            if t in type_counts: type_counts[t] += 1

    def chip(kind, key, count):
        if not count: return ''
        return (f'<button class="fchip" data-{kind}="{H.escape(key)}">{H.escape(key)}'
                f'<i>{count}</i></button>')
    hue_chips = ''.join(chip('hue', h, hue_counts[h]) for h in HUE_FACETS)
    type_chips = ''.join(chip('type', t, type_counts[t]) for t in ['Neutral', 'White', 'Grey', 'Black'])
    tone_chips = ''.join(chip('tone', t, tone_counts[t]) for t in ['Light', 'Mid', 'Dark'])

    tiles = ''.join(
        (lambda tone, tags: (
            f'<a class="sw" href="/colours/{slugs[i]}" '
            f'data-hue="{H.escape("|".join(t for t in tags if t in HUE_FACETS))}" '
            f'data-type="{H.escape("|".join(t for t in tags if t in ("Neutral","White","Grey","Black")))}" '
            f'data-tone="{tone}">'
            f'<span class="block" style="background:{paints[i]["hex"]}"></span>'
            f'<span class="lab"><span class="nm">{H.escape(paints[i]["name"])}</span>'
            f'<span class="tags">{H.escape(" \u00b7 ".join(tags))}</span></span></a>'
        ))(*colour_facets(paints[i]['hex']))
        for i in ordered)

    sections = f"""<div class="filters">
  <div class="frow"><span class="flab">Colour</span><div class="fchips">{hue_chips}</div></div>
  <div class="frow"><span class="flab">Type</span><div class="fchips">{type_chips}</div></div>
  <div class="frow"><span class="flab">Tone</span><div class="fchips">{tone_chips}</div></div>
  <div class="fmeta"><span id="fcount">{len(idxs)} colours</span><button class="fclear" id="fclear" hidden>Clear filters</button></div>
</div>
<div class="swatches" id="libgridfilter">{tiles}</div>"""

    be = H.escape(b)
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{be} colours \u2014 the full range | PaintDial</title>
<link rel="canonical" href="{DOMAIN}/colours/{base_slug(b)}">
<meta name="description" content="All {len(idxs)} {be} paint colours. Filter by colour, neutral or tone, and see each one\u2019s matches from other brands, lighter and darker versions, and where to buy.">
{FAVICON}
{FONTS}<style>{LIB_CSS}</style></head><body><div class="wrap">
{LIB_HDR}
<div class="top"><span class="eyebrow">The colour library</span>
<h1>{be}</h1>
<p class="lede">All {len(idxs)} {be} colours. Muted shades show up under both their colour and Neutral, so a filter won\u2019t hide them. Tap a swatch for its matches from other brands, lighter and darker versions, and where to buy.</p>{dupes_link}{source_line(b)}</div>
<div class="fan">{fan}</div>
{sections}
<footer>{FOOT}</footer>
</div><div class="top-band"></div>
<script>
(function(){{
  var grid=document.getElementById('libgridfilter');
  var sws=[].slice.call(grid.querySelectorAll('.sw'));
  var total=sws.length, countEl=document.getElementById('fcount'), clearEl=document.getElementById('fclear');
  var sel={{hue:new Set(),type:new Set(),tone:new Set()}};
  function apply(){{
    var shown=0;
    for(var k=0;k<sws.length;k++){{
      var s=sws[k], ok=true;
      // within an axis: OR; across axes: AND
      ['hue','type','tone'].forEach(function(ax){{
        if(!sel[ax].size) return;
        var vals=(s.getAttribute('data-'+ax)||'').split('|');
        var hit=false; sel[ax].forEach(function(v){{ if(vals.indexOf(v)>-1) hit=true; }});
        if(!hit) ok=false;
      }});
      s.style.display = ok ? '' : 'none';
      if(ok) shown++;
    }}
    countEl.textContent = shown===total ? total+' colours' : shown+' of '+total+' colours';
    var any = sel.hue.size||sel.type.size||sel.tone.size;
    clearEl.hidden = !any;
  }}
  [].slice.call(document.querySelectorAll('.fchip')).forEach(function(c){{
    c.addEventListener('click',function(){{
      var ax = c.hasAttribute('data-hue')?'hue':c.hasAttribute('data-type')?'type':'tone';
      var v = c.getAttribute('data-'+ax);
      if(sel[ax].has(v)){{ sel[ax].delete(v); c.classList.remove('on'); }}
      else {{ sel[ax].add(v); c.classList.add('on'); }}
      apply();
    }});
  }});
  clearEl.addEventListener('click',function(){{
    sel={{hue:new Set(),type:new Set(),tone:new Set()}};
    [].slice.call(document.querySelectorAll('.fchip.on')).forEach(function(c){{c.classList.remove('on');}});
    apply();
  }});
}})();
</script>
</body></html>"""

def build_colours_index():
    cards = ''
    for b in BRAND_ORDER:
        idxs = [i for i in range(N) if paints[i]['brand'] == b]
        srt = sorted(idxs, key=lambda i: ((C[i] < 6), HUE[i], L[i]))
        step = max(1, len(srt)//36)
        fan = ''.join(f'<span style="background:{paints[i]["hex"]}"></span>' for i in srt[::step][:36])
        cards += (f'<a class="lib" href="/colours/{base_slug(b)}">'
                  f'<span class="l-fan">{fan}</span>'
                  f'<span class="l-body"><span class="l-nm">{H.escape(b)}</span>'
                  f'<span class="l-n">{len(idxs)} colours</span></span></a>')
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The colour library: every colour from {NBRANDS} brands sold in the UK | PaintDial</title>
<link rel="canonical" href="{DOMAIN}/colours/">
<meta name="description" content="Browse {N:,} paint colours from {brand_list()}. Each one has matches from other brands and lighter and darker versions.">
{FAVICON}
{FONTS}<style>{LIB_CSS}</style></head><body><div class="wrap">
{LIB_HDR}
<div class="top"><span class="eyebrow">The colour library</span>
<h1>Every colour, brand by brand</h1>
<p class="lede">{N:,} paints across {BRANDS_WORD} brands sold in the UK. Each brand's full published range, grouped by colour family. You can also start from any colour in the <a href="/" style="color:inherit">colour tool</a>.</p></div>
<div class="lib-grid">{cards}</div>
<footer>{FOOT}</footer>
</div><div class="top-band"></div></body></html>"""

# ---------- SEO "alternatives" decision-pages (premium colours only) ----------
ALT_CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#665F54;--hairline:#E3DFD5;--pc:#5E7E8B;--serif:"Fraunces Amp","Fraunces",Georgia,serif;--sans:"Archivo",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6}
.wrap{max-width:1040px;margin:0 auto;padding:0 32px 72px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--hairline)}
.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px;font-size:13px}
header nav a{font-family:var(--sans);font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:inline-flex;gap:3px}.lib-swatches i{width:13px;height:13px;border-radius:3px;display:inline-block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
h1{font-family:var(--serif);font-size:36px;font-weight:600;letter-spacing:-.015em;line-height:1.15;margin:36px 0 0}
.top-band{height:12px;background:var(--pc)}
.pn{font-weight:600;white-space:nowrap}
a.pn{color:inherit;text-decoration:none;border-bottom:1.5px solid var(--hairline);transition:border-color .12s}
a.pn:hover{border-color:var(--pc)}
.pn i{display:inline-block;width:.72em;height:.72em;border-radius:.2em;margin-right:.3em;vertical-align:-.02em;box-shadow:inset 0 0 0 1px rgba(0,0,0,.14);background:var(--pc)}
h1 .pn i{width:.52em;height:.52em;border-radius:.13em;margin-right:.24em;vertical-align:.03em}
.hero-card{display:flex;margin:24px 0 22px;border:1px solid var(--hairline);border-radius:14px;overflow:hidden;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06),0 10px 26px rgba(33,31,27,.07)}
@supports (background: color-mix(in srgb, red 10%, white)){
  .hero-card{background:color-mix(in srgb, var(--pc) 9%, #fff)}
  .hero-stats span{background:color-mix(in srgb, var(--pc) 5%, #fff)}
}
.hero-sw{width:150px;flex:none;align-self:stretch;min-height:118px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.05)}
.hero-info{padding:18px 20px;display:flex;flex-direction:column;justify-content:center}
.hero-label{font-size:10.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.hero-name{font-family:var(--serif);font-size:22px;font-weight:600;line-height:1.15;margin:3px 0 11px}
.hero-stats{display:flex;gap:9px;flex-wrap:wrap}
.hero-stats span{display:inline-flex;align-items:baseline;gap:6px;font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;border:1px solid var(--hairline);border-radius:8px;padding:5px 10px}
.hero-stats i{font-style:normal;font-size:9.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.intro{font-size:15px;margin-bottom:14px}
@media(max-width:560px){.hero-sw{width:88px;min-height:96px}.hero-name{font-size:19px}}
h2{font-family:var(--serif);font-size:22px;font-weight:600;margin:32px 0 14px}
h2::after{content:'';display:block;width:34px;height:4px;border-radius:2px;background:var(--pc);margin-top:7px}
.alts{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.a-rank{flex:none;width:30px;text-align:center;font-family:var(--serif);font-size:14px;font-weight:600;color:var(--muted)}.alt{position:relative;display:flex;align-items:center;gap:12px;border:1px solid var(--hairline);border-radius:14px;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06);padding:0 14px 0 10px;overflow:hidden;text-decoration:none;color:inherit;cursor:pointer;transition:transform .12s,box-shadow .12s}
.alt:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(33,31,27,.1)}
.alt:focus-within{outline:2px solid var(--pc);outline-offset:2px}
.a-sw{width:72px;align-self:stretch;min-height:84px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.05);flex:none}
.a-body .pd-cmp-btn{position:relative;top:auto;left:auto;margin-top:9px}
.a-body{flex:1;min-width:0;padding:13px 0}
.a-nm{display:block;font-family:var(--serif);font-size:16px;font-weight:600;line-height:1.2;text-wrap:pretty;text-decoration:none;color:inherit;outline:none}
.a-nm::after{content:"";position:absolute;inset:0}
.a-br{display:block;font-size:11px;letter-spacing:.03em;text-transform:uppercase;color:var(--muted);margin:2px 0 4px}
.a-note{display:block;font-size:13px;color:var(--ink)}
.a-diff{display:block;font-size:12.5px;color:var(--muted);line-height:1.35;margin-top:1px}
.a-hex{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;align-self:flex-start;padding-top:13px}
.verdict{border:1px solid var(--hairline);border-radius:14px;padding:15px 17px;margin:16px 0 4px;background:color-mix(in srgb,var(--pc) 5%,var(--card))}
.verdict h3{font-family:var(--serif);font-size:16px;font-weight:600;margin:0 0 6px;display:flex;align-items:center;gap:8px}
.verdict h3::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--pc);flex:0 0 auto}
.verdict p{font-size:14px;color:var(--ink);margin:0;line-height:1.65}
.faq .q{border-top:1px solid var(--hairline);padding:16px 0}
.faq h3{font-family:var(--serif);font-size:16px;font-weight:600;margin-bottom:5px}
.faq p{font-size:14px;color:var(--ink)}
.cta{margin-top:30px;border:1px solid var(--hairline);border-radius:14px;background:var(--card);padding:22px;text-align:center}
.cta a{display:inline-block;margin-top:12px;font-size:14px;font-weight:600;text-decoration:none;background:var(--ink);color:var(--paper);padding:11px 20px;border-radius:8px}
.afftext{font-size:11px;color:var(--muted);margin-top:14px}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:640px){h1{font-size:28px}.alts{grid-template-columns:1fr}}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:11px;height:11px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:4px 9px;border-radius:8px;box-shadow:none}header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}
"""
ALT_CSS += WIDE_SHELL_CSS + ALT_WIDE_CSS

ALT_BRANDS = {b for b in BRAND_ORDER if TIER[b] == 3}  # the premium tier: brands that get alternatives pages

DESC_WORD = {'Reds': 'red', 'Oranges': 'orange', 'Yellows': 'yellow', 'Greens': 'green',
             'Teals': 'blue-green', 'Blues': 'blue', 'Purples': 'purple', 'Pinks': 'pink',
             'Browns': 'brown', 'Whites & neutrals': 'off-white', 'Greys': 'grey',
             'Blacks': 'near-black'}

_TINT = {'Reds': 'pink', 'Oranges': 'pink', 'Yellows': 'green', 'Greens': 'green',
         'Teals': 'blue-green', 'Blues': 'blue', 'Purples': 'lilac'}
def neutral_word(hx, l):
    """What to call a colour family() files under 'Whites & neutrals'. That family runs from true
    off-whites to pale greys, beiges and creams, and "off-white" was being used for all 3,000 of
    them. l is CIELab lightness. Only the wording: family(), the library filters and the research
    figures are untouched."""
    _, c, h = _ok_lch(hx)
    white = l >= 88
    if 50.0 <= h < 105.0:                      # the warm window of the neutral gate
        if c < 0.008: return 'off-white' if white else 'grey'
        if c < 0.020: return 'warm off-white' if white else 'warm grey'
        if c < 0.040: return 'warm off-white' if white else 'beige'
        if h >= 75:   return 'cream' if l >= 86 else 'sandy beige'
        return 'peach' if l >= 86 else 'pinkish beige'
    if c < 0.008: return 'off-white' if white else 'grey'
    return ('off-white' if white else 'grey') + ' with a hint of ' + _TINT[_hue_band(h)]

def describe(i):
    """Human-facing shade wording for the alternatives pages.
    Uses family() -- the same OKLab-calibrated classifier as the library -- so the two can
    never disagree. This previously used CIELab hue with HSL-era band edges, which called
    Stiffkey Blue a 'deep purple', Sulking Room Pink a 'light orange' and pure blue 'pink'."""
    l = L[i]
    depth = 'pale' if l > 78 else 'light' if l > 60 else 'mid-toned' if l > 38 else 'deep' if l > 18 else 'very dark'
    fam = DESC_WORD[family(paints[i]['hex'])]
    if fam == 'off-white':
        fam = neutral_word(paints[i]['hex'], l)
    return depth, fam

def diff_bits(i, k):
    """How match k differs from colour i, computed from the colour values.
    Thresholds are set from the real distribution of close-match pairs across
    the library: 'slightly' = 75th percentile of observed difference,
    'noticeably' = 90th. So the wording is measured, not impressionistic."""
    bits = []
    dl = lrv(L[k]) - lrv(L[i])
    if abs(dl) >= 1.5:
        word = 'lighter' if dl > 0 else 'darker'
        pts = round(abs(dl))
        strength = 'noticeably ' if abs(dl) >= 4 else ''
        bits.append(f'{strength}{word} (about {pts} LRV point{"s" if pts != 1 else ""})')
    db = OK[k, 2] - OK[i, 2]          # OKLab b axis: yellow (+) / blue (-)
    if abs(db) >= 0.010:
        word = 'warmer' if db > 0 else 'cooler'
        strength = 'noticeably ' if abs(db) >= 0.020 else 'slightly '
        bits.append(f'{strength}{word}')
    dc = OC[k] - OC[i]
    if abs(dc) >= 0.010:
        word = 'more saturated' if dc > 0 else 'softer'
        strength = 'noticeably ' if abs(dc) >= 0.020 else 'slightly '
        bits.append(f'{strength}{word}')
    return bits


def joinbits(bits):
    if not bits: return ''
    if len(bits) == 1: return bits[0]
    return ', '.join(bits[:-1]) + ' and ' + bits[-1]


def cooler_note(i, k):
    """Only earned when there is a real warm/cool shift: cool light in a
    north-facing room accentuates a cooler match; warm south light does the
    opposite. Standard decorating practice, and it follows from the values."""
    db = OK[k, 2] - OK[i, 2]
    if db <= -0.010:
        return ' A cooler match reads cooler still in a north-facing room, where the light is indirect.'
    if db >= 0.010:
        return ' A warmer match reads warmer again in a south-facing room that gets direct sun.'
    return ''


def matchword(x):
    return 'near-identical' if x < 2 else 'very close' if x < 5 else 'close' if x < 10 else 'a loose match'


# ---------- ranked dupes pages (league table per premium brand) ----------
DUPES_CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#665F54;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces Amp","Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.wrap{max-width:1100px;margin:0 auto;padding:0 32px 80px}
header{display:flex;align-items:center;justify-content:space-between;padding:20px 0 16px;border-bottom:1px solid var(--hairline);margin-bottom:34px}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo-dial{width:22px;height:22px;border-radius:50%;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);position:relative}
.logo-dial::after{content:"";position:absolute;inset:5px;border-radius:50%;background:#fff;border:2px solid #211F1B}
header nav{display:flex;gap:18px;align-items:center}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}
header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05)}
.lib-swatches{display:inline-flex;gap:3px}.lib-swatches i{width:13px;height:13px;border-radius:3px;display:inline-block}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:36px;font-weight:600;letter-spacing:-.012em;line-height:1.08;margin:8px 0 10px}
.sub{font-size:14.5px;color:var(--muted);max-width:640px;margin-bottom:8px}
.method{font-size:12.5px;color:var(--muted);max-width:640px;margin-bottom:30px}
.method a{color:var(--pc)}
.dupe-list{display:flex;flex-direction:column;gap:10px}
.row{position:relative;display:grid;grid-template-columns:34px 1fr auto 1fr;gap:0;align-items:stretch;background:var(--card);border:1px solid var(--hairline);border-radius:14px;overflow:hidden;text-decoration:none;color:inherit;cursor:pointer;transition:box-shadow .12s,transform .12s}
.row:hover{box-shadow:0 6px 18px rgba(33,31,27,.10);transform:translateY(-1px)}
.row:focus-within{outline:2px solid var(--pc);outline-offset:2px}
.row a.nm{text-decoration:none;color:inherit;outline:none}
.row a.nm::after{content:"";position:absolute;inset:0}
.arrow{padding:0 8px}.arrow .pd-cmp-btn{position:relative;top:auto;left:auto}
.rank{display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-size:14px;font-weight:600;color:var(--muted);background:color-mix(in srgb,var(--paper) 60%,#fff);border-right:1px solid var(--hairline)}
.half{display:flex;align-items:center;gap:12px;padding:10px 14px;min-width:0}
.half .sw{width:64px;height:44px;border-radius:8px;flex:none;border:1px solid rgba(33,31,27,.08)}
.half .tx{min-width:0}
.half .nm{display:block;font-family:var(--serif);font-size:15.5px;font-weight:600;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.half .br{display:block;font-size:10.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-top:3px}
.arrow{display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px}
.badge{margin-left:auto;flex:none;font-size:10.5px;font-weight:600;letter-spacing:.05em;padding:4px 9px;border-radius:999px;border:1px solid var(--hairline);color:var(--muted);background:var(--paper);white-space:nowrap}
.badge.good{color:#3E7A4C;border-color:#3E7A4C33;background:#3E7A4C0d}
.brands-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:30px}
.brands-nav a{font-size:12.5px;font-weight:600;color:var(--ink);text-decoration:none;padding:7px 14px;background:#fff;border:1px solid var(--hairline);border-radius:999px}
.brands-nav a.on{background:var(--ink);color:#fff;border-color:var(--ink)}
footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}
footer a{color:var(--muted)}
.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}
.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:760px){.row{grid-template-columns:28px 1fr}.rank{grid-row:1 / span 2}.arrow{position:absolute;right:9px;bottom:9px;padding:0}.half{grid-column:2;padding:9px 11px;display:grid;grid-template-columns:46px 1fr;column-gap:12px;align-items:center}.half:last-of-type{border-top:1px dashed var(--hairline)}.half .sw{width:46px;height:36px;grid-row:1 / span 2}.half .tx{grid-column:2;min-width:0}.badge{grid-column:2;justify-self:start;margin:4px 0 0}h1{font-size:28px}.wrap{padding:0 18px 60px}}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:11px;height:11px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px;margin-bottom:0}.mnav{margin-bottom:22px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:4px 9px;border-radius:8px;box-shadow:none}header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}
"""
DUPES_CSS += NAV_CSS + WIDE_SHELL_CSS


DUPE_TARGETS = [b for b in BRAND_ORDER if TIER[b] == 3]

def build_dupes_page(brand):
    bslug = base_slug(brand)
    bname = H.escape(brand)
    idxs = [i for i in range(N) if paints[i]['brand'] == brand]
    rows = []
    for i in idxs:
        d = mdist(i)
        best_j, best_d = None, None
        for k in range(N):
            if TIER[paints[k]['brand']] >= 3:
                continue  # dupe must come from a value or mid-range brand
            if best_d is None or d[k] < best_d:
                best_j, best_d = k, float(d[k])
        rows.append((i, best_j, best_d))
    rows.sort(key=lambda r: r[2])

    nav = ''.join(
        f'<a href="/dupes/{base_slug(b)}"{" class=\"on\"" if b == brand else ""}>{H.escape(b)}</a>'
        for b in DUPE_TARGETS)

    def rowhtml(rank, i, j, dd):
        p, q = paints[i], paints[j]
        w = matchword(dd)
        badge_cls = ' good' if dd < 5 else ''
        # Row is a div with the first name as a stretched link; the compare button
        # lives in the middle cell (top-right of the row on phones).
        return (f'<div class="row">'
                f'<span class="rank">{rank}</span>'
                f'<span class="half"><span class="sw" style="background:{p["hex"]}"></span>'
                f'<span class="tx"><a class="nm" href="/colours/{slugs[i]}">{H.escape(p["name"])}</a>'
                f'<span class="br">{H.escape(p["brand"])}</span></span></span>'
                f'<span class="arrow">{cmp_btn(p, q, w)}</span>'
                f'<span class="half"><span class="sw" style="background:{q["hex"]}"></span>'
                f'<span class="tx"><span class="nm">{H.escape(q["name"])}</span>'
                f'<span class="br">{H.escape(q["brand"])} \u00b7 {TIER_WORD[TIER[q["brand"]]]}</span></span>'
                f'<span class="badge{badge_cls}">{w}</span></span></div>')

    body = ''.join(rowhtml(n + 1, i, j, dd) for n, (i, j, dd) in enumerate(rows))
    title = f'{bname} dupes \u2014 every colour\u2019s closest value \u0026 mid-range match, ranked'
    desc = (f'Every {bname} colour matched to its closest value or mid-range equivalent, '
            f'ranked from the strongest match down. Tap any row for the full colour page and where to buy.')
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}/dupes/{bslug}">
{_ldjson(
  _breadcrumb([("Home","/"),("Dupes",None),(brand+" dupes",f"/dupes/{bslug}")]),
  _itemlist([(f"{paints[i0]['name']} \u2192 {paints[j0]['name']} by {paints[j0]['brand']}", f"/colours/{slugs[i0]}") for (i0,j0,_dd) in rows[:30]])
)}
{FONTS}<style>{DUPES_CSS}{COMPARE_BTN_CSS}</style></head><body><div class="wrap">
{HDR}
<span class="eyebrow">Ranked dupes</span>
<h1>Every {bname} colour\u2019s best-value match, ranked</h1>
<p class="sub">All {len(rows)} {bname} colours, each paired with its closest match from a value or mid-range brand, strongest match first. Tap a row for the full colour page, more matches and where to buy.</p>
<p class="method">Matches are computed from each brand\u2019s published digital swatches{source_short()} using perceptual colour distance. No screen shows paint exactly, so get testers of both before you buy.</p>
<div class="brands-nav">{nav}</div>
<div class="dupe-list">{body}</div>
<footer>{FOOT}</footer>
</div>{COMPARE_SCRIPT}</body></html>"""




# ---------- the UK's most searched-for colours, each with its closest lower-tier match ----------
# The list is popular-colours.json, copied in order from one published ranking (see its _source
# and _method), top 100, nothing added or removed: the page claims "most searched", so it must
# not be topped up or trimmed by hand. Refresh by replacing the file with a newer copy of the
# same ranking (or Will's own Keyword Planner figures, which would also let it cover brands the
# current source doesn't measure).
POPULAR = json.load(open('popular-colours.json', encoding='utf-8'))
POPULAR_PATH = '/most-popular-paint-colours/'

def _pkey(brand, name):
    import unicodedata as _ud
    n = _ud.normalize('NFKD', name.replace('’', "'"))
    return brand, re.sub(r'[^a-z0-9]', '', n.lower())

_PIDX = {_pkey(p['brand'], p['name']): i for i, p in enumerate(paints)}
POPULAR_IDX = []
for _b, _n in POPULAR['colours']:
    assert _pkey(_b, _n) in _PIDX, f'popular-colours.json: {_b} {_n} is not in the library'
    POPULAR_IDX.append(_PIDX[_pkey(_b, _n)])

def popular_match(i):
    """Closest match from a brand in a lower tier: value or mid-range for a premium colour,
    value for a mid-range one. A value colour (none at present) gets the closest from any
    other brand."""
    d = mdist(i)
    t = TIER[paints[i]['brand']]
    best_j, best_d = None, None
    for k in range(N):
        tk = TIER[paints[k]['brand']]
        if paints[k]['brand'] == paints[i]['brand'] or (t > 1 and tk >= t):
            continue
        if best_d is None or d[k] < best_d:
            best_j, best_d = k, float(d[k])
    return best_j, best_d

# Labels that say which side is the match: a "Closest match" line on every match, and column
# heads over the list on wider screens (on phones the rows stack, so the per-row label does it).
POPULAR_CSS = """
.half .lab{display:block;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--pc);margin-bottom:3px}
.dupe-heads{display:grid;grid-template-columns:34px 1fr auto 1fr;margin:0 0 8px;padding:0 1px;font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.dupe-heads span{padding:0 14px}.dupe-heads span:nth-child(3){width:112px;padding:0}
@media(max-width:760px){.dupe-heads{display:none}}
"""

def build_popular_page():
    rows = []
    for rank, i in enumerate(POPULAR_IDX, 1):
        j, dd = popular_match(i)
        p, q = paints[i], paints[j]
        w = matchword(dd)
        href = f'/alternatives/{slugs[i]}' if p['brand'] in ALT_BRANDS else f'/colours/{slugs[i]}'
        rows.append(
            f'<div class="row">'
            f'<span class="rank">{rank}</span>'
            f'<span class="half"><span class="sw" style="background:{p["hex"]}"></span>'
            f'<span class="tx"><a class="nm" href="{href}">{H.escape(p["name"])}</a>'
            f'<span class="br">{H.escape(p["brand"])}</span></span></span>'
            f'<span class="arrow">{cmp_btn(p, q, w)}</span>'
            f'<span class="half"><span class="sw" style="background:{q["hex"]}"></span>'
            f'<span class="tx"><span class="lab">Closest match</span><span class="nm">{H.escape(q["name"])}</span>'
            f'<span class="br">{H.escape(q["brand"])} · {TIER_WORD[TIER[q["brand"]]]}</span></span>'
            f'<span class="badge{" good" if dd < 5 else ""}">{w}</span></span></div>')
    n = len(rows)
    src = 'https://paintdb.com/popular/country/uk'
    title = 'The UK’s most popular paint colours by search, and their closest matches'
    desc = (f'The {n} paint colours searched for most by name in the UK, from Farrow &amp; Ball’s '
            f'Skimming Stone down, each next to its closest match from a value or mid-range brand.')
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{POPULAR_PATH}">
{_ldjson(
  _breadcrumb([("Home","/"),("Most searched colours",POPULAR_PATH)]),
  _itemlist([(f"{paints[i0]['name']} by {paints[i0]['brand']}", f"/colours/{slugs[i0]}") for i0 in POPULAR_IDX[:30]])
)}
{FONTS}<style>{DUPES_CSS}{COMPARE_BTN_CSS}{POPULAR_CSS}</style></head><body><div class="wrap">
{HDR}
<span class="eyebrow">Most searched</span>
<h1>The UK’s most searched-for paint colours</h1>
<p class="sub">The {n} paint colours searched for most by name in the UK, each next to its closest match from a value or mid-range brand. Tap a row to see every brand’s closest match.</p>

<div class="dupe-heads" aria-hidden="true"><span></span><span>Most searched</span><span></span><span>Closest match from a value or mid-range brand</span></div>
<div class="dupe-list">{''.join(rows)}</div>
<p class="method" style="margin-top:22px">Ranked by average monthly Google searches for each colour’s name, {POPULAR['_period']}, from <a href="{src}" rel="nofollow noopener" target="_blank">PaintDB</a>’s UK figures. PaintDB measures a handful of brands in the UK, mostly Farrow &amp; Ball and Dulux, so colours from other brands can’t appear in the ranking. Matches are computed from each brand’s published digital swatches{source_short()} using perceptual colour distance. No screen shows paint exactly, so get testers of both before you buy.</p>
<footer>{FOOT}</footer>
</div>{COMPARE_SCRIPT}</body></html>"""

# ---------- static trust pages: how it works + about ----------
PAGES_CSS = """
.faq{margin:6px 0 24px}.faq details{border-top:1px solid var(--hairline);padding:12px 0}.faq details:last-child{border-bottom:1px solid var(--hairline)}.faq summary{font-family:var(--serif);font-size:17px;font-weight:600;cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:16px;align-items:baseline}.faq summary::-webkit-details-marker{display:none}.faq summary::after{content:"+";color:var(--muted);font-family:var(--sans);font-weight:400;flex:none}.faq details[open] summary::after{content:"\\2013"}.faq p{margin:8px 0 2px;max-width:66ch}
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#665F54;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces Amp","Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.65}
.wrap{max-width:760px;margin:0 auto;padding:0 28px 80px}
header{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:1px solid var(--hairline);margin-bottom:38px}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo-dial{width:22px;height:22px;border-radius:50%;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);position:relative}
.logo-dial::after{content:"";position:absolute;inset:5px;border-radius:50%;background:#fff;border:2px solid #211F1B}
header nav{display:flex;gap:12px;align-items:center}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}
header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 2px rgba(33,31,27,.05)}
.lib-swatches{display:inline-flex;gap:3px}.lib-swatches i{width:13px;height:13px;border-radius:3px;display:inline-block}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:34px;font-weight:600;letter-spacing:-.012em;line-height:1.1;margin:8px 0 18px}
h2{font-family:var(--serif);font-size:21px;font-weight:600;margin:34px 0 10px}
p{font-size:15px;color:var(--ink);margin-bottom:14px;max-width:640px}
p.muted{color:var(--muted);font-size:13.5px}
ul{margin:0 0 14px 20px;max-width:620px}
li{font-size:15px;margin-bottom:8px}
a{color:var(--pc)}
.label{display:inline-block;font-weight:600}
footer{margin-top:52px;padding-top:20px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}
footer a{color:var(--muted)}
.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}
.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:11px;height:11px}
h1{font-size:27px}.wrap{padding:0 18px 60px}
}

.pn{font-weight:600;white-space:nowrap;color:inherit;text-decoration:none;border-bottom:1.5px solid var(--hairline);transition:border-color .12s}
.pn:hover{border-color:var(--ink)}
.pn i{display:inline-block;width:.72em;height:.72em;border-radius:.2em;margin-right:.32em;vertical-align:-.02em;box-shadow:inset 0 0 0 1px rgba(0,0,0,.14)}
table{width:100%;border-collapse:collapse;margin:14px 0 18px;font-size:14px}
thead th{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:0 10px 7px 0;border-bottom:1px solid var(--hairline)}
tbody td{padding:10px 10px 10px 0;border-bottom:1px solid var(--hairline);vertical-align:top;line-height:1.5}
tbody tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--muted);background:rgba(0,0,0,.035);padding:1px 5px;border-radius:4px}
@media(max-width:560px){table{font-size:12.5px}thead th,tbody td{padding-right:6px}code{font-size:11px}}

/* --- Paint Match Index visuals --- */
.pair{margin:0 0 14px}
.pair-blocks{display:flex;height:132px;border-radius:14px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)}
.pair-half{flex:1;position:relative;text-decoration:none;display:flex;align-items:flex-end;padding:12px 13px;transition:flex .18s ease}
.pair-half:hover{flex:1.06}
.pair-lab{font-size:12.5px;line-height:1.35;opacity:.94}
.pair-lab b{display:block;font-family:var(--serif);font-size:15px;font-weight:600}
.pair-lab span{font-size:11px;opacity:.8}
.pair figcaption{font-size:11.5px;color:var(--muted);margin-top:6px}
.stack{display:flex;height:44px;border-radius:8px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08);margin:14px 0 8px}
.stack i{display:block;height:100%}
.stack-key{font-size:11.5px;color:var(--muted);margin:0 0 18px}
.bignum{font-family:var(--serif);font-size:34px;font-weight:600;line-height:1.15;margin:4px 0 2px}
.bignum small{font-size:15px;color:var(--muted);font-family:var(--sans);font-weight:400;display:block;margin-top:3px}
.rsch-cards{display:grid;gap:14px;margin:22px 0}
.rsch-card{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--hairline);border-radius:14px;padding:20px 22px;transition:transform .15s}
.rsch-card:hover{transform:translateY(-2px)}
.rsch-card small{display:block;font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}.rsch-card b{font-family:var(--serif);font-size:21px;font-weight:600;line-height:1.25;display:block;margin-bottom:8px;text-wrap:balance}
.rsch-card span{font-size:13.5px;color:var(--muted)}
.uq-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:9px;margin:14px 0 18px}
.uq{display:flex;flex-direction:column;justify-content:flex-end;min-height:104px;padding:11px;border-radius:14px;
text-decoration:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.09);transition:transform .12s}
.uq:hover{transform:translateY(-2px)}
.uq b{font-family:var(--serif);font-size:14px;font-weight:600;line-height:1.25}
.uq span{font-size:10.5px;opacity:.78}
.uq-near{margin-top:3px;opacity:.6}
.bars{margin:14px 0 18px}
.brow{display:grid;grid-template-columns:118px 1fr 42px 118px;align-items:center;gap:10px;padding:5px 0;font-size:13px}
.btrack{background:rgba(0,0,0,.06);border-radius:999px;height:9px;overflow:hidden}
.btrack i{display:block;height:100%;background:var(--pick,#5E7E8B);border-radius:999px}
.bval{font-weight:600;text-align:right}
.bnote{font-size:11px;color:var(--muted)}
@media(max-width:560px){
.pair-blocks{height:112px}.pair-lab b{font-size:13.5px}
.uq-grid{grid-template-columns:1fr 1fr;gap:7px}
.brow{grid-template-columns:82px 1fr 38px;gap:7px;font-size:12px}.bnote{display:none}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px;margin-bottom:0}.mnav{margin-bottom:22px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:4px 9px;border-radius:8px;box-shadow:none}header nav a.nav-cta{font-size:0;gap:0;padding:6px;border-radius:50%}header nav a.nav-cta .cta-wheel{width:20px;height:20px}}
@media(max-width:370px){.lib-swatches{display:none}.logo{font-size:19px}.lib-link{padding:4px 8px}.mnav{gap:13px}.mnav a{font-size:12px}}
"""
PAGES_CSS += NAV_CSS + WIDE_SHELL_CSS + PAGES_WIDE_CSS

# Ko-fi card on the About and Contact pages. The footer's small "buy Will a coffee" link
# stays on every page; this is the big version.
KOFI_URL = "https://ko-fi.com/paintdial"
PAGES_CSS += """
.kofi{max-width:640px;margin:30px 0 34px;padding:26px 30px;background:var(--card);border:1px solid var(--hairline);border-radius:14px;box-shadow:0 1px 3px rgba(33,31,27,.05)}
.kofi-line{font-family:var(--serif);font-size:23px;font-weight:600;line-height:1.3;margin:0 0 16px;text-wrap:balance}
.kofi-act{display:flex;align-items:center;gap:14px}
.kofi-act .kofi-cup{flex:none;width:58px;height:58px;margin-top:-6px}
.kofi-btn{display:inline-flex;align-items:center;justify-content:center;background:var(--ink);color:var(--paper)!important;font-size:16px;font-weight:600;text-decoration:none!important;padding:13px 24px;border-radius:8px;transition:transform .12s,box-shadow .12s}
.kofi-btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(33,31,27,.18)}
@media(max-width:560px){.kofi{text-align:center;padding:24px 20px}.kofi-line{font-size:20px}.kofi-act{justify-content:center}.kofi-btn{flex:1}.kofi-act .kofi-cup{width:50px;height:50px}}
"""
# A mug with PaintDial-blue paint dripping from the rim (option E of six, chosen 5 Nov 2026).
_MUG = 'M12 20h36v24a10 10 0 0 1-10 10H22a10 10 0 0 1-10-10z'
KOFI_ICON = (
    '<svg class="kofi-cup" viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
    f'<defs><clipPath id="kofi-mug"><path d="{_MUG}"/></clipPath></defs>'
    '<path d="M48 27h3.5a7 7 0 0 1 0 14H48" fill="none" stroke="#211F1B" stroke-width="3.4"/>'
    f'<path d="{_MUG}" fill="#F6F1E7"/>'
    '<path clip-path="url(#kofi-mug)" fill="#5E7E8B" d="M10 18H50V26.5C47 26.5 45.5 27 45.5 29V38a2.4 2.4 0 0 1-4.8 0'
    'V29c0-1.6-1-2.5-3-2.5H33.6c-1.6 0-2.4.8-2.4 2.2v2.6a2.1 2.1 0 0 1-4.2 0V28.7c0-1.4-.8-2.2-2.2-2.2H22.4'
    'c-1.4 0-2.3.9-2.3 2.3v6a2.3 2.3 0 0 1-4.6 0V28.5c0-1.3-.9-2-2-2H10z"/>'
    f'<path d="{_MUG}" fill="none" stroke="#211F1B" stroke-width="2.4" stroke-linejoin="round"/>'
    '<path d="M23 13c-2.4-2.8 2.2-4.2.2-7.6M30 12c-2.4-2.8 2.2-4.2.2-7.6M37 13c-2.4-2.8 2.2-4.2.2-7.6" '
    'fill="none" stroke="#9C9488" stroke-width="2.2" stroke-linecap="round"/></svg>')


def kofi_block(line="If you found PaintDial useful…"):
    return (f'<div class="kofi"><p class="kofi-line">{line}</p><div class="kofi-act">'
            f'<a class="kofi-btn" href="{KOFI_URL}" target="_blank" rel="noopener">'
            f'Buy Will a coffee on Ko-fi</a>{KOFI_ICON}</div></div>')


# Slim one-line version at the foot of every colour and alternatives page. index.html has a
# hand-copied twin under the tool's results (shown only once someone has used the tool), so
# change both if the wording or look changes.
KOFI_STRIP_CSS = (
    '.kofi-s{display:flex;align-items:center;gap:14px;margin:28px 0 0;padding:16px 22px;background:var(--card);'
    'border:1px solid var(--hairline);border-radius:14px}'
    '.kofi-s .kofi-cup{flex:none;width:46px;height:46px;margin-top:-5px}'
    '.kofi-s p{flex:1;font-family:var(--serif);font-size:19px;font-weight:600;line-height:1.3;margin:0;max-width:none;color:var(--ink)}'
    '.kofi-s a{flex:none;background:var(--ink);color:var(--paper)!important;font-family:var(--sans);font-size:14px;font-weight:600;'
    'text-align:center;text-decoration:none!important;padding:10px 18px;border-radius:8px;transition:transform .12s,box-shadow .12s}'
    '.kofi-s a:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(33,31,27,.18)}'
    '@media(max-width:560px){.kofi-s{flex-wrap:wrap;gap:10px 12px;padding:14px}'
    '.kofi-s p{flex-basis:100%;font-size:16.5px;text-wrap:balance}.kofi-s a{flex:1;padding:11px 18px}.kofi-s .kofi-cup{width:42px;height:42px}}')


def kofi_strip():
    return (f'<div class="kofi-s"><p>If you found PaintDial useful…</p>'
            f'<a href="{KOFI_URL}" target="_blank" rel="noopener">Buy Will a coffee on Ko-fi</a>{KOFI_ICON}</div>')


_VOID_TAGS = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr'}
_WIDE_CLASSES = {'rsch-cards', 'uq-grid', 'bars', 'stack', 'stack-key', 'pair', 'bignum'}
_TAG_RE = re.compile(r'<!--(.*?)-->|<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>', re.S)


def _top_level_blocks(html):
    """Split an HTML fragment into its top-level elements, in order (scripts and comments
    included as their own blocks). Bare top-level text is not expected in page bodies."""
    blocks, pos, depth, start = [], 0, 0, None
    while True:
        m = _TAG_RE.search(html, pos)
        if not m:
            break
        if m.group(0).startswith('<!--'):
            if depth == 0:
                blocks.append(m.group(0))
            pos = m.end()
            continue
        close, tag, selfclose = m.group(2), m.group(3).lower(), m.group(4)
        if not close and tag in ('script', 'style'):
            end = html.find(f'</{tag}>', m.end())
            end = len(html) if end < 0 else end + len(tag) + 3
            if depth == 0:
                blocks.append(html[m.start():end])
            pos = end
            continue
        if close:
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(html[start:m.end()])
                start = None
        elif tag in _VOID_TAGS or selfclose:
            if depth == 0:
                blocks.append(m.group(0))
        else:
            if depth == 0:
                start = m.start()
            depth += 1
        pos = m.end()
    return blocks


def _block_classes(block):
    m = re.match(r'<([a-zA-Z0-9]+)([^>]*)>', block)
    if not m:
        return '', set()
    c = re.search(r'class="([^"]*)"', m.group(2))
    return m.group(1).lower(), set(c.group(1).split()) if c else set()


def _is_visual(block):
    tag, cls = _block_classes(block)
    return tag in ('figure', 'table', 'form') or bool(cls & _WIDE_CLASSES)


def _sectionise(body, layout):
    """Wrap a text page's body for the wide-screen layout. Everything before the first <h2>
    (or a <!--sec--> marker) is the lead: eyebrow, title, intro. Each <h2> starts a section."""
    lead, secs, cur = [], [], None
    for b in _top_level_blocks(body):
        if b.startswith('<h2') or b == '<!--sec-->':
            cur = []
            secs.append(cur)
            if b != '<!--sec-->':
                cur.append(b)
            continue
        (cur if cur is not None else lead).append(b)
    out = ['<div class="lead">' + '\n'.join(lead) + '</div>']
    if not secs:
        return out[0]
    if layout == 'split':
        rows, k = [], 0
        while k < len(secs):
            sec = secs[k]
            text = [b for b in sec if not _is_visual(b)]
            fig = [b for b in sec if _is_visual(b)]
            nxt = secs[k + 1] if k + 1 < len(secs) else None
            if not fig and nxt and not any(_is_visual(b) for b in nxt) and k + 2 >= len(secs):
                # the last two text-only sections (Method, What this doesn't claim) share a row
                rows.append('<section class="split"><div class="sec-text">' + '\n'.join(text) + '</div>'
                            + '<div class="sec-fig sec-note">' + '\n'.join(nxt) + '</div></section>')
                k += 2
                continue
            rows.append('<section class="split"><div class="sec-text">' + '\n'.join(text) + '</div>'
                        + (f'<div class="sec-fig">{"".join(fig)}</div>' if fig else '') + '</section>')
            k += 1
        out.append('<div class="splits">' + '\n'.join(rows) + '</div>')
    else:
        cells = []
        for sec in secs:
            n_faq = sum(b.count('<details') + b.count('class="pm-q"') for b in sec)
            wide = any('rsch-cards' in _block_classes(b)[1] for b in sec) or n_faq > 5
            cells.append(f'<section class="sec{" sec-wide" if wide else ""}">' + '\n'.join(sec) + '</section>')
        out.append('<div class="secs">' + '\n'.join(cells) + '</div>')
    return '\n'.join(out)


def _page_shell(title, desc, path, body, head="", layout="grid"):
    # Text pages (About, How it works, Contact, research, photo page). The body is wrapped by
    # _sectionise so wide screens get columns instead of one narrow strip; see PAGES_WIDE_CSS.
    body = _sectionise(body, layout)
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{path}">{head}
{FONTS}<style>{PAGES_CSS}</style></head><body><div class="wrap">
{HDR}
{body}
<footer>{FOOT}</footer>
</div></body></html>"""

def build_method_page():
    faqs = [
        ("How accurate are the matches?",
         "The matching itself is exact: it compares each brand\u2019s published colour value" + source_short() + " with every other, using the same maths for every paint. What it cannot know is how a colour will look on your wall. Anything near-identical or very close is worth getting a tester of."),
        ("Why does the paint look different from the swatch on my screen?",
         "No screen can show paint exactly, and sheen, daylight, lamplight and the surface underneath all change how a colour looks. Get a tester."),
        ("If two paints are near-identical, can I just swap one for the other?",
         "For colour, yes. Finish and coverage are another matter: a matt from one brand won’t look like an eggshell from another. Match the colour here, then choose the finish on the brand\u2019s site."),
        ("Can a brand pay to rank higher?",
         "No. Rankings come from colour difference alone, and no brand has any say in them."),
        ("Are the prices accurate?",
         "They are typical per-litre ranges for a 2.5 litre tin mixed to the colour, checked against retailers in September 2026 (Lakeland Paints only sells a 5 litre tin, so its figure is for that, checked November 2026). They’re a rough guide to how brands compare. Check the retailer for the actual price. Retailers vary and bigger tins cost less per litre. The \u00a3 signs group them: \u00a3 is under \u00a3" + f"{PRICE_BANDS[0]:g}" + " a litre, \u00a3\u00a3 is \u00a3" + f"{PRICE_BANDS[0]:g}" + " to \u00a3" + f"{PRICE_BANDS[1]:g}" + " and \u00a3\u00a3\u00a3 is \u00a3" + f"{PRICE_BANDS[1]:g}" + " or more."),
        ("Why isn\u2019t the brand I use in the library?",
         f"PaintDial covers {BRANDS_WORD} brands sold in the UK, chosen because they publish digital colour values and have ranges people ask about. I add a brand when there’s a reliable published source for its colours."),
        # Figures from the Dulux Trade Colour Palette fandeck (duluxtradepaintexpert.co.uk), checked
        # 4 Nov 2026 against the Dulux colours in the library with the site's own distance measure.
        ("Is Dulux Trade the same as Dulux?",
         "For colour, almost entirely. The Dulux Trade Colour Palette fan deck has 2,079 colours. 1,133 of them have exactly the same published value as a Dulux colour on PaintDial, and another 873 are near-identical or very close to one. The rest are mostly trade shades with a code instead of a name (like 10RR 73/016), and all but 12 have a very close match from a brand already here. That’s why Dulux Trade isn’t listed as a separate brand: it would mostly show you the same colours twice. You can still type a Dulux Trade code into the search to find that colour and its closest matches from every brand. The paint itself is a different product, so finish and coverage can differ even where the colour is the same. Checked November 2026."),
        ("Is PaintDial free?",
         "Yes. There’s no account to make and nothing to install. The shortlist is saved in your browser, on your device."),
    ]
    faq_html = "".join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    body = f"""<span class="eyebrow">Methodology</span>
<h1>How PaintDial matches colours</h1>
<p>PaintDial compares {N:,} paints from {BRANDS_WORD} brands sold in the UK and finds the closest matches to any colour across all of them at once.</p>

<h2>Where the colour data comes from</h2>
<p>Every colour in the library uses the brand\u2019s own published digital swatch, the colour value each manufacturer puts on its website{source_exception()}. I don\u2019t photograph or estimate any colours myself. LRV (light reflectance value) shown on colour pages is estimated from the swatch rather than measured from paint.</p>

<h2>How matches are calculated</h2>
<p>Matches are ranked by perceptual colour difference, a measure of how different two colours look to the eye. It\u2019s computed in the OKLab colour space, which handles hue more faithfully than older formulas: blues stay blue as they lighten, and purples don\u2019t get mistaken for blues. The ranking also weights hue more heavily than lightness. A paint a touch lighter or darker still reads as the same colour, but one that has drifted in hue doesn\u2019t, so matches keep the colour\u2019s character and the lighter and darker row on each colour page covers depth.</p>

<h2 id="difference">What the match labels and numbers mean</h2>
<p>Every match has a label and a number. The number is the difference between the two colours\u2019 published values: 0 means they are the same value, and the bigger it gets the further apart they are. The label is set by the number.</p>
<ul>
<li><span class="label">Near-identical</span> (under 2): a difference most people can\u2019t see on a wall. On screen the swatches look the same.</li>
<li><span class="label">Very close</span> (2 to 5): a difference you\u2019d struggle to spot unless the two were side by side.</li>
<li><span class="label">Close</span> (5 to 10): visibly similar, a little off in tone or depth.</li>
<li><span class="label">Same family</span>: further apart, but still the same hue family, checked in OKLab rather than by position in the list.</li>
<li><span class="label">Related / similar tone</span>: close in overall feel, but a different colour family.</li>
</ul>
<p>The number is on roughly the same scale as Delta E, the measure paint and print people use, but it isn\u2019t a Delta E figure and won\u2019t equal one from another site. It is the OKLab difference described above, with hue counted double and lightness counted a little less. It compares published digital values, so treat it as a guide to which testers to order.</p>

<h2>RAL Classic, BS 4800 and Dulux Trade codes</h2>
<p>Trade and specification colours are covered too: type a RAL Classic code (say, \u201cRAL 7016\u201d), a British Standard BS 4800 code (say, \u201c08 B 15\u201d, Magnolia) or a colour name into the tool\u2019s search and PaintDial shows every brand\u2019s nearest paints to it. The RAL values come from the standard\u2019s published CIELAB coordinates, and the BS 4800 values from measured colour data (averaged spectrophotometer readings, standardised to D65 / CIE 1964). Both are physical colour standards, so on-screen values are approximate conversions. For anything binding, use an official RAL or British Standard fan deck.</p>
<p>Dulux Trade Colour Palette codes work the same way. Type one off the tin (say, “10RR 73/016”) and PaintDial sets the wheel to that colour, using the value Dulux Trade publishes for it, and tells you when it’s exactly the same colour as a retail Dulux paint, as hundreds of them are.</p>

<h2>Why photo matching is approximate</h2>
<p>The \u201c<a href="/match-paint-from-a-photo/">match from a photo</a>\u201d tool reads the pixel colour from your image. That pixel is shaped by the room\u2019s lighting, the camera\u2019s processing and your screen, so a photo match is a starting point. The same wall photographed at noon and at dusk will match to different paints. Holding a sheet of white paper against the wall when you take the photo helps: tap <b>Correct the light</b>, tap the paper, and the tool scales the photo so the paper comes out white, which takes out most of a bulb\u2019s colour cast and brightens a dark room. It can\u2019t fix mixed lighting or heavy processing by the phone.</p>

<h2>Why you should still order testers</h2>
<p>No screen shows paint exactly, and every screen shows colour a little differently. Real paint also changes with sheen, light and the surface underneath. Before you commit to a colour or a match, get testers of both and look at them in the room they\u2019re for, in daylight and lamplight.</p>

<h2>Common questions</h2>
<div class="faq">
{faq_html}
</div>
{_ldjson(faq_ld)}

<p class="muted">Found something that looks wrong? <a href="/contact/">Tell me</a> and I\u2019ll fix it.</p>"""
    return _page_shell("How PaintDial matches colours",
        "Where PaintDial's colour data comes from, how cross-brand matches are calculated, what the match labels mean, and why you should still order testers.",
        "/how-it-works/", body)

def ink_on(i):
    """Readable text colour over a swatch, from its OKLab lightness."""
    return '#211F1B' if OL[i] > 0.62 else '#FFFFFF'


RESEARCH = {}   # headline figures published by the two studies, read by the hub

def build_match_index_page():
    """The UK Paint Match Index — findings computed live from the library, so the
    page stays true as brands are added. Every colour named links to its page."""
    NEARID, VCLOSE, DEEP = 2.0, 5.0, 0.30
    brands = sorted({p['brand'] for p in paints})
    idx_by_brand = {b: [i for i in range(N) if paints[i]['brand'] == b] for b in brands}
    prem = [i for i in range(N) if TIER[paints[i]['brand']] == 3]
    valb = [b for b in brands if TIER[b] == 1]

    nearest, nearest_k = {}, {}
    for i in prem:
        d = dmatch(i)
        best_all, best_all_k, best_val = 1e9, -1, 1e9
        for b in brands:
            if b == paints[i]['brand']:
                continue
            ii = idx_by_brand[b]
            k = min(ii, key=lambda j: d[j])
            if d[k] < best_all: best_all, best_all_k = d[k], k
            if b in valb: best_val = min(best_val, d[k])
        nearest[i] = (best_all, best_val); nearest_k[i] = best_all_k

    n_id = sum(1 for i in prem if nearest[i][1] < NEARID)
    n_vc = sum(1 for i in prem if nearest[i][1] < VCLOSE)
    pct_id, pct_vc = round(100*n_id/len(prem)), round(100*n_vc/len(prem))

    def sw(i):
        return (f'<a class="pn" href="/colours/{slugs[i]}"><i style="background:{paints[i]["hex"]}"></i>'
                f'{H.escape(paints[i]["name"])}</a>')

    # truest dupes: premium -> value, smallest distance first
    fb_pairs = []
    for i in prem:
        if paints[i]['brand'] != 'Farrow & Ball': continue
        d = dmatch(i); cand = [j for b in valb for j in idx_by_brand[b]]
        k = min(cand, key=lambda j: d[j])
        fb_pairs.append((d[k], i, k))
    fb_pairs.sort()
    def half(j):
        return (f'<a class="pair-half" href="/colours/{slugs[j]}" style="background:{paints[j]["hex"]};color:{ink_on(j)}">'
                f'<span class="pair-lab"><b>{H.escape(paints[j]["name"])}</b>'
                f'<span>{H.escape(paints[j]["brand"])} \u00b7 <span class="hx">{paints[j]["hex"]}</span></span></span></a>')
    dupe_rows = ''.join(
        f'<figure class="pair"><div class="pair-blocks">{half(i)}{half(k)}</div>'
        f'<figcaption>\u0394E {_d:.1f}</figcaption></figure>'
        for _d, i, k in fb_pairs[:4])

    # unmatchable
    uniq = sorted([i for i in prem if nearest[i][0] >= VCLOSE], key=lambda i: -nearest[i][0])
    uniq_rows = ''.join(
        f'<a class="uq" href="/colours/{slugs[i]}" style="background:{paints[i]["hex"]};color:{ink_on(i)}">'
        f'<b>{H.escape(paints[i]["name"])}</b><span>{paints[i]["hex"]}</span>'
        f'<span class="uq-near">nearest: {H.escape(paints[nearest_k[i]]["name"])}</span></a>'
        for i in uniq[:12])
    uniq_brands = Counter(paints[i]['brand'] for i in uniq)

    # depth
    deep = [i for i in range(N) if OL[i] < DEEP]
    deep_c = Counter(paints[i]['brand'] for i in deep)
    deep_rows = ' \u00b7 '.join(f'<b>{H.escape(b)}</b> {n}' for b, n in deep_c.most_common())

    # F&B-likeness per 100
    fb = [i for i in range(N) if paints[i]['brand'] == 'Farrow & Ball']
    wins = Counter()
    for i in fb:
        d = dmatch(i); best, bb = 1e9, None
        for b in brands:
            if b == 'Farrow & Ball': continue
            k = min(idx_by_brand[b], key=lambda j: d[j])
            if d[k] < best: best, bb = d[k], b
        wins[bb] += 1
    per100 = sorted(((b, 100*n/len(idx_by_brand[b]), n, len(idx_by_brand[b])) for b, n in wins.items()),
                    key=lambda r: -r[1])
    _mx = max(v for _b, v, _n, _s in per100) or 1
    fb_rows = ''.join(
        f'<div class="brow"><span class="blab">{H.escape(b)}</span>'
        f'<span class="btrack"><i style="width:{100*v/_mx:.0f}%"></i></span>'
        f'<span class="bval">{v:.1f}</span>'
        f'<span class="bnote">{n} from {sz:,}</span></div>' for b, v, n, sz in per100)

    prem_brands = sorted({paints[i]['brand'] for i in prem})
    # Which brands own the unmatchable colours. This was typed as "all from one brand" and went
    # false when Zoffany arrived (Nov 2026), so every sentence about it is built from the data.
    ub = [b for b, _n in uniq_brands.most_common()]
    ub_names = _and([H.escape(b) for b in ub]) if ub else ''
    ub_split = _and([f'{n} from {H.escape(b)}' for b, n in uniq_brands.most_common()])
    _top, _top_n = uniq_brands.most_common(1)[0] if ub else ('', 0)
    if len(ub) > 1 and _top_n * 2 > len(uniq):
        # One brand owns most of them (Benjamin Moore, Nov 2026): say so, or the headline reads
        # as if the hard-to-match colours were spread across several brands.
        uniq_head = f'{_top_n} of them are {H.escape(_top)}\u2019s.'
        uniq_h2 = f'and {_top_n} of them are {H.escape(_top)}\u2019s'
        uniq_p = f'They come from <b>{ub_names}</b>: {ub_split}.'
    elif len(ub) == 1:
        uniq_head = 'They\u2019re all from one brand.'
        uniq_h2 = 'and they\u2019re all one brand'
        uniq_p = f'Every one belongs to <b>{ub_names}</b>.'
    elif 1 < len(ub) <= 3:
        uniq_head = f'They all come from just {numword(len(ub))} brands.'
        uniq_h2 = f'and they come from just {numword(len(ub))} brands'
        uniq_p = f'They come from <b>{ub_names}</b>: {ub_split}.'
    else:
        uniq_head = ''
        uniq_h2 = f'from {numword(len(ub))} brands'
        uniq_p = f'By brand: {ub_split}.'
    deep_top = [b for b, _n in deep_c.most_common(len(ub))]
    deep_of_ub = sum(deep_c[b] for b in ub)
    if ub and set(deep_top) == set(ub) and deep_of_ub * 2 > len(deep):
        if len(ub) == 1:
            deep_p = (f'{ub_names} makes {deep_of_ub} of those {len(deep)}, '
                      f'which is why its colours are the hard ones to match.')
        else:
            deep_p = (f'{ub_names} make {deep_of_ub} of those {len(deep)}, '
                      f'which is why their colours are the hard ones to match.')
    else:
        deep_p = ''
    RESEARCH['match'] = dict(pct_vc=pct_vc, n_uniq=len(uniq), n_prem=len(prem), n_prem_brands=len(prem_brands),
                             uniq_head=uniq_head, n_uniq_brands=len(ub), deep_story=bool(deep_p))
    body = f"""<span class="eyebrow">Research \u00b7 The UK Paint Match Index</span>
<h1>Only {len(uniq)} of the {len(prem):,} premium paint colours from {numword(len(prem_brands))} brands sold in the UK can\u2019t be matched. {uniq_head}</h1>
<p>I compared every one of the {N:,} colours published by {len(brands)} paint brands sold in the UK against every other, millions of comparisons in all, to see how many premium paint colours already have a near-identical twin and how many are unique.</p>
<p class="muted">Updated automatically from PaintDial\u2019s live colour library. Last built {TODAY}.</p>

<h2>1. Almost every premium colour has a close alternative</h2>
<p class="bignum">{pct_vc}%<small>of premium colours have at least a very close match from a value brand</small></p>
<p><b>{pct_id}%</b> of premium colours ({n_id} of {len(prem)}) have a <b>near-identical</b> match from a value brand. <b>{pct_vc}%</b> ({n_vc}) have at least a <b>very close</b> one.</p>
<p>So if you want a premium colour, there\u2019s a {pct_vc}% chance another brand makes something very close to it. <a href="/">Check any colour in the tool \u2192</a></p>

<h2>2. The closest pairs differ by a single step in their hex code</h2>
{dupe_rows}

<h2>3. Only {len(uniq)} premium colours can\u2019t be matched, {uniq_h2}</h2>
<p>Of {len(prem):,} premium colours, just <b>{len(uniq)}</b> have no very-close match from any other brand. {uniq_p}</p>
<div class="uq-grid">{uniq_rows}</div>

<h2>4. {"Why: hardly any paints go that dark" if deep_p else "Hardly any paints go very dark"}</h2>
<p class="bignum">{len(deep)} of {N:,}<small>colours across all {len(brands)} brands are very deep</small></p>
<p>Only <b>{len(deep)} of {N:,}</b> colours across all {len(brands)} brands are very deep. By brand: {deep_rows}.</p>
<p>{deep_p}</p>

<h2>5. Whose palette is most Farrow &amp; Ball-like?</h2>
<p>Raw counts favour whoever publishes most colours. Corrected for range size (wins per 100 colours in each brand\u2019s range):</p>
<div class="bars">{fb_rows}</div>
<p><a href="/dupes/farrow-and-ball">See every Farrow &amp; Ball colour\u2019s closest match \u2192</a></p>

<h2>Method</h2>
<p>Every colour is each brand\u2019s <a href="/how-it-works/">own published digital swatch</a>{source_short()}. I don\u2019t photograph or estimate any colours. Differences are computed in <b>OKLab</b>, weighting hue drift twice and discounting lightness, because a paint a shade lighter still reads as the same colour while one that\u2019s drifted in hue reads as a different one. Thresholds are the ones used across the site: near-identical = \u0394E&nbsp;&lt;&nbsp;2, very close = \u0394E&nbsp;&lt;&nbsp;5. \u201cVery deep\u201d means OKLab lightness below {DEEP}.</p>

<h2>What this doesn\u2019t claim</h2>
<ul>
<li><b>No prices in this study.</b> \u201cValue brand\u201d means market tier.</li>
<li><b>On screen only.</b> These are digital swatch comparisons. Real paint varies with finish, pigment and light, so a near-identical hex is somewhere to start. Always order testers.</li>
<li><b>Range sizes differ enormously</b> ({max(len(v) for v in idx_by_brand.values()):,} colours vs {min(len(v) for v in idx_by_brand.values())}). Every brand-level claim here is corrected for that.</li>
<li><b>Published ranges only.</b> Mix-to-order and bespoke matching are excluded.</li>
<li><b>These {len(brands)} brands only.</b> The library holds every brand that publishes a colour value for each paint; ranges that publish only photographs are left out rather than guessed at.</li>
</ul>
<p class="muted">Companion study: <a href="/paint-choice-index/">The UK Paint Choice Index</a>, on how many of these colours are actually different. Journalists and researchers: the underlying comparisons are all on the site, colour by colour. Questions or corrections: <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("The UK Paint Match Index",
        f"I compared {N:,} paint colours from {len(brands)} brands sold in the UK. {pct_vc}% of premium colours have a very close match from another brand, and only {len(uniq)} can\u2019t be matched at all.",
        "/paint-match-index/", body, layout="split")


def build_choice_index_page():
    """The UK Paint Choice Index — how much choice British paint actually offers.
    Every figure computed live from the library at build time; thresholds are the
    site's own published ones (near-identical dE<2, very close dE<5) and the site's
    own live family classification. Verified 15 Jul 2026: clustering robust across
    orderings (0.6% spread); dE<1-based per-brand 'pair' figures from earlier drafts
    were rejected as off-threshold and are NOT used here."""
    NEARID, VCLOSE = 2.0, 5.0
    brands = sorted({p['brand'] for p in paints})

    # --- 1. distinct-colour clustering (greedy dominating set, 5 seeded orderings) ---
    counts = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        order = rng.permutation(N)
        taken = np.zeros(N, bool); reps = 0
        for i in order:
            if taken[i]: continue
            reps += 1; taken[i] = True
            taken |= (dmatch(i) < NEARID)
        counts.append(reps)
    distinct = round(sum(counts)/len(counts))
    dup_pct = round(100*(1 - distinct/N))

    # --- twin stats (cluster-free) + per-brand internal twins + exact hexes ---
    twin_any = 0; twin_cross = 0
    twin_inbrand = Counter(); brand_n = Counter(p['brand'] for p in paints)
    BR_ = [p['brand'] for p in paints]
    for i in range(N):
        d = dmatch(i); d[i] = 1e9
        m = d < NEARID
        if m.any(): twin_any += 1
        hit_cross = hit_in = False
        for j in np.where(m)[0]:
            if BR_[j] == BR_[i]: hit_in = True
            else: hit_cross = True
        if hit_cross: twin_cross += 1
        if hit_in: twin_inbrand[BR_[i]] += 1
    exact = Counter()
    hex_groups = {}
    for b in brands:
        hc = Counter(p['hex'].upper() for p in paints if p['brand'] == b)
        exact[b] = sum(v for v in hc.values() if v > 1)
        for h_, v in hc.items():
            if v > 1: hex_groups.setdefault(b, []).append((h_, v))
    exact_total = sum(exact.values())

    def sw(i):
        return (f'<a class="pn" href="/colours/{slugs[i]}"><i style="background:{paints[i]["hex"]}"></i>'
                f'{H.escape(paints[i]["name"])}</a>')
    def half(j, note=''):
        return (f'<a class="pair-half" href="/colours/{slugs[j]}" style="background:{paints[j]["hex"]};color:{ink_on(j)}">'
                f'<span class="pair-lab"><b>{H.escape(paints[j]["name"])}</b>'
                f'<span>{H.escape(paints[j]["brand"])} \u00b7 <span class="hx">{paints[j]["hex"]}</span>{note}</span></span></a>')

    # exact-hex showcase pairs: Craig & Rose pair + Dulux's biggest same-hex group
    def find(brand, name):
        return next(i for i in range(N) if paints[i]['brand'] == brand and paints[i]['name'] == name)
    showcase = ''
    try:
        cr1, cr2 = find('Craig & Rose', 'Regency White'), find('Craig & Rose', 'Isabelline')
        showcase += (f'<figure class="pair"><div class="pair-blocks">{half(cr1)}{half(cr2)}</div>'
                     f'<figcaption>Two Craig &amp; Rose colours, one published value: {paints[cr1]["hex"]}.</figcaption></figure>')
    except StopIteration:
        pass
    du = [(h_, v) for h_, v in hex_groups.get('Dulux', [])]
    if du:
        bigh = max(du, key=lambda t: t[1])[0]
        group = [i for i in range(N) if paints[i]['brand'] == 'Dulux' and paints[i]['hex'].upper() == bigh][:4]
        if len(group) >= 3:
            showcase += (f'<figure class="pair"><div class="pair-blocks">{"".join(half(j) for j in group)}</div>'
                         f'<figcaption>{len(group)} Dulux names, one published value: {bigh}.</figcaption></figure>')

    inb_rows = ''.join(
        f'<div class="brow"><span class="blab">{H.escape(b)}</span>'
        f'<span class="btrack"><i style="width:{100*twin_inbrand[b]/brand_n[b]/max(twin_inbrand[bb]/brand_n[bb] for bb in brands):.0f}%"></i></span>'
        f'<span class="bval">{100*twin_inbrand[b]/brand_n[b]:.0f}%</span>'
        f'<span class="bnote">{twin_inbrand[b]:,} of {brand_n[b]:,}</span></div>'
        for b in sorted(brands, key=lambda b: -twin_inbrand[b]/brand_n[b]))

    # --- 2. family split (the site's own classification) ---
    # NOTE (17 Jul 2026): the "about half of British paint is a neutral" finding was PULLED.
    # It rested on family()'s neutral gate, which used flat chroma thresholds and wrongly
    # swept pale-but-clearly-coloured paints into Whites & neutrals (Little Greene's Sky Blue,
    # C=0.043, was classed neutral -- it uses 35% of the chroma physically available at its
    # lightness and hue). A gate fitted against brand naming puts the true neutral share near
    # 34%, not 53% -- a 19-point error. Do NOT republish any neutral statistic until the gate
    # is rebuilt and cross-validated. Findings 1-3 and 5 do not depend on the neutral gate.


    # --- 3. how far paint pushes chroma, by hue (bands from the shared HUE_EDGES) ---
    _E = HUE_EDGES
    reds_m = (OH < _E[0]) | (OH >= _E[6])
    purp_m = (OH >= _E[5]) & (OH < _E[6])
    red_max = float(OC[reds_m].max()); purp_max = float(OC[purp_m].max())
    red_vivid = int((OC[reds_m] > 0.10).sum()); purp_vivid = int((OC[purp_m] > 0.10).sum())

    # --- 4. gamut coverage at the site's own thresholds ---
    A1 = np.array([[0.4122214708,0.5363325363,0.0514459929],
                   [0.2119034982,0.6806995451,0.1073969566],
                   [0.0883024619,0.2817188376,0.6299787005]])
    A2 = np.array([[0.2104542553,0.7936177850,-0.0040720468],
                   [1.9779984951,-2.4285922050,0.4505937099],
                   [0.0259040371,0.7827717662,-0.8086757660]])
    A1i, A2i = np.linalg.inv(A1), np.linalg.inv(A2)
    rng = np.random.default_rng(7)
    pts = []
    while len(pts) < 40000:
        cand = rng.uniform([0,-0.4,-0.4],[1,0.4,0.4], size=(20000,3))
        lms = (cand @ A2i.T)**3
        rgb = lms @ A1i.T
        ok = np.all((rgb >= -1e-9) & (rgb <= 1+1e-9), axis=1)
        pts.extend(cand[ok].tolist())
    P = np.array(pts[:40000])
    SL, SA, SB = P[:,0], P[:,1], P[:,2]
    SC = np.hypot(SA, SB); SH = np.degrees(np.arctan2(SB, SA)) % 360
    mind = np.full(len(P), 1e9)
    for i in range(N):
        dL = (SL-OL[i])/1.3; dC = SC-OC[i]
        dh_ = np.abs(SH-OH[i]) % 360; dh_ = np.where(dh_ > 180, 360-dh_, dh_)
        dH = 2*np.sqrt(np.maximum(SC*OC[i], 0))*np.sin(np.radians(dh_)/2)
        np.minimum(mind, 190*np.sqrt(dL*dL + dC*dC + 4*dH*dH), out=mind)
    cover_pct = round(100*(mind < VCLOSE).mean())
    unc = mind >= VCLOSE
    unc_purple = round(100*(((SH >= _E[5]) & (SH < _E[6])) & unc).sum()/unc.sum())
    unc_blue = round(100*(((SH >= _E[4]) & (SH < _E[5])) & unc).sum()/unc.sum())
    unc_pink = round(100*(((SH >= _E[6]) | (SH < _E[0])) & unc).sum()/unc.sum())

    RESEARCH['choice'] = dict(distinct=distinct, dup_pct=dup_pct, exact_total=exact_total, purp_vivid=purp_vivid)
    # The peak-chroma contrast held at 9-15 brands (purple stopped at under half red's peak) but not
    # once Valspar's full range went in (Nov 2026: 0.20 vs 0.21), so it is only claimed when true.
    if purp_max < red_max / 2:
        purp_peak_line = f'red reaches a peak chroma of {red_max:.2f}, but purple stops at {purp_max:.2f}, less than half.'
    else:
        purp_peak_line = (f'the most saturated purple (chroma {purp_max:.2f}) gets close to the most saturated red ({red_max:.2f}), '
                          f'but almost nothing else does.')
    purp_count_line = 'Exactly one purple does.' if purp_vivid == 1 else f'Only {purp_vivid} purples do.'
    dup_head = ('Half of these colours are duplicates' if 45 <= dup_pct <= 55 else
                'More than half of these colours are duplicates' if dup_pct > 55 else
                f'{dup_pct}% of these colours are duplicates')
    body = f"""<span class="eyebrow">Research \u00b7 The UK Paint Choice Index</span>
<h1>{numword(len(brands)).capitalize()} paint brands on the UK market sell {N:,} colours between them. Only {distinct:,} are actually different.</h1>
<p>The {len(brands)} brands in PaintDial’s library ({brand_list()}) publish {N:,} colours between them. This study looks at how many of them are actually different. It covers those brands only: own-label ranges that publish no colour values aren’t in the library, so they aren’t in these figures.</p>
<p class="muted">Computed automatically from PaintDial\u2019s live colour library, using the same thresholds as every page on this site. Last built {TODAY}.</p>

<h2>1. {dup_head}</h2>
<p class="bignum">{distinct:,} of {N:,}<small>colours are actually different at the site’s near-identical threshold</small></p>
<p>You could remove <b>{dup_pct}%</b> of the colours these {len(brands)} brands sell and every one removed would still have a near-identical match among the survivors. Without any clustering at all: <b>{round(100*twin_any/N)}%</b> of colours have a near-identical twin somewhere in the library, and <b>{round(100*twin_cross/N)}%</b> have one from a <em>different brand</em>. <a href="/">Check any colour\u2019s twins in the tool \u2192</a></p>

<h2>2. {exact_total} colours share an exact value with a sibling from their own brand</h2>
<p>These pairs share exactly the same published value, under two names, from the same brand:</p>
{showcase}
<p class="muted">Dulux accounts for most of these: {len(hex_groups.get('Dulux', []))} of its published values appear under more than one name.</p>

<h2>3. Inside the biggest ranges, most colours have an in-house twin</h2>
<p>Share of each brand\u2019s own range with a near-identical twin <em>from the same brand</em>:</p>
<div class="bars">{inb_rows}</div>
<p>Bigger ranges duplicate more. Partly that\u2019s arithmetic: publish {max(brand_n.values()):,} colours into a finite space and some will overlap. It does mean a bigger colour card isn\u2019t proportionally more choice.</p>

<h2>4. The colour these brands don\u2019t sell</h2>
<p class="bignum">{cover_pct}%<small>of the colours a screen can show have a very close paint in the library</small></p>
<p>Take every colour a standard screen can display and ask: does any paint in the library come <b>very close</b> to it (the site-wide \u0394E&nbsp;&lt;&nbsp;5)? The answer is yes for just <b>{cover_pct}%</b> of them. The missing colours aren\u2019t evenly spread: they sit overwhelmingly at the vivid end of <b>purple ({unc_purple}% of the gap), blue ({unc_blue}%) and the reds and pinks ({unc_pink}%)</b>.</p>
<p>Some of that is physics, because a screen gives off light and paint can\u2019t, so no paint will match a glowing violet. The pattern still holds within paint alone: across these {len(brands)} brands, {purp_peak_line} <b>{red_vivid} red paints exceed a chroma of 0.10. {purp_count_line}</b></p>

<h2>Method</h2>
<p>Every colour is each brand\u2019s <a href="/how-it-works/">own published digital swatch</a>{source_short()}. Distinctness uses greedy clustering at the site\u2019s published near-identical threshold (\u0394E&nbsp;&lt;&nbsp;2 in the site’s hue-weighted OKLab metric), averaged over five seeded random orderings; the spread across orderings is about 1%, so the count is not an artefact of ordering. Colour families come from the site\u2019s own classification, the same rule that files every colour in the <a href="/colours/">library</a>. Screen-colour coverage samples the sRGB gamut uniformly in OKLab volume (40,000 seeded points) and measures distance to the nearest paint with the site\u2019s own metric and thresholds.</p>

<h2>What this doesn\u2019t claim</h2>
<ul>
<li><b>Swatch values only.</b> Brands may distinguish colours in ways a swatch value doesn\u2019t capture, such as finish, texture or opacity. Two identical values are identical <em>on screen</em>.</li>
<li><b>This isn’t a criticism of the brands.</b> Much of it is arithmetic (large ranges in a finite colour space), and some may be deliberate continuity across renamed ranges.</li>
<li><b>Some colours are out of reach for paint.</b> Some of the \u201cmissing\u201d colour in finding 4 is physically out of reach for any paint. The red-versus-purple contrast, measured within paint alone, does not depend on that comparison.</li>
<li><b>No prices in this study.</b></li>
<li><b>These {len(brands)} brands only.</b> The library holds every brand that publishes a colour value for each paint. Own-label and other ranges that publish only photographs are left out rather than guessed at, so the UK total is higher than {N:,}.</li>
</ul>
<p class="muted">Companion study: <a href="/paint-match-index/">The UK Paint Match Index</a>, on how closely premium colours can be matched across brands. Questions or corrections: <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("The UK Paint Choice Index",
        f"{numword(len(brands)).capitalize()} paint brands on the UK market sell {N:,} colours between them. Only {distinct:,} are actually different, and just {purp_vivid} {'purple is' if purp_vivid == 1 else 'purples are'} vivid.",
        "/paint-choice-index/", body, layout="split")


def build_research_hub():
    brands = sorted({p['brand'] for p in paints})
    _rm, _rc = RESEARCH['match'], RESEARCH['choice']
    _one = _rm['n_uniq_brands'] == 1
    _rm_deep = (' The ones that can\u2019t be matched are the very dark colours.' if _rm['deep_story'] else '')
    _rc_purp = ('only one of them is a vivid purple' if _rc['purp_vivid'] == 1
                else f'only {_rc["purp_vivid"]} of them are vivid purples')
    body = f"""<span class="eyebrow">PaintDial</span>
<h1>Research</h1>
<p>Original studies computed from PaintDial\u2019s live library of {N:,} colours across {len(brands)} brands sold in the UK, compared with the same metric and thresholds used on every page of this site. Each study rebuilds automatically as brands are added.</p>
<div class="rsch-cards">
<a class="rsch-card" href="/paint-match-index/"><small>The UK Paint Match Index</small><b>Only {_rm['n_uniq']} of the {_rm['n_prem']:,} premium paint colours from {numword(_rm['n_prem_brands'])} brands sold in the UK can\u2019t be matched. {_rm['uniq_head']}</b><span>{_rm['pct_vc']}% of premium colours have a very close match from a value brand.{_rm_deep}</span></a>
<a class="rsch-card" href="/paint-choice-index/"><small>The UK Paint Choice Index</small><b>{numword(len(brands)).capitalize()} paint brands on the UK market sell {N:,} colours between them. Only {_rc['distinct']:,} are actually different.</b><span>{_rc['dup_pct']}% of them are near-identical duplicates, {_rc['exact_total']} colours share an exact value with a sibling from their own range, and {_rc_purp}.</span></a>
</div>
<p class="muted">Journalists and researchers: every underlying comparison is public, colour by colour, across the site. Questions or corrections: <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("Research", 
        f"Original colour research computed from {N:,} UK paint colours across {len(brands)} brands.",
        "/research/", body)


def _about_values_line():
    # "The colour values are the ones each brand publishes, apart from ..." in the About page's
    # own first-person wording. Built from SOURCE_NOTE so it stays right as brands change.
    base = 'The colour values are the ones each brand publishes'
    if not SOURCE_NOTE and not SWATCH_SAMPLED:
        return base + '.'
    bits = []
    sw = [H.escape(b) for b in _swatch_brands()]
    if len(sw) == 1:
        bits.append(f'{sw[0]}, which doesn’t publish any, so I read them from the swatch images on '
                    f'<a href="{SWATCH_SAMPLED[_swatch_brands()[0]]}" rel="nofollow noopener" target="_blank">its own site</a>')
    elif sw:
        bits.append(f'{_and(sw)}, which don’t publish any, so I read them from the swatch images on their own sites{_swatch_links()}')
    for stockist, brands in _by_stockist().items():
        url = SOURCE_NOTE[brands[0]][1] if len(brands) == 1 else STOCKIST_HOME.get(stockist, SOURCE_NOTE[brands[0]][1])
        link = f'<a href="{url}" rel="nofollow noopener" target="_blank">{stockist}</a>'
        names = [H.escape(b) for b in brands]
        if len(names) == 1:
            bits.append(f'{names[0]}, which doesn’t publish any, so I use the values its main stockist {link} publishes')
        else:
            joined = ', '.join(names[:-1]) + ' and ' + names[-1]
            bits.append(f'{joined}, which don’t publish any, so I use the values their main stockist {link} publishes')
    return base + ', apart from ' + '; and '.join(bits) + '.'


def build_about_page():
    body = f"""<span class="eyebrow">About</span>
<h1>About PaintDial</h1>
<!--sec-->
<p>I made PaintDial as a result of doing a full house renovation and being frustrated by the mission of trying to find the right paint. I didn’t want to be restricted to just one brand, and I wanted to be able to easily find different shades of colours I liked.</p>
<p>I work in visual effects, so getting colour to match between cameras and screens is my day job. PaintDial is just me, in my spare time, and no paint brand owns or sponsors it.</p>

<h2>Who pays for it</h2>
<p>At the moment it’s paid for by me, plus the odd coffee people have bought me on <a href="https://ko-fi.com/paintdial" target="_blank" rel="noopener">Ko-fi</a>. Some of the tester buttons are affiliate links, so I get a small commission if you buy through one, at no extra cost to you. Those buttons say so underneath. There are no ads, and no brand can pay to move up the rankings, which are worked out from the colour values alone.</p>
{kofi_block()}

<h2>Where the colours come from</h2>
<p>{_about_values_line()} A screen only gets you so close, so get a tester before you paint a wall.</p>

<p>I answer the <a href="/contact/">contact form</a> myself, so if something looks wrong, tell me.</p>"""
    return _page_shell("About PaintDial",
        f"PaintDial is a one-person site comparing {N:,} paints across {NBRANDS} brands sold in the UK. Why I made it and how it’s paid for.",
        "/about/", body)


def build_privacy_page():
    body = """<span class="eyebrow">Privacy</span>
<h1>Privacy</h1>
<!--sec-->
<p>PaintDial is run by me, Will Phillips. There are no accounts and no adverts, and I don’t sell or pass on anything about the people who use it. This page lists what the site does collect.</p>

<h2>Visitor statistics</h2>
<p>I use two tools to see how the site is used. Cloudflare Web Analytics counts page views without cookies and without identifying you. Microsoft Clarity records how pages are used (clicks, scrolling and movement around the page) so I can see where the site is confusing; it is set up to run without cookies, and Microsoft processes that data for me. Neither tells me who you are.</p>

<h2>Things saved in your browser</h2>
<p>Your shortlist, the brands you’ve switched off and any scheme you make in the colour scheme planner are saved in your own browser so they are still there next time. They stay on your device and are never sent to me. Clearing your browser’s site data removes them. If you copy a link to a scheme, the room names and colours are in the link itself, so whoever you send it to can see them.</p>

<h2>Photos</h2>
<p>Photos you use in the photo match or the visualiser stay on your device. The work is done in your browser and the photo isn’t uploaded.</p>

<h2>The contact form</h2>
<p>If you send a message, I get your name, email address and what you wrote. The form is handled by Netlify, which hosts the site, and the message arrives in my email. I use it to reply to you and for nothing else. There is no mailing list.</p>

<h2>Links to shops</h2>
<p>Buttons that take you to a brand or retailer open their site, which has its own privacy policy. Some are affiliate links through Awin: if you buy after following one, Awin records that the sale came from PaintDial so I can be paid a commission. I’m never told who bought what.</p>

<h2>Fonts</h2>
<p>The site’s fonts load from Google Fonts, so your browser makes a request to Google when a page loads.</p>

<h2>Asking about your data</h2>
<p>If you’ve sent me a message and want it deleted, or have any question about this page, email <a href="mailto:hello@paintdial.co.uk">hello@paintdial.co.uk</a>.</p>"""
    return _page_shell("Privacy",
        "What PaintDial collects and what it doesn’t: visitor statistics, what is saved in your browser, photos, the contact form and affiliate links.",
        "/privacy/", body)


def build_contact_page():
    body = f"""<style>
.cf{{max-width:560px;margin-top:18px}}
.cf label{{display:block;font-family:var(--sans);font-size:13px;font-weight:600;margin:16px 0 5px}}
.cf input,.cf select,.cf textarea{{width:100%;box-sizing:border-box;font:inherit;font-size:15px;padding:10px 12px;border:1px solid #D9D4C8;border-radius:8px;background:#fff;color:var(--ink)}}
.cf textarea{{min-height:150px;resize:vertical}}
.cf input:focus,.cf select:focus,.cf textarea:focus{{outline:none;border-color:var(--pc);box-shadow:0 0 0 3px rgba(94,126,139,.18)}}
.cf button{{margin-top:18px;border:none;background:var(--pc);color:#fff;font:inherit;font-size:15px;font-weight:600;padding:12px 26px;border-radius:8px;cursor:pointer}}
.cf button:hover{{filter:brightness(1.06)}}
.cf .hp{{position:absolute;left:-9999px}}
.cf-note{{font-size:13px;color:var(--muted);margin-top:10px}}
</style>
<span class="eyebrow">Contact</span>
<h1>Get in touch</h1>
<!--sec-->
<p>PaintDial is run by one person, so messages come to me directly and I read all of them. Corrections are the most useful thing you can send: if a colour looks wrong, a match seems off, or a brand link goes somewhere odd, tell me and I will check the source data.</p>
<p>Journalists and researchers using the <a href="/paint-match-index/">Match Index</a> or <a href="/paint-choice-index/">Choice Index</a> are welcome to ask about method or request the underlying figures. If you’re a brand or retailer, you’re welcome to get in touch about your colour data or links. The rankings are worked out from the colour values alone.</p>

<p>You can use the form below, or email me at <a href="mailto:hello@paintdial.co.uk">hello@paintdial.co.uk</a>.</p>

<!--sec-->
<form class="cf" name="contact" method="POST" action="/contact/thanks/" data-netlify="true" netlify-honeypot="website">
  <input type="hidden" name="form-name" value="contact">
  <p class="hp"><label>Leave this empty <input name="website" tabindex="-1" autocomplete="off"></label></p>
  <label for="cf-name">Your name</label>
  <input id="cf-name" name="name" type="text" autocomplete="name" required>
  <label for="cf-email">Email, so I can reply</label>
  <input id="cf-email" name="email" type="email" autocomplete="email" required>
  <label for="cf-topic">What is it about?</label>
  <select id="cf-topic" name="topic">
    <option>A correction or something that looks wrong</option>
    <option>A question about how matching works</option>
    <option>Press or research</option>
    <option>Brand, retailer or data enquiry</option>
    <option>Something else</option>
  </select>
  <label for="cf-msg">Message</label>
  <textarea id="cf-msg" name="message" required placeholder="If it is about a specific colour, include the brand and colour name and I can find it straight away."></textarea>
  <button type="submit">Send message</button>
  <p class="cf-note">Replies usually take a few days. Your details are used only to answer you; PaintDial keeps no mailing list.</p>
</form>
<!--sec-->
{kofi_block()}

<p class="muted" style="margin-top:34px">Not a message, just a question about the site? The <a href="/how-it-works/">how it works</a> page covers the data, the matching and the labels, and <a href="/about/">about</a> covers who runs it and how it is funded.</p>"""
    return _page_shell("Contact PaintDial",
        "Send a correction, ask about the matching or the Match Index, or get in touch as a brand, retailer or journalist. PaintDial is one person, and I read every message.",
        "/contact/", body)


def build_contact_thanks_page():
    body = """<span class="eyebrow">Contact</span>
<h1>Thanks, got it</h1>
<p>Your message has been sent. I will reply by email, usually within a few days.</p>
<p class="muted">In the meantime: <a href="/">back to the colour tool</a> or <a href="/colours/">browse the library</a>.</p>"""
    return _page_shell("Message sent", "Your message to PaintDial has been sent.", "/contact/thanks/", body,
                       head='<meta name="robots" content="noindex">')


def build_photo_match_page():
    faqs = [
        ("Can you really match paint from a photo?",
         f"Yes. Upload any photo, tap the colour you want, and PaintDial compares it against all {N:,} paints in the library, then ranks the closest match from every brand."),
        ("How accurate is matching paint from a photo?",
         "As accurate as your photo. A well-lit shot in daylight gives a close shortlist; a photo taken under a warm bulb or in a dark room will drift a long way. Holding a sheet of white paper against the wall and using Correct the light takes most of that out, but it can't fix mixed lighting or a phone's own heavy processing. Treat any match as a starting point and always order a tester pot."),
        ("Can I match a colour from a fabric, tile or wallpaper?",
         "Yes. Anything in a photo works: a fabric, a cushion, a tile, a flower, even a room you screenshotted."),
        ("Is it free?",
         "Completely free. There’s no app to install and no account to create; it runs in your browser."),
    ]
    faq_html = "".join(f'<div class="pm-q"><b>{q}</b><p>{a}</p></div>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication",
              "name": "PaintDial: match paint from a photo",
              "url": f"{DOMAIN}/match-paint-from-a-photo/",
              "applicationCategory": "UtilitiesApplication", "operatingSystem": "Web",
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "GBP"},
              "description": f"Upload a photo and find the closest paint colour from {BRANDS_WORD} brands sold in the UK."}
    body = f"""<style>
.pm-hero{{display:grid;grid-template-columns:1fr 360px;gap:36px;align-items:start;margin:8px 0 6px}}
.pm-diff{{background:#eef1f0;border-left:3px solid var(--pc);border-radius:0 8px 8px 0;padding:13px 16px;font-size:15px;margin-top:14px}}
.pm-up{{background:#fff;border:2px dashed #c9c3b5;border-radius:14px;padding:30px 22px;text-align:center;box-shadow:0 2px 10px rgba(33,31,27,.05)}}
.pm-cta{{display:inline-block;background:var(--pc);color:#fff;font-weight:600;font-size:15px;padding:12px 26px;border-radius:8px;text-decoration:none;margin:10px 0 4px}}
.pm-up small{{display:block;color:var(--muted);font-size:13px;margin-top:6px}}
.pm-eg{{margin-top:14px;background:#fff;border:1px solid var(--hairline);border-radius:14px;padding:12px;display:flex;align-items:center;gap:11px}}
.pm-thumb{{width:60px;height:60px;border-radius:8px;background:linear-gradient(135deg,#3d4e57,#5e7e8b);flex:none}}
.pm-arrow{{color:var(--muted);font-size:18px}}
.pm-chips{{display:flex;gap:7px}}
.pm-chip{{font-size:10px;text-align:left}}
.pm-sw{{width:40px;height:32px;border-radius:8px;margin-bottom:3px;display:block}}
.pm-chip b{{font-family:var(--serif);font-size:11px;display:block}}
.pm-chip span.pm-br{{color:var(--muted);text-transform:uppercase;letter-spacing:.04em;font-size:8.5px}}
.pm-q{{border-bottom:1px solid var(--hairline);padding:14px 0}}
.pm-q b{{font-family:var(--serif);font-size:16px;display:block;margin-bottom:3px}}
.pm-q p{{margin:0}}
@media(max-width:720px){{.pm-hero{{grid-template-columns:1fr;gap:20px}}.pm-hero>div:last-child{{order:-1}}}}
</style>
<span class="eyebrow">Free colour tool</span>
<h1>Match a paint colour from a photo</h1>
<div class="pm-hero">
<div>
<p>Upload a photo of a wall, a fabric or anything else, tap the colour you want, and see the closest paint from every brand side by side. It’s free and runs in your browser.</p>
</div>
<div>
<div class="pm-up"><div style="font-family:var(--serif);font-size:19px;font-weight:600">Match from a photo</div><a class="pm-cta" href="/#photoBtn">Upload a photo</a><small>or take one on your phone · free · no sign-up</small></div>
<div class="pm-eg"><div class="pm-thumb"></div><span class="pm-arrow">→</span><div class="pm-chips"><div class="pm-chip"><span class="pm-sw" style="background:#3D4E57"></span><b>Hague Blue</b><span class="pm-br">F&amp;B</span></div><div class="pm-chip"><span class="pm-sw" style="background:#3b4b54"></span><b>The Drink</b><span class="pm-br">COAT</span></div><div class="pm-chip"><span class="pm-sw" style="background:#3e4f59"></span><b>Blue 07</b><span class="pm-br">Lick</span></div></div></div>
</div>
</div>

<h2>How it works</h2>
<div class="rsch-cards">
<div class="rsch-card"><b>1. Upload a photo</b><span>Any image: a painted wall, a cushion, a photo you saved from Pinterest.</span></div>
<div class="rsch-card"><b>2. Tap the colour</b><span>Point at the exact spot; PaintDial reads the colour under your finger.</span></div>
<div class="rsch-card"><b>3. See every brand</b><span>The closest paint from {BRANDS_WORD} brands sold in the UK, ranked, with how close each one is.</span></div>
</div>

<h2>Getting the best match</h2>
<ul>
<li>Shoot in <b>natural daylight</b>. Flash and warm bulbs shift the colour.</li>
<li>Indoors or under lamps, <b>hold a sheet of white paper against the wall</b> when you take the photo. Then tap <b>Correct the light</b> and tap the paper, and PaintDial takes out the colour cast and brightens a dark photo before you pick the wall.</li>
<li><b>Fill the frame</b> with the colour you want, and avoid shadows and glare.</li>
<li>A photo of a <b>screen</b> drifts from real paint, so use the real surface where you can.</li>
<li>Treat a match as a <b>shortlist</b> and order a tester pot before you commit.</li>
</ul>

<h2>Compared with a brand’s own photo tool</h2>
<p>Dulux’s and Valspar’s photo tools only show you <em>their</em> paints. PaintDial compares your colour across {BRANDS_WORD} brands sold in the UK at once, including Farrow &amp; Ball, Little Greene, Dulux and Johnstone’s, so you see every close option side by side. It uses the same <a href="/how-it-works/">matching</a> as the rest of the site.</p>

<h2>Common questions</h2>
{faq_html}

<p class="muted" style="margin-top:20px"><a class="pm-cta" href="/#photoBtn" style="color:#fff">Match a colour from a photo →</a></p>
{_ldjson(app_ld, faq_ld)}"""
    return _page_shell(f"Match Paint From a Photo — {NBRANDS} Brands Sold in the UK",
        f"Upload a photo and get the closest paint from {BRANDS_WORD} brands sold in the UK, including Farrow & Ball, Dulux and Little Greene. Free, in your browser, with no app or sign-up.",
        "/match-paint-from-a-photo/", body)


# ---------- paint visualiser (/paint-visualiser/) ----------
# Paint a wall in your own photo with any paint in the library, next to its closest match
# from another brand. The tool is visualiser/tool.html (styles scoped under #pv) plus
# vis-core.js, vis-wheel.js and sam-worker.js; everything runs in the browser and the photo
# is never uploaded. The wall finder (SlimSAM, via Transformers.js) downloads once from
# Hugging Face. Tried on a separate test site first (paintdial-visualiser.netlify.app);
# Will put it live on 10 Nov 2026. Colour pages link here with ?c=<slug>, the compare view
# with ?c=&vs=, and the homepage with ?hex= (the nearest paint to the wheel's colour).
VIS_PATH = '/paint-visualiser/'
VIS_FILES = ['vis-core.js', 'vis-wheel.js', 'sam-worker.js', 'example-room.jpg', 'example-room-wall.png']

def visualiser_data():
    """The library for the visualiser, in paints.json order. The page works out each colour's
    slug itself with the same rules as base_slug() and the de-duplication above, so links
    to /colours/ line up (checked for every colour when it was built)."""
    bi = {b: i for i, b in enumerate(BRAND_ORDER)}
    rows = []
    for p in paints:
        hx = p['hex'].strip()
        assert re.fullmatch(r'#[0-9A-Fa-f]{6}', hx), f"bad hex for the visualiser: {p}"
        rows.append([bi[p['brand']], p['name'], hx[1:].upper(), p.get('code') or ''])
    return {'brands': BRAND_ORDER,
            'sourced': {b: s for b, (s, _u) in SOURCE_NOTE.items()},
            'swatched': [b for b in BRAND_ORDER if b in SWATCH_SAMPLED],
            'c': rows}

def build_visualiser_page():
    # The heading and intro sit inside the tool's grid (right-hand column on a computer, above
    # the photo on a phone), so the photo can start right under the site header.
    lead = ('<span class="eyebrow">Paint visualiser</span>'
            '<h1>See a paint colour on your own wall</h1>'
            f'<p>Take a photo of your room, tap the wall and try any of {N:,} paints from {BRANDS_WORD} brands '
            'sold in the UK on it. The closest match from another brand goes on the other half of the wall, '
            'so you can see the two side by side.</p>')
    tool = open('visualiser/tool.html', encoding='utf-8').read()
    assert tool.count('<!--PV-LEAD-->') == 1, 'visualiser/tool.html has lost its <!--PV-LEAD--> placeholder'
    tool = tool.replace('<!--PV-LEAD-->', lead)
    faqs = [
        ("Is my photo uploaded?",
         "No. Everything happens in your browser, on your phone or computer. The photo isn’t sent anywhere."),
        ("How accurate is the colour?",
         "The wall is painted so that it averages out at the paint’s published colour, with the light and shade from your photo on top. Screens vary and paint changes with the light in your room, so use it to narrow things down and get a tester before you buy."),
        ("Which paints can I try?",
         f"Any of the {N:,} paints in the library, from {BRANDS_WORD} brands sold in the UK. Search by name or code, or use the colour wheel, and the closest match from another brand goes on the other half of the wall."),
        ("Why has it missed part of my wall, or painted something it shouldn’t?",
         "It works out where the wall ends from your tap. Tap any part of the wall that’s been missed and it’s added. To take something out, like a picture or a radiator, switch to Remove and tap it."),
        ("Is it free?",
         "Yes. There’s no app to install and no account to make."),
    ]
    faq_html = "".join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication",
              "name": "PaintDial paint visualiser",
              "url": f"{DOMAIN}{VIS_PATH}",
              "applicationCategory": "DesignApplication", "operatingSystem": "Web",
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "GBP"},
              "description": f"See any of {N:,} paints from {BRANDS_WORD} brands sold in the UK on a wall in your own photo, next to its closest match from another brand."}
    text = f"""<h2>How it works</h2>
<p>Take or choose a photo and tap the wall. The visualiser works out where the wall is from your tap, then paints it, keeping the light and shade from your photo, so a corner in shadow stays in shadow. It runs in your browser and the photo isn’t uploaded anywhere.</p>
<p>The first time you tap a wall, your browser downloads the part that finds walls. After that it’s kept, so next time it starts straight away.</p>
<h2>Getting a good result</h2>
<ul>
<li>Stand back so the whole wall is in the photo, and take it in daylight if you can.</li>
<li>Tap each wall you want painted. Switch to Remove to take out pictures, radiators and anything else that shouldn’t be painted.</li>
<li>If you know the colour that’s on the wall now, pick it under Lighting. The new colour is then lit the way your photo is, so a dim room stays dim.</li>
<li>Phone cameras shift colour and screens vary. Narrow it down here, then order testers.</li>
</ul>
<h2>Common questions</h2>
<div class="faq">{faq_html}</div>"""
    secs = _sectionise(text, 'grid').replace('<div class="lead"></div>\n', '', 1)
    title = f"Paint Visualiser: {NBRANDS} Brands on Your Own Wall"
    desc = (f"Take a photo, tap the wall and try {N:,} paints from {BRANDS_WORD} brands sold in the UK, "
            "next to the closest match from another brand. Free, no app.")
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{VIS_PATH}">
{FAVICON}
{FONTS}<style>{PAGES_CSS}</style></head><body><div class="wrap">
{HDR}
{tool}
{secs}
{_ldjson(app_ld, faq_ld)}
<footer>{FOOT}</footer>
</div></body></html>"""


# ---------- colour scheme planner ----------
# Rooms, each with a colour for walls, woodwork, ceiling and an accent, picked from the
# shortlist or by search. Runs in the browser like the visualiser and borrows its library
# (colours.json) and colour maths (vis-core.js), so slugs and match distances are the site's
# own. The scheme is kept in the browser and, when shared, in the link (?s=...), so there is
# no account and nothing stored on a server. Shared links all canonicalise to the bare page.
# First built 12 Nov 2026 from the growth roadmap (item 3); the tool itself is scheme/tool.html.
SCHEME_PATH = '/colour-scheme-planner/'

def build_scheme_page():
    lead = ('<span class="eyebrow">Colour scheme planner</span>'
            '<h1>Plan your colours, room by room</h1>'
            '<p>Add your rooms and give each one a colour for the walls, woodwork and ceiling, plus any others you need. '
            f'Pick from your shortlist or search {N:,} paints from {BRANDS_WORD} brands sold in the UK. '
            'Then share the scheme as a link, or print it as a colour schedule.</p>')
    tool = open('scheme/tool.html', encoding='utf-8').read()
    assert tool.count('<!--SP-LEAD-->') == 1, 'scheme/tool.html has lost its <!--SP-LEAD--> placeholder'
    tool = tool.replace('<!--SP-LEAD-->', lead)
    assert f"PATH='{SCHEME_PATH}'" in tool, 'scheme/tool.html and SCHEME_PATH disagree about the page address'
    faqs = [
        ("Is my scheme saved?",
         "Yes, in your browser, on the device you made it on. There’s no account. To move it to another device, or send it to someone, copy the link."),
        ("What does the link share?",
         "The room names and the colours you chose, and nothing else. Anyone who opens it sees the same scheme and can make their own copy to change."),
        ("What is a colour schedule?",
         "A list of every room and surface with its colour, brand and code. Decorators work from one. Print it, or save it as a PDF from your browser’s print window."),
        ("Can I mix brands in one scheme?",
         "Yes. Each colour shows its closest matches from other brands, and you can swap to one of them with a tap, so you can keep the whole house in one brand if that’s easier to buy."),
        ("Is it free?",
         "Yes. There’s no app to install and no account to make."),
    ]
    faq_html = "".join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    text = f"""<h2>How it works</h2>
<p>Add a room, then tap a surface to choose its colour. Colours you’ve saved to your shortlist are offered first, and you can search the whole library by name or code. The strip at the top puts the wall colours side by side, so you can see how one room leads into the next.</p>
<p>Every room starts with walls, woodwork and ceiling. Use <b>Add another colour</b> for a feature wall, cabinets, a door or anything else, and tap any name to change it.</p>
<h2>Getting a scheme that hangs together</h2>
<ul>
<li>Choose the woodwork and ceiling colours once, then use them in every room. One white through the house is easier to live with than five.</li>
<li>Look at the rooms that open onto each other. Colours you can see from one doorway should sit comfortably side by side.</li>
<li>Open <b>Closest in other brands</b> under any colour to see what else is near it.</li>
<li>Screens vary and paint changes with the light. Order testers of every colour and try them in the room they’re for.</li>
</ul>
<h2>Common questions</h2>
<div class="faq">{faq_html}</div>"""
    secs = _sectionise(text, 'grid').replace('<div class="lead"></div>\n', '', 1)
    title = "Colour Scheme Planner: Paint Colours Room by Room"
    desc = (f"Plan paint colours for every room from {N:,} paints across {BRANDS_WORD} UK brands. "
            "Share the scheme as a link or print a colour schedule. Free, no account.")
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{SCHEME_PATH}">
{FAVICON}
{FONTS}<style>{PAGES_CSS}</style></head><body><div class="wrap">
{HDR}
{tool}
{secs}
{_ldjson(faq_ld)}
<footer>{FOOT}</footer>
</div></body></html>"""


def build_calc_page():
    lead = ('<span class="eyebrow">Paint calculator</span>'
            '<h1>How much paint do you need?</h1>'
            f'<p>Pick a brand and give the size of the room. The sum uses the coverage figure each brand publishes for its own wall paint, for {BRANDS_WORD} brands sold in the UK, and gives the answer in the tin sizes that brand sells.</p>')
    tool = open('calc/tool.html', encoding='utf-8').read()
    for mark in ('<!--PC-LEAD-->', '/*PC-DATA*/null', "/*PC-CHECKED*/''"):
        assert tool.count(mark) == 1, f'calc/tool.html has lost its {mark} placeholder'
    tool = (tool.replace('<!--PC-LEAD-->', lead)
                .replace('/*PC-DATA*/null', json.dumps(calc_data(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
                .replace("/*PC-CHECKED*/''", json.dumps(PAINT_CHECKED)))
    none = [b.replace("'", '’') for b in BRAND_ORDER if b not in CALC_COV]
    faqs = [
        ("How is it worked out?",
         "The area of the walls, less doors and windows, times the number of coats, divided by the coverage the brand gives for a litre of its wall matt. The answer is then rounded up to the tins that brand sells."),
        ("Why does the amount change from brand to brand?",
         "Each brand states a different coverage for its own paint. The calculator uses each brand’s own published figure and doesn’t compare them."),
        ("Why does it ask me for the coverage?",
         f"{_and([H.escape(n) for n in none])} don’t publish a coverage per litre for the paint the calculator uses, and PaintDial doesn’t guess one. The figure is on the tin or in the paint’s data sheet."),
        ("How many coats will I need?",
         "Most brands say two. Bare plaster needs a first thinned coat or a primer, and going from a dark colour to a light one can take a third."),
        ("Does it work for woodwork or ceilings?",
         "Tick the box to add the ceiling in the same paint. Woodwork is painted in eggshell or gloss, which cover differently, so use the figure on that tin."),
    ]
    faq_html = "".join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    text = f"""<h2>Measuring a room</h2>
<p>Measure the length and width of the room and the height of the walls. Count the doors and windows so their area comes off. If the room isn’t a plain rectangle, work out the wall area yourself (width times height for each wall, added up) and choose <b>I know the area</b>.</p>
<h2>What the figure does and doesn’t tell you</h2>
<ul>
<li>It’s for each brand’s main matt for walls and ceilings, the same paint described on that brand’s colour pages.</li>
<li>Coverage figures are the brands’ own, checked {PAINT_CHECKED}. Where a brand says “up to”, the answer is the least you’ll need.</li>
<li>Rough or bare walls and a big change of colour take more. If you’re between tin sizes, the calculator rounds up.</li>
<li>Mixed-to-order paint can vary slightly from batch to batch, so buy enough for the room in one go.</li>
</ul>
<h2>Common questions</h2>
<div class="faq">{faq_html}</div>"""
    secs = _sectionise(text, 'grid').replace('<div class="lead"></div>\n', '', 1)
    title = "Paint Calculator: How Much Paint for a Room, by Brand"
    desc = (f"Work out how many litres and which tins you need, using the coverage each of {BRANDS_WORD} UK paint brands "
            "publishes for its own wall paint. Free, no account.")
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{CALC_PATH}">
{FAVICON}
{FONTS}<style>{PAGES_CSS}</style></head><body><div class="wrap">
{HDR}
{tool}
{secs}
{_ldjson(faq_ld)}
<footer>{FOOT}</footer>
</div></body></html>"""


# Hand-written, evergreen openings for the most-searched hero colours. The opening is
# editorial (no LRV/hex/price claims); the closest-match sentence that follows is ALWAYS
# generated from the data, so match names can never go stale. Any slug not listed gets a
# varied generated opening instead.
EDITORIAL_INTRO = {
 'farrow-and-ball-hague-blue': "{home} is one of Farrow &amp; Ball’s best-known deep blues. You’ll see it a lot on front doors, kitchen cabinets and in darker rooms.",
 'farrow-and-ball-elephants-breath': "{home} is a warm greige and one of Farrow &amp; Ball’s most popular neutrals. It shifts a lot with the light through the day, so test any match in the room it’s going in.",
 'farrow-and-ball-railings': "{home} is Farrow &amp; Ball’s soft off-black, with a blue undertone. It’s a favourite for railings, window frames and joinery.",
 'farrow-and-ball-setting-plaster': "{home} is a chalky plaster pink, and in the right light it reads more like a warm neutral. It’s one of the most searched-for Farrow &amp; Ball colours.",
 'farrow-and-ball-skimming-stone': "A warm, soft off-white that sits comfortably almost anywhere, {home} gets used a lot for whole-house schemes.",
 'farrow-and-ball-sulking-room-pink': "{home} is a muted, dusky pink that suits snugs and bedrooms.",
 'farrow-and-ball-green-smoke': "{home} is a smoky grey-green that gets used a lot on cabinetry and panelling.",
 'farrow-and-ball-cornforth-white': "{home} is one of Farrow &amp; Ball’s most popular pale greys, used a lot in living rooms and hallways.",
 'farrow-and-ball-ammonite': "{home} is a soft, pale grey that has become a default neutral in a lot of UK homes.",
 'farrow-and-ball-stiffkey-blue': "{home} is one of Farrow &amp; Ball’s darkest blues, and it works as well on cabinets as it does on walls.",
 'farrow-and-ball-de-nimes': "{home} is a muted grey-blue named after workwear denim. It’s one of Farrow &amp; Ball’s newer colours and has caught on quickly.",
 'farrow-and-ball-stone-blue': "{home} is one of Farrow &amp; Ball’s historic colours, a mid-toned blue that leans towards green.",
}

def build_alternatives_page(i):
    p = paints[i]; lab = LAB[i]; name = H.escape(p['name']); brand = H.escape(p['brand'])
    d = mdist(i)                       # gated: a colour's alternatives never include a neutral
    best = {}
    for k in range(N):
        b = paints[k]['brand']
        if b == p['brand'] or d[k] >= 1e9:
            continue
        if b not in best or d[k] < d[best[b]]:
            best[b] = k
    # exhaustive ranked list: EVERY genuinely close match from other brands,
    # multiple per brand allowed (the colour page shows the one-per-brand view)
    others = sorted((k for k in range(N) if paints[k]['brand'] != p['brand'] and d[k] < 1e9), key=lambda k: d[k])
    alts = [k for k in others if d[k] < 10][:20]
    if len(alts) < 8:
        alts = others[:8]
    closest = alts[0]
    cheapest = min(alts, key=lambda k: (TIER[paints[k]['brand']], d[k]))
    depth, fam = describe(i)

    # ---- PaintDial verdict: computed from the colour values, unique per page ----
    cb = diff_bits(i, closest)
    close_txt = (f'is the closest match from any other brand ({matchword(d[closest])})'
                 + (f', though it\u2019s {joinbits(cb)}.' if cb
                    else f', and it keeps {name}\u2019s lightness, warmth and saturation.'))
    if cheapest == closest:
        value_txt = ' It\u2019s also the best-value tier among the close matches, which is unusual: normally the nearest and the best-value match are different paints.'
    else:
        vb = diff_bits(i, cheapest)
        value_txt = (f' The closest value-tier option is <a class="pn" href="/colours/{slugs[cheapest]}">'
                     f'<i style="background:{paints[cheapest]["hex"]}"></i>{H.escape(paints[cheapest]["name"])}</a> '
                     f'by {H.escape(paints[cheapest]["brand"])} ({matchword(d[cheapest])})'
                     + (f', {joinbits(vb)}.' if vb else ', just as true to the original.')
                     + cooler_note(i, cheapest))

    # How distinctive is this colour? Counts vary a lot per colour, so this line
    # is real information rather than filler.
    n_near = sum(1 for b, k in best.items() if d[k] < 3)
    n_brands = len(best)
    if n_near == 0:
        dist_txt = (f' No other brand has a near-identical match for {name}. '
                    f'It\u2019s one of the more distinctive colours in the library, so expect a visible difference whichever you pick.')
    elif n_near == 1:
        dist_txt = f' Only one of the {n_brands} other brands manages a near-identical match, which makes {name} fairly distinctive.'
    elif n_near == n_brands:
        dist_txt = f' Every other brand has a near-identical match, so you have plenty of choice here.'
    elif n_near == n_brands - 1:
        dist_txt = f' Almost every other brand ({n_near} of {n_brands}) has a near-identical match, so you have real choice here.'
    else:
        dist_txt = f' {n_near} of the {n_brands} other brands have a near-identical match.'

    verdict = (f'<div class="verdict"><h3>PaintDial verdict</h3><p>'
               f'<a class="pn" href="/colours/{slugs[closest]}">'
               f'<i style="background:{paints[closest]["hex"]}"></i>{H.escape(paints[closest]["name"])}</a> '
               f'by {H.escape(paints[closest]["brand"])} {close_txt}{value_txt}{dist_txt} '
               f'LRV is estimated from each brand\u2019s swatch, so order testers before committing.</p></div>')

    def acard(rank, k):
        q = paints[k]; s = slugs[k]; note = ''
        if k == closest: note = 'Closest overall match.'
        elif k == cheapest: note = 'Closest match from a value-tier brand.'
        note_html = f'<span class="a-note">{note}</span>' if note else ''
        # Computed, per-match difference from the target colour \u2014 same machinery as the
        # verdict (diff_bits/joinbits), so it's factual and can never contradict the swatch.
        _db = diff_bits(i, k)
        diff_html = (f'<span class="a-diff">{joinbits(_db)[:1].upper()+joinbits(_db)[1:]} than {name}.</span>'
                     if _db else '')
        # The card is a div with the name as a stretched link (the ::after covers the
        # card), so the compare button can sit beside the link rather than inside it.
        return (f'<div class="alt">'
                f'<span class="a-rank">{rank}</span>'
                f'<span class="a-sw" style="background:{q["hex"]}"></span>'
                f'<span class="a-body"><a class="a-nm" href="/colours/{s}">{H.escape(q["name"])}</a>'
                f'<span class="a-br">{H.escape(q["brand"])} \u00b7 {TIER_WORD[TIER[q["brand"]]]} \u00b7 {matchword(d[k])} \u00b7 <span title="Difference score: lower is closer">{float(d[k]):.1f}</span></span>'
                f'{diff_html}{note_html}{cmp_btn(p, q, matchword(d[k]))}</span>'
                f'<span class="a-hex">{q["hex"]}</span></div>')

    cards = ''.join(acard(n + 1, k) for n, k in enumerate(alts))
    nm = lambda k: H.escape(paints[k]['name']); brn = lambda k: H.escape(paints[k]['brand'])
    dulux = best.get('Dulux')
    dulux_q = (f'<div class="q"><h3>Is there a Dulux equivalent to <span class="pn"><i></i>{name}</span>?</h3>'
               f'<p>The nearest Dulux colour is <a class="pn" href="/colours/{slugs[dulux]}"><i style="background:{paints[dulux]['hex']}"></i>{nm(dulux)}</a> ({matchword(d[dulux])}). '
               f'It won\u2019t be pixel-perfect, so order a tester before committing.</p></div>') if dulux is not None else ''
    # ---- Intro ----
    _homelink = f'<a class="pn" href="/colours/{slugs[i]}"><i></i>{name}</a>'
    # Only hand-written intros get a paragraph. Rotating stock openers were removed in Nov 2026,
    # and the verdict box directly below already names the closest match, so no generated
    # sentence repeats it here.
    _open = EDITORIAL_INTRO.get(slugs[i])
    intro_html = f'<p class="intro">{_open.replace("{home}", _homelink)}</p>' if _open else ''

    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand} {name} alternatives \u2014 dupes &amp; closest matches | PaintDial</title>
<meta name="description" content="The closest alternative to {brand} {name} is {H.escape(paints[closest]['name'])} by {H.escape(paints[closest]['brand'])} ({matchword(d[closest])}). See all {len(alts)} matches from other brands, ranked, including value-brand options.">
<link rel="canonical" href="{DOMAIN}/alternatives/{slugs[i]}">
{_ldjson(
  _breadcrumb([("Home","/"),("Colours","/colours/"),(p['name'],f"/colours/{slugs[i]}"),("Alternatives",f"/alternatives/{slugs[i]}")]),
  _itemlist([(f"{paints[k]['name']} by {paints[k]['brand']}", f"/colours/{slugs[k]}") for k in alts])
)}
<meta property="og:title" content="{brand} {name} alternatives \u2014 closest: {H.escape(paints[closest]['name'])} by {H.escape(paints[closest]['brand'])}">
<meta property="og:image" content="{DOMAIN}/share/{slugs[i]}.jpg">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{DOMAIN}/share/{slugs[i]}.jpg">
{FAVICON}
{FONTS}<style>{ALT_CSS}{COMPARE_BTN_CSS}{KOFI_STRIP_CSS}</style></head><body style="--pc:{p['hex']}"><div class="top-band"></div><div class="wrap">
<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="head-nav" href="/research/">Research</a><a class="head-nav" href="/colour-scheme-planner/">Scheme planner</a><a class="lib-link" href="/colours/"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span>Colour library</a><a class="nav-cta" href="/"><span class="cta-wheel" aria-hidden="true"></span>Open the colour tool</a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/research/">Research</a><a href="/colour-scheme-planner/">Scheme planner</a></div>
<h1>{brand} <span class="pn"><i></i>{name}</span> alternatives</h1>
<div class="hero-card"><div class="hero-sw" style="background:{p['hex']}">{solo_btn(p, chip=False)}</div>
<div class="hero-info"><div class="hero-label">The colour you\u2019re matching</div>
<div class="hero-name">{brand} <span class="pn"><i></i>{name}</span></div>
<div class="hero-stats"><span><i>Hex</i>{p['hex']}</span><span><i>LRV</i>\u2248 {lrv(L[i]):.0f}</span><span><i>Shade</i>{depth.capitalize()} {fam}</span></div></div></div>
{intro_html}
{verdict}
<p class="intro">One brand can appear several times if it has more than one close match. For the single best match <em>per brand</em>, see the <a href="/colours/{slugs[i]}">{name} colour page</a>.</p>
<h2>All {len(alts)} close matches, ranked</h2>
<p class="intro">The number on each is how far apart the two colours are: under 2 is near-identical, under 5 very close. <a href="/how-it-works/#difference">How it\u2019s worked out</a>.</p>
<div class="alts">{cards}</div>
<div class="faq"><h2>Common questions</h2>
{dulux_q}
<div class="q"><h3>What\u2019s the best-value alternative to <span class="pn"><i></i>{name}</span>?</h3>
<p>Of the close matches, <a class="pn" href="/colours/{slugs[cheapest]}"><i style="background:{paints[cheapest]['hex']}"></i>{nm(cheapest)}</a> by {brn(cheapest)} is the best-value option ({TIER_WORD[TIER[paints[cheapest]['brand']]].lower()}, {matchword(d[cheapest])}).</p></div>
<div class="q"><h3>How close are these to <span class="pn"><i></i>{name}</span>?</h3>
<p>They\u2019re ranked nearest first by perceptual colour difference, and the label on each card says how close it is. Screens differ from paint on a wall, so treat these as a shortlist and order tester pots.</p></div></div>
<div class="cta"><b style="font-family:var(--serif);font-size:18px">Matching a different colour?</b>
<p style="font-size:14px;color:var(--muted);margin:6px 0 0">Search any paint name in the tool to see its closest matches across all {BRANDS_WORD} brands.</p>
<a href="/colours/{slugs[i]}">See the full {name} colour page \u2192</a></div>
{kofi_strip()}
<footer>{FOOT}</footer>
</div><div class="top-band"></div>{COMPARE_SCRIPT}</body></html>"""

# ---------- run ----------
if __name__ == '__main__':
    os.makedirs('site/colours', exist_ok=True)
    os.makedirs('site/alternatives', exist_ok=True)
    # wipe old colour pages so removed slugs don't linger
    for fn in os.listdir('site/colours'):
        if fn.endswith('.html'): os.remove('site/colours/'+fn)

    # Every buy button should go to the colour itself, never to a search page.
    _search = [p for p in paints if re.search(r'/search\b|catalogsearch|[?&]q=', buy_link(p) or '')]
    if _search:
        print(f'WARNING: {len(_search)} colour pages link to a search, not the colour, e.g. '
              + ', '.join(f"{p['brand']} {p['name']}" for p in _search[:5]))
    else:
        print('buy links: every colour page links to its colour directly')

    count = 0
    for i in range(N):
        open(f'site/colours/{slugs[i]}.html', 'w', encoding='utf-8').write(build_colour_page(i))
        count += 1
        if count % 1000 == 0: print(f'  ...{count}/{N} colour pages')
    print('colour pages:', count)

    for b in BRAND_ORDER:
        open(f'site/colours/{base_slug(b)}.html', 'w', encoding='utf-8').write(build_brand_page(b))
    print('brand pages:', len(BRAND_ORDER))

    open('site/colours/index.html', 'w', encoding='utf-8').write(build_colours_index())
    print('colours index written')

    for fn in os.listdir('site/alternatives'):
        if fn.endswith('.html'): os.remove('site/alternatives/'+fn)
    alt_idx = [i for i in range(N) if paints[i]['brand'] in ALT_BRANDS]
    for i in alt_idx:
        open(f'site/alternatives/{slugs[i]}.html', 'w', encoding='utf-8').write(build_alternatives_page(i))
    print('alternatives pages:', len(alt_idx))

    os.makedirs('site/dupes', exist_ok=True)
    for fn in os.listdir('site/dupes'):
        if fn.endswith('.html'): os.remove('site/dupes/'+fn)
    for b in DUPE_TARGETS:
        open(f'site/dupes/{base_slug(b)}.html', 'w', encoding='utf-8').write(build_dupes_page(b))
    print('dupes pages:', len(DUPE_TARGETS))

    os.makedirs('site' + POPULAR_PATH, exist_ok=True)
    open('site' + POPULAR_PATH + 'index.html', 'w', encoding='utf-8').write(build_popular_page())
    print('most searched colours page written:', len(POPULAR_IDX))

    os.makedirs('site/how-it-works', exist_ok=True)
    open('site/how-it-works/index.html', 'w', encoding='utf-8').write(build_method_page())
    os.makedirs('site/about', exist_ok=True)
    open('site/about/index.html', 'w', encoding='utf-8').write(build_about_page())
    os.makedirs('site/privacy', exist_ok=True)
    open('site/privacy/index.html', 'w', encoding='utf-8').write(build_privacy_page())
    os.makedirs('site/contact/thanks', exist_ok=True)
    open('site/contact/index.html', 'w', encoding='utf-8').write(build_contact_page())
    open('site/contact/thanks/index.html', 'w', encoding='utf-8').write(build_contact_thanks_page())
    os.makedirs('site/paint-match-index', exist_ok=True)
    open('site/paint-match-index/index.html', 'w', encoding='utf-8').write(build_match_index_page())
    print('paint match index written')
    os.makedirs('site/paint-choice-index', exist_ok=True)
    open('site/paint-choice-index/index.html', 'w', encoding='utf-8').write(build_choice_index_page())
    print('paint choice index written')
    os.makedirs('site/research', exist_ok=True)
    open('site/research/index.html', 'w', encoding='utf-8').write(build_research_hub())
    print('research hub written')
    os.makedirs('site/match-paint-from-a-photo', exist_ok=True)
    open('site/match-paint-from-a-photo/index.html', 'w', encoding='utf-8').write(build_photo_match_page())
    print('photo-match page written')
    import shutil as _shv
    os.makedirs('site' + VIS_PATH, exist_ok=True)
    open('site' + VIS_PATH + 'index.html', 'w', encoding='utf-8').write(build_visualiser_page())
    json.dump(visualiser_data(), open('site' + VIS_PATH + 'colours.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    for _f in VIS_FILES:
        _shv.copyfile('visualiser/' + _f, 'site' + VIS_PATH + _f)
    print('paint visualiser written')
    os.makedirs('site' + SCHEME_PATH, exist_ok=True)
    open('site' + SCHEME_PATH + 'index.html', 'w', encoding='utf-8').write(build_scheme_page())
    print('colour scheme planner written')
    os.makedirs('site' + CALC_PATH, exist_ok=True)
    open('site' + CALC_PATH + 'index.html', 'w', encoding='utf-8').write(build_calc_page())
    print('paint calculator written')
    print('trust pages: 3 (+ contact thanks)')

    urls = [f'{DOMAIN}/', f'{DOMAIN}/colours/'] \
        + [f'{DOMAIN}/colours/{base_slug(b)}' for b in BRAND_ORDER] \
        + [f'{DOMAIN}/colours/{slugs[i]}' for i in range(N)] \
        + [f'{DOMAIN}/alternatives/{slugs[i]}' for i in alt_idx] \
        + [f'{DOMAIN}/dupes/{base_slug(b)}' for b in DUPE_TARGETS] \
        + [f'{DOMAIN}{POPULAR_PATH}'] \
        + [f'{DOMAIN}/how-it-works/', f'{DOMAIN}/about/', f'{DOMAIN}/contact/', f'{DOMAIN}/privacy/', f'{DOMAIN}/paint-match-index/',
           f'{DOMAIN}/paint-choice-index/', f'{DOMAIN}/research/', f'{DOMAIN}/match-paint-from-a-photo/',
           f'{DOMAIN}{VIS_PATH}', f'{DOMAIN}{SCHEME_PATH}', f'{DOMAIN}{CALC_PATH}']
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += ''.join(f'<url><loc>{u}</loc></url>\n' for u in urls)+'</urlset>'
    open('site/sitemap.xml', 'w').write(sm)

    # The compare view's script is one shared file (see COMPARE_SCRIPT above). Copied
    # here rather than in build.sh so a plain `python3 gen_pages.py` run is complete too.
    import shutil as _sh
    # The compare view names stockist-sourced and swatch-sampled brands from its own SOURCED
    # and SWATCHED lists; they must agree with SOURCE_NOTE and SWATCH_SAMPLED or the compare
    # strip and the colour pages say different things.
    _js = open('pd-compare.js', encoding='utf-8').read()
    _m = re.search(r'var SOURCED = (\{[^}]*\});', _js)
    assert _m and json.loads(_m.group(1)) == {b: s for b, (s, _u) in SOURCE_NOTE.items()}, \
        'pd-compare.js SOURCED map does not match SOURCE_NOTE in gen_pages.py'
    _m = re.search(r'var SWATCHED = (\[[^\]]*\]);', _js)
    assert _m and sorted(json.loads(_m.group(1))) == sorted(SWATCH_SAMPLED), \
        'pd-compare.js SWATCHED list does not match SWATCH_SAMPLED in gen_pages.py'
    _sh.copyfile('pd-compare.js', 'site/pd-compare.js')
    _sh.copyfile('fraunces-amp.woff2', 'site/fraunces-amp.woff2')
    print('pd-compare.js and fraunces-amp.woff2 copied')


    # ---------- 404 page (Netlify serves 404.html automatically) ----------
    NOTFOUND = f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page not found | PaintDial</title>
    <meta name="robots" content="noindex">
    {FAVICON}
    {FONTS}<style>{CSS}</style></head><body><div class="top-band"></div><div class="wrap">
    {HDR}
    <div class="hero"><div class="hero-body">
    <span class="eyebrow">404</span><h1>That colour has escaped the wheel</h1>
    <p class="sub">That page doesn\u2019t exist. It may have moved when the site was reorganised.</p>
    <p class="sub" style="margin-top:14px"><a href="/" style="color:inherit;font-weight:600">Open the colour tool \u2192</a> &nbsp;\u00b7&nbsp; <a href="/colours/" style="color:inherit;font-weight:600">Browse the colour library \u2192</a></p>
    </div></div>
    {FOOT}
    </div></body></html>"""
    open('site/404.html', 'w').write(NOTFOUND)
    print('404 page written')
    print('sitemap:', len(urls), 'urls')
