#!/usr/bin/env python3
"""
PaintDial page generator (definitive, nine brands incl. Craig & Rose, Lick, Crown, COAT).
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
         8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven', 12: 'twelve'}
def numword(n):
    return _NUMW.get(n, f'{n}')
def a_an(w):
    """'a' or 'an' by the first letter — so 'Order an Etruria tester', not 'a Etruria'."""
    return 'an' if (w[:1].lower() in 'aeiou') else 'a'
SHORTLIST_CSS = '.pd-heart{position:absolute;top:8px;right:8px;width:30px;height:30px;border:none;border-radius:50%;background:rgba(255,255,255,.82);backdrop-filter:blur(3px);cursor:pointer;display:flex;align-items:center;justify-content:center;color:#8C8578;transition:transform .12s,color .12s;z-index:2;padding:0}\n.pd-heart:hover{transform:scale(1.12);color:#5E7E8B}\n.pd-heart svg{fill:none;stroke:currentColor;stroke-width:1.7}\n.pd-heart.on{color:#5E7E8B}.pd-heart.on svg{fill:currentColor;stroke:currentColor}\n#pd-tray{position:fixed;right:14px;bottom:14px;z-index:900;background:#fff;border:1px solid #E3DFD5;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.16);padding:11px 12px;max-width:min(92vw,560px)}\n.pd-tray-head{display:flex;align-items:center;gap:8px;font-size:13px;color:#211F1B}\n.pd-tray-head b{font-weight:600}.pd-tray-n{background:#F1EEE7;border-radius:20px;padding:1px 8px;font-size:12px;color:#7E786C}\n.pd-tray-clear{margin-left:auto;border:none;background:none;color:#9A6B6B;font-size:12px;cursor:pointer;padding:2px 4px}\n.pd-tray-clear:hover{text-decoration:underline}\n.pd-tray-note{font-size:11px;color:#9A9488;margin:3px 0 9px}\n.pd-tray-row{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px}\n.pd-tray-chip{position:relative;flex:0 0 auto;width:64px;text-decoration:none;color:#211F1B}\n.pd-tray-sw{display:block;height:48px;border-radius:8px;border:1px solid rgba(0,0,0,.08)}\n.pd-tray-name{display:block;font-size:10px;line-height:1.2;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#7E786C}\n.pd-tray-x{position:absolute;top:-6px;right:-6px;width:18px;height:18px;border-radius:50%;background:#211F1B;color:#fff;font-size:12px;line-height:18px;text-align:center}\n.pd-tray-mail{margin-top:10px;border-top:1px solid #EEEAE1;padding-top:9px}\n.pd-mail-toggle{border:none;background:none;color:#5E7E8B;font-size:12.5px;font-weight:600;cursor:pointer;padding:0}\n.pd-mail-toggle:hover{text-decoration:underline}\n.pd-mail-form{display:flex;gap:6px;margin-top:8px}\n.pd-mail-input{flex:1;min-width:0;border:1px solid #D9D4C8;border-radius:8px;padding:7px 9px;font-size:13px;font-family:inherit}\n.pd-mail-input:focus{outline:none;border-color:#5E7E8B}\n.pd-mail-send{border:none;background:#5E7E8B;color:#fff;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer}\n.pd-mail-send:hover{filter:brightness(1.06)}\n\n.pd-tray-min{border:none;background:none;color:#7E786C;font-size:17px;line-height:1;cursor:pointer;padding:0 4px;margin-left:2px}\n.pd-tray-min:hover{color:#211F1B}\n#pd-tray.min{padding:0;cursor:pointer}\n#pd-tray.min .pd-tray-head{margin-bottom:0;padding:10px 13px}\n#pd-tray.min .pd-tray-note,#pd-tray.min .pd-tray-row,#pd-tray.min .pd-tray-mail,#pd-tray.min .pd-tray-clear{display:none}\n#pd-sl-flash{position:fixed;left:50%;bottom:80px;transform:translateX(-50%) translateY(10px);background:#211F1B;color:#fff;padding:9px 15px;border-radius:9px;font-size:13px;opacity:0;pointer-events:none;transition:.25s;z-index:950}\n#pd-sl-flash.show{opacity:1;transform:translateX(-50%) translateY(0)}\n.chip,.c-swatch,.alt-row,.hero-swatch{position:relative}\n@media(max-width:560px){#pd-tray{right:8px;bottom:8px;left:8px;max-width:none}.pd-heart{width:27px;height:27px}}\n'
SHORTLIST_JS = '/* ---------- PaintDial shortlist: save paints on this device, compare & email ----------\n   No login, no basket. Held in localStorage; shared by the tool and every colour page. */\n(function(){\n  const KEY=\'pd_shortlist_v1\', MAX=12, SITE=\'https://www.paintdial.co.uk\';\n  let minimized=false;\n  const read=()=>{try{return JSON.parse(localStorage.getItem(KEY))||[];}catch(e){return [];}};\n  const write=a=>{try{localStorage.setItem(KEY,JSON.stringify(a.slice(0,MAX)));}catch(e){}};\n  const has=id=>read().some(x=>x.id===id);\n  const idOf=(name,brand)=>(brand+\'|\'+name).toLowerCase();\n\n  function toggle(item){\n    let a=read(); const i=a.findIndex(x=>x.id===item.id);\n    if(i>=0) a.splice(i,1); else { if(a.length>=MAX){flash(\'You can keep up to \'+MAX+\' colours\');return false;} a.unshift(item); }\n    write(a); paint(); return true;\n  }\n  function flash(msg){\n    let f=document.getElementById(\'pd-sl-flash\'); if(!f){f=document.createElement(\'div\');f.id=\'pd-sl-flash\';document.body.appendChild(f);}\n    f.textContent=msg; f.classList.add(\'show\'); clearTimeout(f._t); f._t=setTimeout(()=>f.classList.remove(\'show\'),1900);\n  }\n  const BOOKMARK=\'<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>\';\n\n  window.PDShortlist={\n    heartHTML:(name,brand,hex)=>`<button class="pd-heart" data-name="${name.replace(/"/g,\'&quot;\')}" data-brand="${brand.replace(/"/g,\'&quot;\')}" data-hex="${hex}" aria-label="Save ${name.replace(/"/g,\'&quot;\')} to your shortlist" title="Save to shortlist">${BOOKMARK}</button>`,\n    isSaved:has, idOf, toggle, read, refresh:()=>paint()\n  };\n\n  function bindHearts(root){\n    (root||document).querySelectorAll(\'.pd-heart\').forEach(btn=>{\n      if(btn._b) return; btn._b=1;\n      const id=idOf(btn.dataset.name, btn.dataset.brand);\n      if(has(id)) btn.classList.add(\'on\');\n      btn.addEventListener(\'click\',e=>{\n        e.preventDefault(); e.stopPropagation();\n        const ok=toggle({id, name:btn.dataset.name, brand:btn.dataset.brand, hex:btn.dataset.hex});\n        if(ok!==false) btn.classList.toggle(\'on\', has(id));\n      });\n    });\n  }\n  window.PDShortlist.bind=bindHearts;\n\n  function slug(s){return s.normalize(\'NFKD\').replace(/[\\u0300-\\u036f]/g,\'\').toLowerCase().replace(/&/g,\'and\').replace(/\'/g,\'\').replace(/[^a-z0-9]+/g,\'-\').replace(/^-|-$/g,\'\');}\n  function colourURLFor(it){return `/colours/${slug(it.brand)}-${slug(it.name)}`;}\n\n  function emailBody(items){\n    const lines = items.map(it=>`\\u2022 ${it.name} \\u2014 ${it.brand} \\u2014 ${it.hex}\\n  ${SITE}${colourURLFor(it)}`).join(\'\\n\\n\');\n    return `Here are the paint colours I shortlisted on PaintDial:\\n\\n${lines}\\n\\nCompare them anytime at ${SITE}`;\n  }\n  function sendEmail(addr){\n    const items=read(); if(!items.length) return;\n    const subj=`My PaintDial shortlist (${items.length} colour${items.length>1?\'s\':\'\'})`;\n    const to=addr?encodeURIComponent(addr):\'\';\n    window.location.href=`mailto:${to}?subject=${encodeURIComponent(subj)}&body=${encodeURIComponent(emailBody(items))}`;\n  }\n\n  function paint(){\n    const items=read();\n    let tray=document.getElementById(\'pd-tray\');\n    if(!items.length){ if(tray) tray.remove(); document.querySelectorAll(\'.pd-heart.on\').forEach(b=>{ if(!has(idOf(b.dataset.name,b.dataset.brand))) b.classList.remove(\'on\');}); return; }\n    if(!tray){ tray=document.createElement(\'div\'); tray.id=\'pd-tray\'; document.body.appendChild(tray); }\n    tray.innerHTML=\n      `<div class="pd-tray-head"><b>Your shortlist</b> <span class="pd-tray-n">${items.length}</span>`+\n      `<button class="pd-tray-min" aria-label="Minimise shortlist" title="Minimise">\\u2013</button>`+\n      `<button class="pd-tray-clear" aria-label="Clear shortlist">Clear</button></div>`+\n      `<div class="pd-tray-note">Saved on this device \\u2014 come back anytime. A shortlist to compare, not a basket.</div>`+\n      `<div class="pd-tray-row">`+items.map(it=>\n        `<a class="pd-tray-chip" href="${colourURLFor(it)}" title="${it.name} \\u2014 ${it.brand}">`+\n        `<span class="pd-tray-sw" style="background:${it.hex}"></span>`+\n        `<span class="pd-tray-x" data-id="${it.id}" role="button" aria-label="Remove ${it.name}">\\u00d7</span>`+\n        `<span class="pd-tray-name">${it.name}</span></a>`).join(\'\')+`</div>`+\n      `<div class="pd-tray-mail">`+\n        `<button class="pd-mail-toggle" type="button">\\u2709 Email these to me</button>`+\n        `<div class="pd-mail-form" hidden><input type="email" class="pd-mail-input" placeholder="you@email.com" aria-label="Your email address"><button class="pd-mail-send" type="button">Send</button></div>`+\n      `</div>`;\n    tray.querySelector(\'.pd-tray-clear\').onclick=()=>{write([]);paint();document.querySelectorAll(\'.pd-heart.on\').forEach(b=>b.classList.remove(\'on\'));};\n    tray.querySelectorAll(\'.pd-tray-x\').forEach(x=>x.addEventListener(\'click\',e=>{\n      e.preventDefault();e.stopPropagation(); const a=read().filter(y=>y.id!==x.dataset.id); write(a); paint();\n      document.querySelectorAll(\'.pd-heart\').forEach(b=>{ if(idOf(b.dataset.name,b.dataset.brand)===x.dataset.id) b.classList.remove(\'on\');});\n    }));\n    const mt=tray.querySelector(\'.pd-mail-toggle\'), mf=tray.querySelector(\'.pd-mail-form\'),\n          mi=tray.querySelector(\'.pd-mail-input\'), ms=tray.querySelector(\'.pd-mail-send\');\n    mt.onclick=()=>{mf.hidden=!mf.hidden; if(!mf.hidden) mi.focus();};\n    ms.onclick=()=>sendEmail(mi.value.trim());\n    mi.addEventListener(\'keydown\',e=>{if(e.key===\'Enter\'){e.preventDefault();sendEmail(mi.value.trim());}});\n    // minimise / expand\n    const head=tray.querySelector(\'.pd-tray-head\'), minBtn=tray.querySelector(\'.pd-tray-min\');\n    const applyMin=()=>{tray.classList.toggle(\'min\',minimized); minBtn.textContent=minimized?\'\\u002b\':\'\\u2013\'; minBtn.title=minimized?\'Expand\':\'Minimise\';};\n    minBtn.addEventListener(\'click\',e=>{e.stopPropagation(); minimized=!minimized; applyMin();});\n    head.addEventListener(\'click\',e=>{ if(minimized && !e.target.closest(\'.pd-tray-clear\')){ minimized=false; applyMin(); }});\n    applyMin();\n  }\n\n  document.addEventListener(\'DOMContentLoaded\',()=>{bindHearts(document);paint();});\n  window.addEventListener(\'pd:rendered\',e=>bindHearts(e.detail||document));\n})();\n'

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
    """A Product node is the honest fit: a named, branded, purchasable paint colour."""
    return {"@context":"https://schema.org","@type":"Product","name":f"{name} by {brand}",
            "brand":{"@type":"Brand","name":brand},"category":"Paint",
            "image":f"{DOMAIN}/share/{slug}.jpg","url":f"{DOMAIN}/colours/{slug}",
            "description":desc,"color":hexv,
            "additionalProperty":{"@type":"PropertyValue","name":"Hex","value":hexv}}

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

def save_button(name, brand, hexv):
    """A big, explicit labelled version of the shortlist bookmark for the hero.
    Shares the .pd-heart class so the existing shortlist JS binds and toggles it;
    the .btn-save class restyles it from the corner-icon into a labelled button."""
    nm=H.escape(name, quote=True); br=H.escape(brand, quote=True)
    return (f'<button class="pd-heart btn-save" data-name="{nm}" data-brand="{br}" data-hex="{hexv}" '
            f'aria-label="Save {nm} to your shortlist" title="Save to your shortlist">'
            '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>'
            '<span class="save-on">Saved</span><span class="save-off">Save this paint</span></button>')

def _ldjson(*objs):
    return "".join(f'<script type="application/ld+json">{_json.dumps(o, ensure_ascii=False, separators=(",",":"))}</script>' for o in objs)
AWIN_AFFID = "2971455"
# Freshlick (Awin #101923) retailer route for brands with no direct programme (Crown, Little Greene).
# DORMANT while None -> direct links. Set to 101923 once Freshlick approves you, then regenerate.
FRESHLICK_MID = None
FRESHLICK_BRANDS = {"Little Greene", "Crown"}
BRAND_ORDER = ['Farrow & Ball', 'Little Greene', 'Craig & Rose', 'Dulux', "Johnstone's", 'Valspar', 'Lick', 'Crown', 'COAT']
TIER = {'Farrow & Ball': 3, 'Little Greene': 3, 'Craig & Rose': 3, 'Lick': 3, 'COAT': 3, 'Dulux': 2, 'Crown': 2, "Johnstone's": 1, 'Valspar': 1}
TIER_WORD = {3: 'Premium', 2: 'Mid-range', 1: 'Value'}

paints = json.load(open('paints.json'))
# Repair mojibake paint names at load (the U+FFFD replacement char lost the original accent).
# Kept here (not in paints-fixed.json) so the fix ships in a single file. If the source JSON is
# ever corrected, these simply stop matching — harmless. Add new entries if more surface.
_NAME_FIX = {
    'Consomm�': 'Consommé',
    'Ch�teau Mantle': 'Château Mantle',
    'Clementine Cr�me': 'Clementine Crème',
    'Cr�me de Menthe': 'Crème de Menthe',
    'D�j� Blue': 'Déjà Blue',
}
for _p in paints:
    _p['name'] = _NAME_FIX.get(_p.get('name'), _p.get('name'))
N = len(paints)
NBRANDS = len({p['brand'] for p in paints})
BRANDS_WORD = numword(NBRANDS)          # e.g. "nine"  -> "{BRANDS_WORD} UK brands"
OTHERS_WORD = numword(NBRANDS - 1)      # e.g. "eight" -> "the other {OTHERS_WORD} brands"

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
    # Retailer route (Freshlick) takes priority for its brands, once live.
    if FRESHLICK_MID and p['brand'] in FRESHLICK_BRANDS:
        from urllib.parse import quote
        dest = "https://www.freshlick.com/catalogsearch/result/?q=" + quote(f"{p['brand']} {p['name']}")
        return _awin_wrap(FRESHLICK_MID, dest)
    if p.get('url'): return p['url']
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

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23F7F5F0'/%3E"
           "%3Ccircle cx='16' cy='16' r='10' fill='none' stroke='%235E7E8B' stroke-width='4'/%3E"
           "%3Ccircle cx='16' cy='16' r='3.4' fill='%23211F1B'/%3E%3C/svg%3E\">")
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,600'
         '&family=Archivo:wght@400;500;600&display=swap" rel="stylesheet">')
HDR = '<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="lib-link" href="/colours/" aria-label="Colour library"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span><span class="nav-lbl">Colour library</span></a><a class="nav-cta" href="/" aria-label="Open the colour tool"><span class="cta-wheel" aria-hidden="true"></span><span class="nav-lbl">Colour tool</span></a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How matching works</a></div>'
FOOT = ("<span class=\"foot-links\">"
        "<a href=\"/about/\">About</a> \u00b7 "
        "<a href=\"/how-it-works/\">How matching works</a> \u00b7 "
        "<a href=\"/research/\">Research</a> \u00b7 "
        "<a href=\"/contact/\">Contact</a> \u00b7 "
        "<a href=\"/colours/\">Colour library</a> \u00b7 "
        "<a href=\"/match-from-a-photo/\">Match from a photo</a> \u00b7 "
        "<a href=\"/\">Colour tool</a>"
        "</span>"
        "<span class=\"foot-copy\">\u00a9 2026 PaintDial. All rights reserved.</span>"
        "Screen colours are indicative \u2014 always order a tester pot before committing. Colour values are the "
        "brand\u2019s published digital swatches; LRV is estimated. Colour names are the property of their respective "
        "brands. Some links may earn PaintDial a commission at no cost to you.")

# ---------- colour page CSS (current, with all layout fixes) ----------
CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#7E786C;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.top-band{height:12px;background:var(--pc)}
.wrap{max-width:1160px;margin:0 auto;padding:0 32px 72px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--hairline)}
.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px;font-size:13px}
header nav a{font-family:var(--sans);font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:2px}.lib-swatches i{width:8px;height:8px;border-radius:2px;display:block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
.hero{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--hairline);border-radius:16px;overflow:hidden;background:var(--card);margin:28px 0}
@supports (background: color-mix(in srgb, red 10%, white)){.hero-body{background:color-mix(in srgb, var(--pc) 7%, #fff)}}
@media(max-width:640px){.hero{grid-template-columns:1fr}}
.hero-swatch{min-height:320px}
.hero-body{padding:26px 28px}
.eyebrow{font-size:10.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:34px;font-weight:600;letter-spacing:-.01em;line-height:1.1;margin:6px 0 2px}
.facts{display:flex;gap:18px;margin:16px 0 20px;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;flex-wrap:wrap}
.facts b{color:var(--ink)}
.btn{display:inline-block;font-size:14px;font-weight:600;text-decoration:none;padding:11px 20px;border-radius:9px;background:var(--ink);color:var(--paper)}
h2{font-family:var(--serif);font-size:21px;font-weight:600;margin:34px 0 4px}
h2::after{content:'';display:block;width:34px;height:4px;border-radius:2px;background:var(--pc);margin-top:7px}
.sub{font-size:13px;color:var(--muted);margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}
.chip{border:1px solid var(--hairline);border-radius:10px;overflow:hidden;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06);text-decoration:none;color:var(--ink);transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column}
.chip:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(33,31,27,.1)}
.c-swatch{height:74px;flex:none}
.c-body{padding:9px 11px 11px}
.c-name{display:block;font-family:var(--serif);font-size:14.5px;font-weight:600;line-height:1.2;text-wrap:pretty}
.c-brand{display:block;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:2px}
.c-de{display:block;font-size:11px;color:var(--muted);margin-top:5px;font-variant-numeric:tabular-nums}
.c-meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:8px}
.c-badge{font-size:11px;font-weight:600;letter-spacing:.005em;padding:3px 9px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.c-badge.near{color:#2E6E40;background:rgba(46,110,64,.10);border-color:rgba(46,110,64,.24)}
.c-badge.vclose{color:#3E6A78;background:rgba(62,106,120,.10);border-color:rgba(62,106,120,.24)}
.c-badge.close{color:#6F6A5F;background:rgba(33,31,27,.045);border-color:var(--hairline)}
.c-badge.soft{color:#8C8578;background:rgba(33,31,27,.03);border-color:var(--hairline)}
.c-tier{font-size:9.5px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.ladder{display:flex;border:1px solid var(--hairline);border-radius:12px;overflow-x:auto;background:var(--card)}
.rung{flex:1 1 0;min-width:72px;text-decoration:none;color:var(--ink);display:flex;flex-direction:column}
.rung+.rung{border-left:1px solid var(--hairline)}
.rung .r-s{height:56px;flex:none}
.rung .r-b{padding:7px 8px 9px;min-height:58px;min-width:0}
.rung .r-n{font-family:var(--serif);font-size:11.5px;font-weight:600;line-height:1.2;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;height:28px}
.rung .r-br{font-size:9px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.cta{margin-top:40px;border:1px solid var(--hairline);border-radius:14px;background:var(--card);padding:24px 26px;text-align:center}
.cta p{font-size:14px;color:var(--muted);margin:6px 0 14px}
.afftext{font-size:11px;color:var(--muted);margin-top:12px}
.cta-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.colour-summary{font-size:15px;color:var(--ink);max-width:72ch;margin:22px 0 2px;line-height:1.6}
.colour-summary a{color:var(--pc);text-decoration:none;font-weight:600}
.colour-summary a:hover{text-decoration:underline}
.dcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(212px,1fr));gap:12px;margin:16px 0 2px}
.dcard{display:flex;align-items:stretch;border:1px solid var(--hairline);border-radius:12px;overflow:hidden;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06);text-decoration:none;color:var(--ink);transition:transform .12s,box-shadow .12s}
.dcard:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(33,31,27,.10)}
.dc-sw{width:66px;flex:none;align-self:stretch;min-height:80px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.05)}
.dc-body{padding:11px 13px;min-width:0}
.dc-role{display:block;font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--pc)}
.dc-nm{display:block;font-family:var(--serif);font-size:16px;font-weight:600;line-height:1.15;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dc-meta{display:block;font-size:11.5px;color:var(--muted);margin-top:3px}
.pd-heart.btn-save{position:static;top:auto;right:auto;width:auto;height:auto;border-radius:9px;background:#fff;backdrop-filter:none;border:1px solid var(--hairline);box-shadow:0 1px 2px rgba(33,31,27,.05);padding:10px 15px;gap:8px;font-family:var(--sans);font-size:14px;font-weight:600;color:var(--ink)}
.pd-heart.btn-save:hover{transform:none;color:var(--ink);border-color:var(--muted);box-shadow:0 4px 12px rgba(33,31,27,.10)}
.pd-heart.btn-save.on{color:#5E7E8B;border-color:#5E7E8B}
.btn-save .save-on{display:none}
.btn-save.on .save-off{display:none}
.btn-save.on .save-on{display:inline}
footer{margin-top:36px;padding-top:18px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
footer a{color:var(--muted)}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:9px;height:9px}
}

@media(max-width:640px){
.hero-swatch{min-height:200px}
.hero-body{padding:20px 20px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:7px;border-radius:8px;box-shadow:none;gap:0}.nav-lbl{display:none}}
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
        if d < 2: word, bcls = 'near-identical', 'near'
        elif d < 5: word, bcls = 'very close', 'vclose'
        elif d < 10: word, bcls = 'close', 'close'
        else:
            word, bcls = 'related', 'soft'
            if home_i is not None:
                _hd = abs(OH[j]-OH[home_i]) % 360
                _hd = min(_hd, 360-_hd)
                if OC[j] < 0.04 or OC[home_i] < 0.04:
                    word = 'similar tone'
                else:
                    _minc = min(OC[j], OC[home_i])
                    _tol = 28 if _minc >= 0.12 else 22 if _minc >= 0.08 else 16
                    if _hd <= _tol:
                        word = 'same family'
        # Closeness is the payoff, so it leads as a coloured badge; the tier is a
        # quiet market-position label alongside it (never a price claim).
        tier = (f'<span class="c-tier" title="Brand market tier — not a price">{TIER_WORD[TIER[q["brand"]]]}</span>'
                if show_tier else '')
        de = f'<div class="c-meta"><span class="c-badge {bcls}">{word}</span>{tier}</div>'
    return (f'<a class="chip" href="/colours/{slugs[j]}">'
            f'<div class="c-swatch" style="background:{q["hex"]}">{heart(q["name"], q["brand"], q["hex"])}</div>'
            f'<div class="c-body"><span class="c-name">{H.escape(q["name"])}</span>'
            f'<span class="c-brand">{H.escape(q["brand"])}</span>{de}</div></a>')

def decision_card(role, j, dd):
    """A featured 'decision' card for the colour page — the closest / closest value-brand /
    best-premium answer, surfaced above the full ranked grid."""
    q = paints[j]
    return (f'<a class="dcard" href="/colours/{slugs[j]}">'
            f'<span class="dc-sw" style="background:{q["hex"]}"></span>'
            f'<span class="dc-body"><span class="dc-role">{role}</span>'
            f'<span class="dc-nm">{H.escape(q["name"])}</span>'
            f'<span class="dc-meta">{H.escape(q["brand"])} · {TIER_WORD[TIER[q["brand"]]]} · {matchword(dd)}</span>'
            f'</span></a>')

def build_colour_page(i):
    p = paints[i]; lab = LAB[i]
    name = H.escape(p['name']); brand = H.escape(p['brand'])
    slug = slugs[i]
    d = dmatch(i)

    # cross-brand: closest from each OTHER brand, ranked by dE
    xmatch = []
    for b in BRAND_ORDER:
        if b == p['brand']: continue
        mask = BRANDS == b
        j = int(np.argmin(np.where(mask, d, 1e9)))
        xmatch.append((j, d[j]))
    xmatch.sort(key=lambda t: t[1])
    # SEO: name the closest cross-brand match in title/meta (answers the dupe query in the SERP)
    _x0, _x0d = xmatch[0]
    seo_top = f"{H.escape(paints[_x0]['name'])} by {H.escape(paints[_x0]['brand'])}"
    seo_word = matchword(_x0d)
    _depth, _fam = describe(i)   # computed one-line summary (like allpaintcolours' lead sentence)
    # decision layer: closest overall / closest value-brand / closest premium (deduped).
    # NB deliberately NOT "best value" — we hold no live prices, so no savings claim (see research pages).
    _val = [(j, dd) for j, dd in xmatch if TIER[paints[j]['brand']] == 1]
    _prem = [(j, dd) for j, dd in xmatch if TIER[paints[j]['brand']] == 3]
    _bv = min(_val, key=lambda t: t[1]) if _val else None
    _bp = min(_prem, key=lambda t: t[1]) if _prem else None
    _cards = [('Closest overall', _x0, _x0d)]
    if _bv and _bv[0] != _x0:
        _cards.append(('Closest value-brand match', _bv[0], _bv[1]))
    if _bp and _bp[0] != _x0 and (not _bv or _bp[0] != _bv[0]):
        _cards.append(('Closest premium alternative', _bp[0], _bp[1]))
    dcards_html = ''.join(decision_card(r, j, dd) for r, j, dd in _cards)
    seo_also = (f"{H.escape(paints[xmatch[1][0]]['name'])} by {H.escape(paints[xmatch[1][0]]['brand'])} "
                f"and {H.escape(paints[xmatch[2][0]]['name'])} by {H.escape(paints[xmatch[2][0]]['brand'])}")

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
<meta name="description" content="{brand} {name} ({p['hex']}, LRV \u2248 {lrv(L0):.0f}). See its closest matches across {BRANDS_WORD} UK brands, lighter &amp; darker shades, and where to buy a tester.">
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
{FONTS}<style>{CSS}.hero-swatch{{background:{p['hex']}}}{SHORTLIST_CSS}</style></head><body style="--pc:{p['hex']}"><div class="top-band"></div><div class="wrap">
{HDR}
<div class="hero"><div class="hero-swatch">{heart(p['name'], p['brand'], p['hex'])}</div><div class="hero-body">
<span class="eyebrow">{brand}</span><h1>{name}</h1>
<div class="facts"><span>Hex <b>{p['hex']}</b></span><span>LRV <b>\u2248\u2009{lrv(L0):.0f}</b></span><span>Lightness <b>{L0:.0f}/100</b></span></div>
<div class="cta-row"><a class="btn" href="{buy_link(p)}" target="_blank" rel="noopener sponsored">Order {a_an(paints[i]['name'])} {name} tester \u2192</a>{save_button(p['name'], p['brand'], p['hex'])}</div>
<p class="afftext">Opens {brand}\u2019s page, where you can order a tester or a full tin. Affiliate link \u2014 PaintDial may earn a small commission at no cost to you. Always test in your own light before committing.</p>
</div></div>
<p class="colour-summary">{name} is a {_depth} {_fam} from {brand} — hex {p['hex']}, LRV ≈ {lrv(L0):.0f}. Its closest match from another brand is <a href="/colours/{slugs[_x0]}">{seo_top}</a> ({seo_word}), with the full ranked list below.</p>
<div class="dcards">{dcards_html}</div>
<h2>Closest matches from other brands</h2>
<p class="sub">One from each brand, badged by how close the match is. The tier is the brand\u2019s market position, not a price. Tap any to open the full colour.</p>
<div class="grid">{''.join(chip(j, home_lab=lab, show_tier=True, home_i=i) for j, _ in xmatch)}</div>
{alt_link}
<h2>Lighter &amp; darker</h2>
<p class="sub">This colour, stepped evenly from dark to light.</p>
<div class="ladder">{rung_html}</div>
<h2>Pairs well with</h2>
<p class="sub">Sympathetic neutrals for trim and ceilings, plus one contrast accent.</p>
<div class="grid">{''.join(chip(j) for j in neutrals+accents)}</div>
<div class="cta"><h2 style="margin-top:0">Not quite right?</h2>
<p>Use the PaintDial colour tool to walk this colour lighter, darker, warmer or cooler across 5,000+ UK paints.</p>
<a class="btn" href="/">Open the colour tool \u2192</a></div>
<footer>{FOOT}</footer>
</div><div class="top-band"></div><script>{SHORTLIST_JS}</script></body></html>"""
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

def colour_facets(hx):
    """Return (tone, [tags]). Tags are multi-membership: a hue family plus optional
    Neutral/White/Grey/Black. Tone is one of Light/Mid/Dark."""
    L, C, H = _ok_lch(hx)
    fam = family(hx)
    tone = "Light" if L > 0.70 else "Dark" if L < 0.35 else "Mid"
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

LIB_CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#7E786C;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.wrap{max-width:1320px;margin:0 auto;padding:0 32px 80px}
header{padding:16px 0;border-bottom:1px solid var(--hairline);display:flex;justify-content:space-between;align-items:center}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
header .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:2px}.lib-swatches i{width:8px;height:8px;border-radius:2px;display:block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
header nav a.nav-cta:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}
.top{margin:34px 0 6px}
.eyebrow{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:40px;font-weight:600;letter-spacing:-.015em;line-height:1.05;margin:8px 0 0}
.lede{font-size:14.5px;color:var(--muted);max-width:52ch;margin-top:10px}
.fan{display:flex;height:64px;border-radius:12px;overflow:hidden;margin:22px 0 6px;box-shadow:0 1px 2px rgba(33,31,27,.08),0 10px 30px rgba(33,31,27,.09)}
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
.fchip{font-family:var(--sans);font-size:12.5px;padding:6px 12px;border:1px solid var(--hairline);border-radius:20px;background:#fff;color:var(--ink);cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:background .12s,border-color .12s,color .12s}
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
.sw{display:block;text-decoration:none;color:inherit;border:1px solid var(--hairline);border-radius:13px;overflow:hidden;
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
.lib-swatches i{width:9px;height:9px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:7px;border-radius:8px;box-shadow:none;gap:0}.nav-lbl{display:none}}
"""

LIB_HDR = '<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="nav-cta" href="/" aria-label="Open the colour tool"><span class="cta-wheel" aria-hidden="true"></span><span class="nav-lbl">Colour tool</span></a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How matching works</a></div>'

def anchor(fam): return 'f-'+re.sub(r'[^a-z0-9]+', '-', fam.lower().replace('&', 'and')).strip('-')

def build_brand_page(b):
    idxs = [i for i in range(N) if paints[i]['brand'] == b]
    dupes_link = (f'<p class="lede" style="margin-top:6px"><a href="/dupes/{base_slug(b)}" style="color:var(--pc);font-weight:600">See every {H.escape(b)} colour\u2019s closest value or mid-range match, ranked \u2192</a></p>'
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
<meta name="description" content="All {len(idxs)} {be} paint colours. Filter by colour, neutral, or tone \u2014 with cross-brand matches, lighter and darker versions, and where to buy.">
{FAVICON}
{FONTS}<style>{LIB_CSS}</style></head><body><div class="wrap">
{LIB_HDR}
<div class="top"><span class="eyebrow">The colour library</span>
<h1>{be}</h1>
<p class="lede">All {len(idxs)} {be} colours. Filter by colour, type or tone \u2014 a muted shade can be both a colour and a neutral, so nothing hides. Tap any swatch for its cross-brand matches, lighter &amp; darker versions, and where to buy.</p>{dupes_link}</div>
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
<title>The colour library \u2014 every UK paint colour by brand | PaintDial</title>
<meta name="description" content="Browse {N:,} UK paint colours across Farrow &amp; Ball, Little Greene, Dulux, Johnstone's, Valspar and Lick \u2014 each with cross-brand matches and tonal ladders.">
{FAVICON}
{FONTS}<style>{LIB_CSS}</style></head><body><div class="wrap">
{LIB_HDR}
<div class="top"><span class="eyebrow">The colour library</span>
<h1>Every colour, brand by brand</h1>
<p class="lede">{N:,} paints across {BRANDS_WORD} UK brands. Each brand's complete published range, grouped by colour family \u2014 or start from any colour in the <a href="/" style="color:inherit">colour tool</a>.</p></div>
<div class="lib-grid">{cards}</div>
<footer>{FOOT}</footer>
</div><div class="top-band"></div></body></html>"""

# ---------- SEO "alternatives" decision-pages (premium colours only) ----------
ALT_CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#7E786C;--hairline:#E3DFD5;--pc:#5E7E8B;--serif:"Fraunces",Georgia,serif;--sans:"Archivo",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6}
.wrap{max-width:1040px;margin:0 auto;padding:0 32px 72px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--hairline)}
.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo .mark{flex:none}
header nav{display:flex;align-items:center;gap:16px;font-size:13px}
header nav a{font-family:var(--sans);font-weight:500;color:var(--muted);text-decoration:none}header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}header nav a.lib-link:hover{box-shadow:0 4px 12px rgba(33,31,27,.10);transform:translateY(-1px);border-color:var(--muted);color:var(--ink)}.lib-swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:2px}.lib-swatches i{width:8px;height:8px;border-radius:2px;display:block}
header nav a:hover{color:var(--ink)}
header nav a.nav-cta{display:inline-flex;align-items:center;gap:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;padding:6px 14px 6px 8px;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05);transition:box-shadow .12s,transform .12s,border-color .12s}.cta-wheel{width:16px;height:16px;border-radius:50%;flex:none;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);box-shadow:inset 0 0 0 3px #fff,inset 0 0 0 4px rgba(0,0,0,.06)}
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
.a-rank{flex:none;width:30px;text-align:center;font-family:var(--serif);font-size:14px;font-weight:600;color:var(--muted)}.alt{display:flex;align-items:center;gap:12px;border:1px solid var(--hairline);border-radius:12px;background:var(--card);box-shadow:0 1px 2px rgba(33,31,27,.06);padding:0 14px 0 10px;overflow:hidden;text-decoration:none;color:inherit;transition:transform .12s,box-shadow .12s}
.alt:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(33,31,27,.1)}
.a-sw{width:72px;align-self:stretch;min-height:84px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.05);flex:none}
.a-body{flex:1;min-width:0;padding:13px 0}
.a-nm{display:block;font-family:var(--serif);font-size:16px;font-weight:600;line-height:1.2;text-wrap:pretty}
.a-br{display:block;font-size:11px;letter-spacing:.03em;text-transform:uppercase;color:var(--muted);margin:2px 0 4px}
.a-note{display:block;font-size:13px;color:var(--ink)}
.a-hex{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;align-self:flex-start;padding-top:13px}
.verdict{border:1px solid var(--hairline);border-radius:12px;padding:15px 17px;margin:16px 0 4px;background:color-mix(in srgb,var(--pc) 5%,var(--card))}
.verdict h3{font-family:var(--serif);font-size:16px;font-weight:600;margin:0 0 6px;display:flex;align-items:center;gap:8px}
.verdict h3::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--pc);flex:0 0 auto}
.verdict p{font-size:14px;color:var(--ink);margin:0;line-height:1.65}
.faq .q{border-top:1px solid var(--hairline);padding:16px 0}
.faq h3{font-family:var(--serif);font-size:16px;font-weight:600;margin-bottom:5px}
.faq p{font-size:14px;color:var(--ink)}
.cta{margin-top:30px;border:1px solid var(--hairline);border-radius:13px;background:var(--card);padding:22px;text-align:center}
.cta a{display:inline-block;margin-top:12px;font-size:14px;font-weight:600;text-decoration:none;background:var(--ink);color:var(--paper);padding:11px 20px;border-radius:9px}
.afftext{font-size:11px;color:var(--muted);margin-top:14px}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:640px){h1{font-size:28px}.alts{grid-template-columns:1fr}}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:9px;height:9px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:7px;border-radius:8px;box-shadow:none;gap:0}.nav-lbl{display:none}}
"""
ALT_BRANDS = {b for b in BRAND_ORDER if TIER[b] == 3}  # Farrow & Ball, Little Greene, Lick, COAT
AVAIL = {'Dulux': 'widely available', 'Crown': 'widely available', "Johnstone's": 'widely available',
         'Valspar': 'widely available at B&amp;Q', 'Little Greene': 'available online or in-store',
         'Lick': 'ordered direct', 'COAT': 'ordered direct', 'Farrow & Ball': 'available online or in-store'}

DESC_WORD = {'Reds': 'red', 'Oranges': 'orange', 'Yellows': 'yellow', 'Greens': 'green',
             'Teals': 'blue-green', 'Blues': 'blue', 'Purples': 'purple', 'Pinks': 'pink',
             'Browns': 'brown', 'Whites & neutrals': 'off-white', 'Greys': 'grey',
             'Blacks': 'near-black'}

def describe(i):
    """Human-facing shade wording for the alternatives pages.
    Uses family() -- the same OKLab-calibrated classifier as the library -- so the two can
    never disagree. This previously used CIELab hue with HSL-era band edges, which called
    Stiffkey Blue a 'deep purple', Sulking Room Pink a 'light orange' and pure blue 'pink'."""
    l = L[i]
    depth = 'pale' if l > 78 else 'light' if l > 60 else 'mid-toned' if l > 38 else 'deep' if l > 18 else 'very dark'
    fam = DESC_WORD[family(paints[i]['hex'])]
    if fam == 'off-white':
        fam = 'off-white' if l > 80 else 'neutral'
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
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#7E786C;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55}
.wrap{max-width:1100px;margin:0 auto;padding:0 32px 80px}
header{display:flex;align-items:center;justify-content:space-between;padding:20px 0 16px;border-bottom:1px solid var(--hairline);margin-bottom:34px}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo-dial{width:22px;height:22px;border-radius:50%;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);position:relative}
.logo-dial::after{content:"";position:absolute;inset:5px;border-radius:50%;background:#fff;border:2px solid #211F1B}
header nav{display:flex;gap:18px;align-items:center}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}
header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05)}
.lib-swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:2px}.lib-swatches i{width:8px;height:8px;border-radius:2px;display:block}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-size:36px;font-weight:600;letter-spacing:-.012em;line-height:1.08;margin:8px 0 10px}
.sub{font-size:14.5px;color:var(--muted);max-width:640px;margin-bottom:8px}
.method{font-size:12.5px;color:var(--muted);max-width:640px;margin-bottom:30px}
.method a{color:var(--pc)}
.dupe-list{display:flex;flex-direction:column;gap:10px}
.row{display:grid;grid-template-columns:34px 1fr 24px 1fr;gap:0;align-items:stretch;background:var(--card);border:1px solid var(--hairline);border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;transition:box-shadow .12s,transform .12s}
.row:hover{box-shadow:0 6px 18px rgba(33,31,27,.10);transform:translateY(-1px)}
.rank{display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-size:14px;font-weight:600;color:var(--muted);background:color-mix(in srgb,var(--paper) 60%,#fff);border-right:1px solid var(--hairline)}
.half{display:flex;align-items:center;gap:12px;padding:10px 14px;min-width:0}
.half .sw{width:64px;height:44px;border-radius:8px;flex:none;border:1px solid rgba(33,31,27,.08)}
.half .tx{min-width:0}
.half .nm{display:block;font-family:var(--serif);font-size:15.5px;font-weight:600;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.half .br{display:block;font-size:10.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-top:3px}
.arrow{display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px}
.badge{margin-left:auto;flex:none;font-size:10.5px;font-weight:600;letter-spacing:.05em;padding:4px 9px;border-radius:99px;border:1px solid var(--hairline);color:var(--muted);background:var(--paper);white-space:nowrap}
.badge.good{color:#3E7A4C;border-color:#3E7A4C33;background:#3E7A4C0d}
.brands-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:30px}
.brands-nav a{font-size:12.5px;font-weight:600;color:var(--ink);text-decoration:none;padding:7px 14px;background:#fff;border:1px solid var(--hairline);border-radius:99px}
.brands-nav a.on{background:var(--ink);color:#fff;border-color:var(--ink)}
footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--hairline);font-size:11.5px;color:var(--muted);line-height:1.6}
footer a{color:var(--muted)}
.foot-links{display:block;margin-bottom:6px}.foot-links a{color:var(--pc);font-weight:600;text-decoration:none}.foot-links a:hover{text-decoration:underline}
.foot-copy{display:block;margin-bottom:10px;color:var(--muted)}
@media(max-width:760px){.row{grid-template-columns:28px 1fr}.arrow{display:none}.half{padding:9px 11px;display:grid;grid-template-columns:46px 1fr;column-gap:12px;align-items:center}.half:last-of-type{border-top:1px dashed var(--hairline)}.half .sw{width:46px;height:36px;grid-row:1 / span 2}.half .tx{grid-column:2;min-width:0}.badge{grid-column:2;justify-self:start;margin:4px 0 0}h1{font-size:28px}.wrap{padding:0 18px 60px}}

@media(max-width:640px){
header{flex-wrap:wrap;row-gap:6px;padding:12px 0}
header nav{width:100%;gap:8px;justify-content:flex-start}header nav:only-child,header nav:has(> :only-child){width:auto;justify-content:flex-end;margin-left:auto}
header nav a.lib-link,header nav a.nav-cta{font-size:12px;padding:5px 10px 5px 6px;white-space:nowrap}
.lib-swatches i{width:9px;height:9px}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:7px;border-radius:8px;box-shadow:none;gap:0}.nav-lbl{display:none}}
"""

DUPE_TARGETS = [b for b in BRAND_ORDER if TIER[b] == 3]

def build_dupes_page(brand):
    bslug = base_slug(brand)
    bname = H.escape(brand)
    idxs = [i for i in range(N) if paints[i]['brand'] == brand]
    rows = []
    for i in idxs:
        d = dmatch(i)
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
        return (f'<a class="row" href="/colours/{slugs[i]}">'
                f'<span class="rank">{rank}</span>'
                f'<span class="half"><span class="sw" style="background:{p["hex"]}"></span>'
                f'<span class="tx"><span class="nm">{H.escape(p["name"])}</span>'
                f'<span class="br">{H.escape(p["brand"])}</span></span></span>'
                f'<span class="arrow">\u2192</span>'
                f'<span class="half"><span class="sw" style="background:{q["hex"]}"></span>'
                f'<span class="tx"><span class="nm">{H.escape(q["name"])}</span>'
                f'<span class="br">{H.escape(q["brand"])} \u00b7 {TIER_WORD[TIER[q["brand"]]]}</span></span>'
                f'<span class="badge{badge_cls}">{w}</span></span></a>')

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
{FONTS}<style>{DUPES_CSS}</style></head><body><div class="wrap">
<header><a class="logo" href="/"><span class="logo-dial"></span>PaintDial</a>
<nav><a class="lib-link" href="/colours/" aria-label="Colour library"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span><span class="nav-lbl">Colour library</span></a><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How matching works</a></div>
<span class="eyebrow">Ranked dupes</span>
<h1>Every {bname} colour\u2019s closest value or mid-range match, ranked</h1>
<p class="sub">All {len(rows)} {bname} colours, each paired with its single closest match from a value or mid-range brand \u2014 ranked from the strongest match down. Tap any row to see the full colour page, more matches, and where to buy.</p>
<p class="method">Matches are computed from each brand\u2019s published digital swatches using perceptual colour distance. Screen colours are indicative \u2014 always order tester pots of both before committing.</p>
<div class="brands-nav">{nav}</div>
<div class="dupe-list">{body}</div>
<footer>{FOOT}</footer>
</div></body></html>"""



# ---------- static trust pages: how it works + about ----------
PAGES_CSS = """
:root{--paper:#F7F5F0;--card:#fff;--ink:#211F1B;--muted:#7E786C;--hairline:#E3DFD5;--pc:#5E7E8B;
--serif:"Fraunces",Georgia,serif;--sans:"Archivo",-apple-system,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.65}
.wrap{max-width:760px;margin:0 auto;padding:0 28px 80px}
header{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:1px solid var(--hairline);margin-bottom:38px}
header a.logo{display:inline-flex;align-items:center;gap:9px;font-family:var(--serif);font-size:20px;font-weight:600;color:#5E7E8B;text-decoration:none}
.logo-dial{width:22px;height:22px;border-radius:50%;background:conic-gradient(from 90deg,#e0574f,#e6a02e,#c9c94f,#8a9d80,#5e7e8b,#7a6a9e,#b7788d,#e0574f);position:relative}
.logo-dial::after{content:"";position:absolute;inset:5px;border-radius:50%;background:#fff;border:2px solid #211F1B}
header nav{display:flex;gap:12px;align-items:center}
header nav a{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);text-decoration:none}
header nav a.lib-link{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-weight:600;padding:6px 12px 6px 7px;background:#fff;border:1px solid var(--hairline);border-radius:9px;box-shadow:0 1px 2px rgba(33,31,27,.05)}
.lib-swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:2px}.lib-swatches i{width:8px;height:8px;border-radius:2px;display:block}
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
.lib-swatches i{width:9px;height:9px}
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
.pair-blocks{display:flex;height:132px;border-radius:11px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)}
.pair-half{flex:1;position:relative;text-decoration:none;display:flex;align-items:flex-end;padding:12px 13px;transition:flex .18s ease}
.pair-half:hover{flex:1.06}
.pair-lab{font-size:12.5px;line-height:1.35;opacity:.94}
.pair-lab b{display:block;font-family:var(--serif);font-size:15px;font-weight:600}
.pair-lab span{font-size:11px;opacity:.8}
.pair figcaption{font-size:11.5px;color:var(--muted);margin-top:6px}
.stack{display:flex;height:44px;border-radius:9px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.08);margin:14px 0 8px}
.stack i{display:block;height:100%}
.stack-key{font-size:11.5px;color:var(--muted);margin:0 0 18px}
.bignum{font-family:var(--serif);font-size:34px;font-weight:600;line-height:1.15;margin:4px 0 2px}
.bignum small{font-size:15px;color:var(--muted);font-family:var(--sans);font-weight:400;display:block;margin-top:3px}
.rsch-cards{display:grid;gap:14px;margin:22px 0}
.rsch-card{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--hairline);border-radius:12px;padding:20px 22px;transition:transform .15s}
.rsch-card:hover{transform:translateY(-2px)}
.rsch-card b{font-family:var(--serif);font-size:19px;font-weight:600;display:block;margin-bottom:5px}
.rsch-card span{font-size:13.5px;color:var(--muted)}
.uq-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:9px;margin:14px 0 18px}
.uq{display:flex;flex-direction:column;justify-content:flex-end;min-height:104px;padding:11px;border-radius:10px;
text-decoration:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.09);transition:transform .12s}
.uq:hover{transform:translateY(-2px)}
.uq b{font-family:var(--serif);font-size:14px;font-weight:600;line-height:1.25}
.uq span{font-size:10.5px;opacity:.78}
.uq-near{margin-top:3px;opacity:.6}
.bars{margin:14px 0 18px}
.brow{display:grid;grid-template-columns:118px 1fr 42px 118px;align-items:center;gap:10px;padding:5px 0;font-size:13px}
.btrack{background:rgba(0,0,0,.06);border-radius:5px;height:9px;overflow:hidden}
.btrack i{display:block;height:100%;background:var(--pick,#5E7E8B);border-radius:5px}
.bval{font-weight:600;text-align:right}
.bnote{font-size:11px;color:var(--muted)}
@media(max-width:560px){
.pair-blocks{height:112px}.pair-lab b{font-size:13.5px}
.uq-grid{grid-template-columns:1fr 1fr;gap:7px}
.brow{grid-template-columns:82px 1fr 38px;gap:7px;font-size:12px}.bnote{display:none}
}
.head-nav{font-family:var(--sans);font-size:12.5px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap;transition:color .12s}.head-nav:hover{color:var(--ink)}@media(max-width:560px){.head-nav{display:none}}
.mnav{display:none}@media(max-width:560px){.mnav{display:flex;gap:18px;align-items:center;padding:7px 0 9px;border-bottom:1px solid var(--hairline);overflow-x:auto;-webkit-overflow-scrolling:touch}.mnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--muted);text-decoration:none;white-space:nowrap}.mnav a:active{color:var(--ink)}}
@media(max-width:560px){header{align-items:center!important;flex-wrap:nowrap!important;gap:10px;padding:13px 0 11px}header nav{width:auto!important;margin-left:auto;justify-content:flex-end!important;flex:0 0 auto}.logo{font-size:21px}.lib-link,.nav-cta{font-size:10.5px;padding:7px;border-radius:8px;box-shadow:none;gap:0}.nav-lbl{display:none}}
"""

def _page_shell(title, desc, path, body):
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | PaintDial</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{path}">
{FONTS}<style>{PAGES_CSS}</style></head><body><div class="wrap">
<header><a class="logo" href="/"><span class="logo-dial"></span>PaintDial</a>
<nav><a class="lib-link" href="/colours/" aria-label="Colour library"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span><span class="nav-lbl">Colour library</span></a><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How matching works</a></div>
{body}
<footer>{FOOT}</footer>
</div></body></html>"""

def build_method_page():
    body = f"""<span class="eyebrow">Methodology</span>
<h1>How PaintDial matches colours</h1>
<p>PaintDial compares {N:,} paints from {BRANDS_WORD} UK brands and finds the closest matches to any colour \u2014 across every brand at once, not just one manufacturer\u2019s range. Here\u2019s exactly how it works, and what its limits are.</p>

<h2>Where the colour data comes from</h2>
<p>Every colour in the library uses the brand\u2019s own published digital swatch \u2014 the colour value each manufacturer provides for its paints on the web. We don\u2019t re-photograph or estimate colours ourselves. LRV (light reflectance value) shown on colour pages is estimated from the swatch rather than measured from paint.</p>

<h2>How matches are calculated</h2>
<p>Matches are ranked by perceptual colour difference \u2014 a measure of how different two colours look to the human eye \u2014 computed in the OKLab colour space, which handles hue more faithfully than older formulas (blues stay blue as they lighten, and purples don\u2019t get mistaken for blues). Our ranking also weights hue more heavily than lightness: a paint that\u2019s a touch lighter or darker still reads as the same colour, while one that\u2019s drifted in hue reads as a different colour \u2014 so matches keep the colour\u2019s character, and the lighter/darker ladder covers depth.</p>

<h2>What the match labels mean</h2>
<ul>
<li><span class="label">Near-identical</span> \u2014 a difference most people can\u2019t see on a wall. On screen the swatches look the same.</li>
<li><span class="label">Very close</span> \u2014 a difference you\u2019d struggle to spot unless the two were side by side.</li>
<li><span class="label">Close</span> \u2014 visibly similar; the same decorating intent, with a slight shift in tone or depth.</li>
<li><span class="label">Same family</span> \u2014 further apart, but genuinely the same hue family (checked in OKLab, not just nearby in the list).</li>
<li><span class="label">Related / similar tone</span> \u2014 close in overall feel, but honestly not the same family. We label these rather than overclaim.</li>
</ul>

<h2>RAL Classic and BS 4800 codes</h2>
<p>Trade and specification colours are covered too: type a RAL Classic code (say, \u201cRAL 7016\u201d) or a British Standard BS 4800 code (say, \u201c08 B 15\u201d, Magnolia) \u2014 or a colour name \u2014 into the tool\u2019s search and PaintDial shows every brand\u2019s nearest paints to it. Our RAL values are derived from the standard\u2019s published CIELAB coordinates; our BS 4800 values are derived from measured colour data (averaged spectrophotometer readings, standardised to D65 / CIE 1964). Both are physical colour standards, so on-screen values are approximate conversions \u2014 for binding samples, use an official RAL or British Standard fan deck.</p>

<h2>Why photo matching is approximate</h2>
<p>The \u201cmatch from a photo\u201d tool reads the pixel colour from your image. That pixel is shaped by the room\u2019s lighting, the camera\u2019s processing, and your screen \u2014 so treat photo matches as a strong starting point, not a guarantee. The same wall photographed at noon and at dusk will match to different paints.</p>

<h2>Why you should still order testers</h2>
<p>Screen colours are indicative. Real paint changes with sheen, light, and the surface underneath it \u2014 and every screen shows colour slightly differently. Before committing to any colour (or any match), order tester pots of both and look at them in the room they\u2019ll live in, in daylight and lamplight.</p>

<p class="muted">Found something that looks wrong? <a href="/contact/">Tell us</a> \u2014 accuracy is the whole point of PaintDial, and corrections are genuinely welcome.</p>"""
    return _page_shell("How PaintDial matches colours",
        "Where PaintDial's colour data comes from, how cross-brand matches are calculated, what the match labels mean, and why you should still order testers.",
        "/how-it-works/", body)

def ink_on(i):
    """Readable text colour over a swatch, from its OKLab lightness."""
    return '#211F1B' if OL[i] > 0.62 else '#FFFFFF'


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
                f'<span>{H.escape(paints[j]["brand"])} \u00b7 {paints[j]["hex"]}</span></span></a>')
    dupe_rows = ''.join(
        f'<figure class="pair"><div class="pair-blocks">{half(i)}{half(k)}</div>'
        f'<figcaption>\u0394E {_d:.1f} \u2014 the published digital swatches are '
        f'virtually indistinguishable.</figcaption></figure>'
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

    body = f"""<span class="eyebrow">Research</span>
<h1>The UK Paint Match Index</h1>
<p>We compared every one of the {N:,} colours published by {len(brands)} UK paint brands against every other \u2014 millions of pairwise comparisons \u2014 to answer one question: how many premium paint colours are genuinely unique, and how many already have a near-identical twin?</p>
<p class="muted">Updated automatically from PaintDial\u2019s live colour library. Last built {TODAY}.</p>

<h2>1. Almost every premium colour has a close alternative</h2>
<p><b>{pct_id}%</b> of premium colours ({n_id} of {len(prem)}) have a <b>near-identical</b> match from a value brand. <b>{pct_vc}%</b> ({n_vc}) have at least a <b>very close</b> one.</p>
<p>Put plainly: based on the brands\u2019 own published digital swatches, if you want a premium colour there\u2019s a {pct_vc}% chance another brand already makes something very close to it. <a href="/">Check any colour in the tool \u2192</a></p>

<h2>2. The closest pairs differ by a single step in their hex code</h2>
{dupe_rows}

<h2>3. Only {len(uniq)} premium colours can\u2019t be matched \u2014 and they\u2019re all one brand</h2>
<p>Of {len(prem)} premium colours, just <b>{len(uniq)}</b> have no very-close match from any other brand. Every one belongs to <b>{uniq_brands.most_common(1)[0][0]}</b>.</p>
<div class="uq-grid">{uniq_rows}</div>

<h2>4. The reason: British paint barely goes dark</h2>
<p>Only <b>{len(deep)} of {N:,}</b> colours across all {len(brands)} brands are genuinely deep. By brand: {deep_rows}.</p>
<p>That single fact explains the finding above. {uniq_brands.most_common(1)[0][0]} isn\u2019t unmatchable because it\u2019s premium \u2014 it\u2019s unmatchable because it\u2019s the only brand making colours that dark. <b>Depth, not prestige, is what can\u2019t be copied.</b></p>

<h2>5. Whose palette is most Farrow &amp; Ball-like?</h2>
<p>Raw counts favour whoever publishes most colours. Corrected for range size \u2014 closest-match wins per 100 colours of each brand\u2019s own range \u2014 the picture changes:</p>
<div class="bars">{fb_rows}</div>
<p>Volume and aim are different things. <a href="/dupes/farrow-and-ball">See every Farrow &amp; Ball colour\u2019s closest match \u2192</a></p>

<h2>Method</h2>
<p>Every colour is each brand\u2019s <a href="/how-it-works/">own published digital swatch</a> \u2014 we don\u2019t photograph or estimate colours. Differences are computed in <b>OKLab</b>, weighting hue drift twice and discounting lightness, because a paint a shade lighter still reads as the same colour while one that\u2019s drifted in hue reads as a different one. Thresholds are the ones used across the site: near-identical = \u0394E&nbsp;&lt;&nbsp;2, very close = \u0394E&nbsp;&lt;&nbsp;5. \u201cGenuinely deep\u201d means OKLab lightness below {DEEP}.</p>

<h2>What this doesn\u2019t claim</h2>
<ul>
<li><b>No price claims.</b> PaintDial holds no live pricing, so we make no statements about savings. \u201cValue brand\u201d describes market tier, not price.</li>
<li><b>Screen, not wall.</b> These are digital swatch comparisons. Real paint differs by finish, pigment and light \u2014 a near-identical hex is a shortlist, not a guarantee. Always order testers.</li>
<li><b>Range sizes differ enormously</b> ({max(len(v) for v in idx_by_brand.values()):,} colours vs {min(len(v) for v in idx_by_brand.values())}). Every brand-level claim here is corrected for that.</li>
<li><b>Published ranges only.</b> Mix-to-order and bespoke matching are excluded.</li>
</ul>
<p class="muted">Companion study: <a href="/paint-choice-index/">The UK Paint Choice Index</a> \u2014 how much genuine choice Britain\u2019s paint colours actually offer. Journalists and researchers: the underlying comparisons are all on the site, colour by colour. Questions or corrections \u2014 <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("The UK Paint Match Index",
        f"We compared {N:,} UK paint colours across {len(brands)} brands. {pct_vc}% of premium colours have a very close match from another brand \u2014 and only {len(uniq)} can\u2019t be matched at all.",
        "/paint-match-index/", body)


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
                f'<span>{H.escape(paints[j]["brand"])} \u00b7 {paints[j]["hex"]}{note}</span></span></a>')

    # exact-hex showcase pairs: Craig & Rose pair + Dulux's biggest same-hex group
    def find(brand, name):
        return next(i for i in range(N) if paints[i]['brand'] == brand and paints[i]['name'] == name)
    showcase = ''
    try:
        cr1, cr2 = find('Craig & Rose', 'Regency White'), find('Craig & Rose', 'Isabelline')
        showcase += (f'<figure class="pair"><div class="pair-blocks">{half(cr1)}{half(cr2)}</div>'
                     f'<figcaption>Two Craig &amp; Rose colours, one published value \u2014 {paints[cr1]["hex"]}. '
                     f'There is no join to find.</figcaption></figure>')
    except StopIteration:
        pass
    du = [(h_, v) for h_, v in hex_groups.get('Dulux', [])]
    if du:
        bigh = max(du, key=lambda t: t[1])[0]
        group = [i for i in range(N) if paints[i]['brand'] == 'Dulux' and paints[i]['hex'].upper() == bigh][:4]
        if len(group) >= 3:
            showcase += (f'<figure class="pair"><div class="pair-blocks">{"".join(half(j) for j in group)}</div>'
                         f'<figcaption>{len(group)} Dulux names, one published value \u2014 {bigh}.</figcaption></figure>')

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

    body = f"""<span class="eyebrow">Research</span>
<h1>The UK Paint Choice Index</h1>
<p>Britain sells {N:,} paint colours across {len(brands)} brands. This study asks a simple question of all of them: <b>how much genuine choice is that?</b></p>
<p class="muted">Computed automatically from PaintDial\u2019s live colour library, using the same thresholds as every page on this site. Last built {TODAY}.</p>

<h2>1. Half of Britain\u2019s paint colours are duplicates</h2>
<p class="bignum">{distinct:,} of {N:,}<small>colours are genuinely distinct at our near-identical threshold</small></p>
<p>You could remove <b>{dup_pct}%</b> of the colours on sale in Britain and every one removed would still have a near-identical match among the survivors. Without any clustering at all: <b>{round(100*twin_any/N)}%</b> of colours have a near-identical twin somewhere on the market, and <b>{round(100*twin_cross/N)}%</b> have one from a <em>different brand</em>. <a href="/">Check any colour\u2019s twins in the tool \u2192</a></p>

<h2>2. {exact_total} colours share an exact value with a sibling from their own brand</h2>
<p>Not near-identical \u2014 identical. The same published swatch value, sold under two names by the same brand:</p>
{showcase}
<p class="muted">Dulux accounts for most of these: {len(hex_groups.get('Dulux', []))} of its published values appear under more than one name.</p>

<h2>3. Inside the biggest ranges, most colours have an in-house twin</h2>
<p>Share of each brand\u2019s own range with a near-identical twin <em>from the same brand</em>:</p>
<div class="bars">{inb_rows}</div>
<p>Bigger ranges duplicate more \u2014 partly simple arithmetic: publish {max(brand_n.values()):,} colours into a finite space and overlap follows. But it means a bigger colour card is not proportionally more choice.</p>

<h2>4. The colour Britain doesn\u2019t sell</h2>
<p>Take every colour a standard screen can display and ask: does any UK paint come <b>very close</b> to it (our site-wide \u0394E&nbsp;&lt;&nbsp;5)? The answer is yes for just <b>{cover_pct}%</b> of them. The missing colour isn\u2019t evenly spread \u2014 it is overwhelmingly the vivid end of <b>purple ({unc_purple}% of the gap), blue ({unc_blue}%) and the reds and pinks ({unc_pink}%)</b>.</p>
<p>Part of that is physics: screens emit light and pigment can\u2019t, so no paint will ever match a glowing violet. But the pattern holds <em>inside</em> paint itself: British paint pushes red to a peak chroma of {red_max:.2f}, yet purple stops at {purp_max:.2f} \u2014 less than half. <b>{red_vivid} red paints exceed a chroma of 0.10. Exactly {purp_vivid} purple does.</b></p>

<h2>Method</h2>
<p>Every colour is each brand\u2019s <a href="/how-it-works/">own published digital swatch</a>. Distinctness uses greedy clustering at the site\u2019s published near-identical threshold (\u0394E&nbsp;&lt;&nbsp;2 in our hue-weighted OKLab metric), averaged over five seeded random orderings; the spread across orderings is about 1%, so the count is not an artefact of ordering. Colour families are the site\u2019s own live classification \u2014 the same rule that files every colour in the <a href="/colours/">library</a>. Screen-colour coverage samples the sRGB gamut uniformly in OKLab volume (40,000 seeded points) and measures distance to the nearest paint with the site\u2019s own metric and thresholds.</p>

<h2>What this doesn\u2019t claim</h2>
<ul>
<li><b>Published swatch values, not paint in tins.</b> Brands may distinguish colours in ways a swatch value doesn\u2019t capture \u2014 finish, texture, opacity. Two identical values are identical <em>on screen</em>.</li>
<li><b>Duplication is not an accusation.</b> Much of it is arithmetic \u2014 large ranges into a finite colour space \u2014 and some may be deliberate continuity across renamed ranges.</li>
<li><b>Screens glow; pigment doesn\u2019t.</b> Some of the \u201cmissing\u201d colour in finding 4 is physically out of reach for any paint. The red-versus-purple contrast, measured within paint alone, does not depend on that comparison.</li>
<li><b>No price claims.</b> PaintDial holds no live pricing.</li>
</ul>
<p class="muted">Companion study: <a href="/paint-match-index/">The UK Paint Match Index</a> \u2014 how closely premium colours can be matched across brands. Questions or corrections \u2014 <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("The UK Paint Choice Index",
        f"Britain sells {N:,} paint colours. Only {distinct:,} are genuinely distinct \u2014 and just {purp_vivid} purple is genuinely vivid.",
        "/paint-choice-index/", body)


def build_photo_page():
    """Dedicated SEO landing page for 'match a paint colour from a photo'. It does NOT
    duplicate the tool — it ranks for the query and funnels into the homepage tool (/#photo)."""
    cta = '<a class="pf-cta" href="/#photo">\U0001F4F7️ Upload a photo →</a>'
    faqs = [
        ("How accurate is matching a paint colour from a photo?",
         "It’s a strong starting point, not a guarantee. A photo’s colour is shaped by the "
         "room’s lighting, your camera and your screen, so treat the match as a shortlist and always "
         "order a tester pot to check in the room itself."),
        ("What kind of photo works best?",
         "A flat, evenly-lit patch of the colour, shot in daylight without glare or heavy shadow. Avoid "
         "filtered or very dark images — the truer the light, the closer the match."),
        (f"Which paint brands does it match against?",
         f"All {N:,} colours across {BRANDS_WORD} UK brands at once — Farrow &amp; Ball, Little Greene, "
         "Craig &amp; Rose, Dulux, Johnstone’s, Valspar, Lick, Crown and COAT — ranked by how close each is."),
    ]
    faq_ld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":re.sub('<[^>]+>','',a)}} for q,a in faqs]}
    faq_html = ''.join(f'<div class="q"><h3>{q}</h3><p>{a}</p></div>' for q,a in faqs)
    body = f"""<style>
.pf-cta{{display:inline-block;margin:8px 0 2px;font-size:15px;font-weight:600;text-decoration:none;background:var(--ink);color:var(--paper);padding:13px 24px;border-radius:10px}}
.pf-cta:hover{{filter:brightness(1.08)}}
.pf-steps{{margin:18px 0 8px;padding:0;counter-reset:s;list-style:none}}
.pf-steps li{{position:relative;padding:0 0 14px 46px;font-size:15px;max-width:640px}}
.pf-steps li::before{{counter-increment:s;content:counter(s);position:absolute;left:0;top:-3px;width:30px;height:30px;border-radius:50%;background:var(--pc);color:#fff;font-family:var(--serif);font-weight:600;display:flex;align-items:center;justify-content:center}}
.q h3{{font-family:var(--serif);font-size:16px;font-weight:600;margin:16px 0 4px}}
</style>
<span class="eyebrow">Colour tool</span>
<h1>Match a paint colour from a photo</h1>
<p>Seen a colour you love — on a wall, a fabric, a front door? Upload a photo and PaintDial finds the
nearest paint to it across {N:,} colours from {BRANDS_WORD} UK brands at once, ranked by how close each one
is. Free, and no sign-up.</p>
<p>{cta}</p>
<h2>How it works</h2>
<ol class="pf-steps">
<li><b>Upload your photo.</b> Open the tool and tap “Match from a photo”, then pick any image from your phone or computer.</li>
<li><b>Tap the colour you want.</b> Touch or drag anywhere on the image to choose the exact spot — a wall, a cushion, a leaf.</li>
<li><b>See the nearest paints, ranked.</b> PaintDial shows the closest match from every UK brand, with lighter and darker options and where to order a tester.</li>
</ol>
<p>{cta}</p>
<h2>Why a photo match is a starting point</h2>
<p>The colour in a photo is shaped by the room’s light, your camera and your screen — the same wall at
noon and at dusk can read as different paints. So PaintDial treats a photo as a strong shortlist, never the
last word. Before committing, <a href="/how-it-works/">order a tester pot</a> and look at it in the room it’s
for, in daylight and lamplight.</p>
<h2>Common questions</h2>
<div class="faq">{faq_html}</div>
<p class="muted" style="margin-top:20px"><a href="/">Open the colour tool →</a> · <a href="/how-it-works/">How matching works</a></p>
{_ldjson(faq_ld)}"""
    return _page_shell("Match a paint colour from a photo",
        f"Upload a photo and find the nearest paint colour across {N:,} shades from {BRANDS_WORD} UK brands "
        "— Farrow &amp; Ball, Dulux, Little Greene and more. Free, no sign-up. Always order a tester.",
        "/match-from-a-photo/", body)

def build_research_hub():
    brands = sorted({p['brand'] for p in paints})
    body = f"""<span class="eyebrow">PaintDial</span>
<h1>Research</h1>
<p>Original studies computed from PaintDial\u2019s live library \u2014 {N:,} colours across {len(brands)} UK brands, compared with the same metric and thresholds used on every page of this site. Each study rebuilds automatically as brands are added.</p>
<div class="rsch-cards">
<a class="rsch-card" href="/paint-match-index/"><b>The UK Paint Match Index</b><span>How closely can premium paint colours be matched across brands \u2014 and which colours can\u2019t be matched at all?</span></a>
<a class="rsch-card" href="/paint-choice-index/"><b>The UK Paint Choice Index</b><span>Britain sells {N:,} paint colours. How much genuine choice is that \u2014 and what colour does Britain not sell?</span></a>
</div>
<p class="muted">Journalists and researchers: every underlying comparison is public, colour by colour, across the site. Questions or corrections \u2014 <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("Research", 
        f"Original colour research computed from {N:,} UK paint colours across {len(brands)} brands.",
        "/research/", body)


def build_about_page():
    body = f"""<span class="eyebrow">About</span>
<h1>About PaintDial</h1>
<p>PaintDial started with a familiar frustration: every paint brand\u2019s website has a lovely colour tool \u2014 that only shows you <em>their</em> paints. If you\u2019ve fallen for a designer colour but want to see what every other brand\u2019s nearest equivalent looks like, you end up with a dozen tabs open and no honest way to compare.</p>
<p>So PaintDial does one thing: it puts {N:,} paints from {BRANDS_WORD} UK brands \u2014 Farrow &amp; Ball, Little Greene, Craig &amp; Rose, Dulux, Johnstone\u2019s, Valspar, Lick, Crown and COAT \u2014 into one independent tool. Pick any colour, match one from a photo, or search a paint you already know, and see the closest equivalents from every brand side by side, honestly labelled.</p>
<p>It\u2019s an independent, one-person project. PaintDial isn\u2019t owned by, sponsored by, or affiliated with any paint brand, and no brand can pay to change how well its colours match. The matching is <a href="/how-it-works/">pure colour science</a>, applied the same way to every paint in the library.</p>

<h2>How PaintDial is funded</h2>
<p>Some \u201cwhere to buy\u201d links are affiliate links, run through partner networks including impact.com and Awin. If you buy through one, PaintDial may earn a small commission at no extra cost to you. That\u2019s the only way the site makes money \u2014 there are no ads, no sponsored placements, and no paid rankings. Matches are never influenced by whether a link earns commission.</p>

<h2>A note on colour names</h2>
<p>Colour names and paint ranges are the property of their respective brands. PaintDial shows each brand\u2019s published digital swatch values for comparison \u2014 always order a tester pot before committing to any colour.</p>

<p class="muted">Questions, corrections, or partnership enquiries: <a href="/contact/">get in touch</a>.</p>"""
    return _page_shell("About PaintDial",
        f"PaintDial is an independent tool comparing {N:,} paints across {BRANDS_WORD} UK brands. Who's behind it, how it's funded, and why no brand can influence the matches.",
        "/about/", body)


def build_alternatives_page(i):
    p = paints[i]; lab = LAB[i]; name = H.escape(p['name']); brand = H.escape(p['brand'])
    d = dmatch(i)
    best = {}
    for k in range(N):
        b = paints[k]['brand']
        if b == p['brand']:
            continue
        if b not in best or d[k] < d[best[b]]:
            best[b] = k
    # exhaustive ranked list: EVERY genuinely close match from other brands,
    # multiple per brand allowed (the colour page shows the one-per-brand view)
    others = sorted((k for k in range(N) if paints[k]['brand'] != p['brand']), key=lambda k: d[k])
    alts = [k for k in others if d[k] < 10][:20]
    if len(alts) < 8:
        alts = others[:8]
    closest = alts[0]
    cheapest = min(alts, key=lambda k: (TIER[paints[k]['brand']], d[k]))
    depth, fam = describe(i)

    # ---- PaintDial verdict: computed from the colour values, unique per page ----
    cb = diff_bits(i, closest)
    close_txt = (f'is the closest match from any other brand ({matchword(d[closest])})'
                 + (f' \u2014 though it\u2019s {joinbits(cb)}.' if cb
                    else f' \u2014 and it holds {name}\u2019s lightness, warmth and saturation alike.'))
    if cheapest == closest:
        value_txt = ' It\u2019s also the closest match from a value brand \u2014 unusual, as the nearest match and the closest value-brand one usually differ.'
    else:
        vb = diff_bits(i, cheapest)
        value_txt = (f' The closest value-brand match is <a class="pn" href="/colours/{slugs[cheapest]}">'
                     f'<i style="background:{paints[cheapest]["hex"]}"></i>{H.escape(paints[cheapest]["name"])}</a> '
                     f'by {H.escape(paints[cheapest]["brand"])} ({matchword(d[cheapest])})'
                     + (f', {joinbits(vb)}.' if vb else ', just as true to the original.')
                     + cooler_note(i, cheapest))

    # How distinctive is this colour? Counts vary a lot per colour, so this line
    # is real information rather than filler.
    n_near = sum(1 for b, k in best.items() if d[k] < 3)
    n_brands = len(best)
    if n_near == 0:
        dist_txt = (f' No other brand gets within a near-identical match of {name} \u2014 '
                    f'it\u2019s one of the more distinctive colours in the library, so expect a visible difference whichever you pick.')
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
        elif k == cheapest: note = 'Closest value-brand match.'
        note_html = f'<span class="a-note">{note}</span>' if note else ''
        return (f'<a class="alt" href="/colours/{s}">'
                f'<span class="a-rank">{rank}</span>'
                f'<span class="a-sw" style="background:{q["hex"]}"></span>'
                f'<span class="a-body"><span class="a-nm">{H.escape(q["name"])}</span>'
                f'<span class="a-br">{H.escape(q["brand"])} \u00b7 {TIER_WORD[TIER[q["brand"]]]} \u00b7 {matchword(d[k])}</span>'
                f'{note_html}</span>'
                f'<span class="a-hex">{q["hex"]}</span></a>')

    cards = ''.join(acard(n + 1, k) for n, k in enumerate(alts))
    nm = lambda k: H.escape(paints[k]['name']); brn = lambda k: H.escape(paints[k]['brand'])
    dulux = best.get('Dulux')
    dulux_q = (f'<div class="q"><h3>Is there a Dulux equivalent to <span class="pn"><i></i>{name}</span>?</h3>'
               f'<p>The nearest Dulux colour is <a class="pn" href="/colours/{slugs[dulux]}"><i style="background:{paints[dulux]['hex']}"></i>{nm(dulux)}</a> ({matchword(d[dulux])}). '
               f'It won\u2019t be pixel-perfect, so order a tester before committing.</p></div>') if dulux is not None else ''
    intro = (f'<a class="pn" href="/colours/{slugs[i]}"><i></i>{name}</a> is a {depth} {fam} from {brand}. As a premium paint, '
             f'it\u2019s a popular colour to seek out close matches and value-brand alternatives to.')

    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand} {name} alternatives \u2014 dupes &amp; closest matches | PaintDial</title>
<meta name="description" content="The closest alternative to {brand} {name} is {H.escape(paints[closest]['name'])} by {H.escape(paints[closest]['brand'])} ({matchword(d[closest])}). See all {len(alts)} matches from other UK brands, ranked, including value-brand options.">
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
{FONTS}<style>{ALT_CSS}</style></head><body style="--pc:{p['hex']}"><div class="top-band"></div><div class="wrap">
<header><a class="logo" href="/"><svg class="mark" viewBox="0 0 32 32" width="25" height="25" aria-hidden="true"><circle cx="16" cy="16" r="10" fill="none" stroke="var(--pc)" stroke-width="5"/><circle cx="16" cy="16" r="3.2" fill="var(--ink)"/></svg>PaintDial</a><nav><a class="head-nav" href="/about/">About</a><a class="head-nav" href="/how-it-works/">How it works</a><a class="lib-link" href="/colours/" aria-label="Colour library"><span class="lib-swatches" aria-hidden="true"><i style="background:#5E7E8B"></i><i style="background:#A6675A"></i><i style="background:#8A9D80"></i><i style="background:#D7B576"></i></span><span class="nav-lbl">Colour library</span></a><a class="nav-cta" href="/" aria-label="Open the colour tool"><span class="cta-wheel" aria-hidden="true"></span><span class="nav-lbl">Colour tool</span></a></nav></header><div class="mnav"><a href="/about/">About</a><a href="/how-it-works/">How matching works</a></div>
<h1>{brand} <span class="pn"><i></i>{name}</span> alternatives</h1>
<div class="hero-card"><div class="hero-sw" style="background:{p['hex']}"></div>
<div class="hero-info"><div class="hero-label">The colour you\u2019re matching</div>
<div class="hero-name">{brand} <span class="pn"><i></i>{name}</span></div>
<div class="hero-stats"><span><i>Hex</i>{p['hex']}</span><span><i>LRV</i>\u2248 {lrv(L[i]):.0f}</span><span><i>Shade</i>{depth.capitalize()} {fam}</span></div></div></div>
<p class="intro">{intro}</p>
{verdict}
<p class="intro">Below is every genuinely close match to <span class="pn"><i></i>{name}</span> from the other {OTHERS_WORD} brands \u2014 ranked purely by closeness, so where one brand has several near-misses, they all appear. For the single best match <em>per brand</em>, see the <a href="/colours/{slugs[i]}">{name} colour page</a>.</p>
<h2>All {len(alts)} close matches, ranked</h2>
<div class="alts">{cards}</div>
<div class="faq"><h2>Common questions</h2>
{dulux_q}
<div class="q"><h3>What\u2019s the closest value-brand alternative to <span class="pn"><i></i>{name}</span>?</h3>
<p>Of the close matches, <a class="pn" href="/colours/{slugs[cheapest]}"><i style="background:{paints[cheapest]['hex']}"></i>{nm(cheapest)}</a> by {brn(cheapest)} is the closest value-brand match ({TIER_WORD[TIER[paints[cheapest]['brand']]].lower()}, {matchword(d[cheapest])}).</p></div>
<div class="q"><h3>How close are these to <span class="pn"><i></i>{name}</span>?</h3>
<p>The list shows every genuinely close match from other brands, ranked nearest-first by perceptual colour difference \u2014 including several from one brand where they\u2019re all close. Screens differ from paint on a wall, so treat these as a shortlist and always order tester pots.</p></div></div>
<div class="cta"><b style="font-family:var(--serif);font-size:18px">Matching a different colour?</b>
<p style="font-size:14px;color:var(--muted);margin:6px 0 0">Search any paint name in the tool to see its closest matches across every UK brand.</p>
<a href="/colours/{slugs[i]}">See the full {name} colour page \u2192</a></div>
<footer>{FOOT}</footer>
</div><div class="top-band"></div></body></html>"""

# ---------- run ----------
if __name__ == '__main__':
    os.makedirs('site/colours', exist_ok=True)
    os.makedirs('site/alternatives', exist_ok=True)
    # wipe old colour pages so removed slugs don't linger
    for fn in os.listdir('site/colours'):
        if fn.endswith('.html'): os.remove('site/colours/'+fn)

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

    os.makedirs('site/how-it-works', exist_ok=True)
    open('site/how-it-works/index.html', 'w', encoding='utf-8').write(build_method_page())
    os.makedirs('site/about', exist_ok=True)
    open('site/about/index.html', 'w', encoding='utf-8').write(build_about_page())
    os.makedirs('site/paint-match-index', exist_ok=True)
    open('site/paint-match-index/index.html', 'w', encoding='utf-8').write(build_match_index_page())
    print('paint match index written')
    os.makedirs('site/paint-choice-index', exist_ok=True)
    open('site/paint-choice-index/index.html', 'w', encoding='utf-8').write(build_choice_index_page())
    print('paint choice index written')
    os.makedirs('site/research', exist_ok=True)
    open('site/research/index.html', 'w', encoding='utf-8').write(build_research_hub())
    print('research hub written')
    os.makedirs('site/match-from-a-photo', exist_ok=True)
    open('site/match-from-a-photo/index.html', 'w', encoding='utf-8').write(build_photo_page())
    print('photo landing page written')
    print('trust pages: 2')

    urls = [f'{DOMAIN}/', f'{DOMAIN}/colours/'] \
        + [f'{DOMAIN}/colours/{base_slug(b)}' for b in BRAND_ORDER] \
        + [f'{DOMAIN}/colours/{slugs[i]}' for i in range(N)] \
        + [f'{DOMAIN}/alternatives/{slugs[i]}' for i in alt_idx] \
        + [f'{DOMAIN}/dupes/{base_slug(b)}' for b in DUPE_TARGETS] \
        + [f'{DOMAIN}/how-it-works/', f'{DOMAIN}/about/', f'{DOMAIN}/paint-match-index/',
           f'{DOMAIN}/paint-choice-index/', f'{DOMAIN}/research/', f'{DOMAIN}/match-from-a-photo/']
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += ''.join(f'<url><loc>{u}</loc></url>\n' for u in urls)+'</urlset>'
    open('site/sitemap.xml', 'w').write(sm)


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
    <p class="sub">The page you were after doesn\u2019t exist \u2014 it may have moved when we reorganised.</p>
    <p class="sub" style="margin-top:14px"><a href="/" style="color:inherit;font-weight:600">Open the colour tool \u2192</a> &nbsp;\u00b7&nbsp; <a href="/colours/" style="color:inherit;font-weight:600">Browse the colour library \u2192</a></p>
    </div></div>
    {FOOT}
    </div></body></html>"""
    open('site/404.html', 'w').write(NOTFOUND)
    print('404 page written')
    print('sitemap:', len(urls), 'urls')
