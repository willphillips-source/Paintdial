#!/usr/bin/env python3
"""
check_dco_stock.py - rewrite dco-stock.json from Decorating Centre Online's live stock.

    python3 check_dco_stock.py            # check all links, rewrite dco-stock.json if lists changed
    python3 check_dco_stock.py --dry-run  # check and report, write nothing

For every colour in dco-links.json it reads the product's public Shopify data
(/products/<handle>.js) and looks at the variant the link points to. A colour is listed as
out of stock when that variant is unavailable AND no other sample (tester, sample pot, colour
patch, swatch) of the same product is available. gen_pages.py sends listed colours to the
brand's own page, so the button never lands on a dead end.

Run weekly by .github/workflows/dco-stock.yml. Safety rules, so a bad run can never strip
the affiliate links off the site:
  - a product that fails to load keeps whatever status it had in the existing file;
  - if more than 5% of products fail to load, nothing is written and the run fails;
  - if more than 40% come back out of stock, nothing is written and the run fails.
The file is only rewritten when the lists change, so a no-change week causes no deploy.
"""
import sys, json, re, time, datetime, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

LINKS, STOCK = 'dco-links.json', 'dco-stock.json'
SAMPLE_RE = re.compile(r'tester|sample|patch|swatch', re.I)
UA = 'PaintDialStockCheck/1.0 (+https://paintdial.co.uk/contact/)'
PAUSE = 0.6            # seconds between requests: about 8 minutes for 772 products
MAX_FAIL, MAX_OUT = 0.05, 0.40

def fetch(handle_url, tries=3):
    req = urllib.request.Request(handle_url + '.js', headers={'User-Agent': UA, 'Accept': 'application/json'})
    for n in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {'_gone': True}
            time.sleep(5 * (n + 1))
        except Exception:
            time.sleep(5 * (n + 1))
    return None

def status(product, variant_id, handle):
    """'in', 'out' or 'gone' for one link, given the product's Shopify data."""
    if product.get('_gone'):
        return 'gone'
    variants = product.get('variants') or []
    linked = next((v for v in variants if str(v.get('id')) == str(variant_id)), None)
    if linked and linked.get('available'):
        return 'in'
    whole_product_is_sample = bool(SAMPLE_RE.search(handle))
    for v in variants:
        if v.get('available') and (whole_product_is_sample or SAMPLE_RE.search(v.get('title') or '')):
            return 'in'
    return 'out'

def main(dry):
    links = {b: v for b, v in json.load(open(LINKS, encoding='utf-8')).items() if not b.startswith('_')}
    try:
        old_file = json.load(open(STOCK, encoding='utf-8'))
    except FileNotFoundError:
        old_file = {}
    old = {b: set(v) for b, v in old_file.items() if not b.startswith('_')}

    out, total, failed, gone = {}, 0, 0, []
    for brand in sorted(links):
        for key, url in sorted(links[brand].items()):
            total += 1
            u = urlparse(url)
            handle_url = f'{u.scheme}://{u.netloc}{u.path}'
            variant_id = (parse_qs(u.query).get('variant') or [''])[0]
            product = fetch(handle_url)
            time.sleep(PAUSE)
            if product is None:
                failed += 1
                if key in old.get(brand, ()):          # keep the previous status
                    out.setdefault(brand, []).append(key)
                continue
            s = status(product, variant_id, u.path.rsplit('/', 1)[-1])
            if s == 'gone':
                gone.append(f'{brand}: {key}')
            if s in ('out', 'gone'):
                out.setdefault(brand, []).append(key)

    n_out = sum(len(v) for v in out.values())
    print(f'checked {total} links: {n_out} out of stock, {failed} failed to load, {len(gone)} product pages gone')
    for g in gone:
        print('  page gone (rebuild dco-links.json from the feed):', g)
    if total and failed / total > MAX_FAIL:
        sys.exit(f'ABORT: {failed} of {total} products failed to load; dco-stock.json left as it was')
    if total and n_out / total > MAX_OUT:
        sys.exit(f'ABORT: {n_out} of {total} look out of stock, which is not believable; dco-stock.json left as it was')

    new = {b: set(v) for b, v in out.items()}
    back = sorted(f'{b}: {k}' for b in old for k in old[b] - new.get(b, set()))
    newly = sorted(f'{b}: {k}' for b in new for k in new[b] - old.get(b, set()))
    print(f'back in stock: {len(back)}; newly out of stock: {len(newly)}')
    for x in back:  print('  + back:', x)
    for x in newly: print('  - out: ', x)
    if not back and not newly:
        print('no change; file not rewritten')
        return
    if dry:
        print('dry run; file not rewritten')
        return
    result = {
        '_note': 'Colours whose tester at Decorating Centre Online was out of stock when checked, with no '
                 'other sample in stock there. gen_pages.py sends these to the brand\'s own page until the '
                 'next check. Checked by check_dco_stock.py, which reads each product\'s stock from '
                 'decoratingcentreonline.co.uk (/products/<handle>.js) for every link in dco-links.json.',
        '_checked': datetime.date.today().isoformat(),
    }
    result.update({b: sorted(out[b]) for b in sorted(out)})
    with open(STOCK, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('dco-stock.json rewritten')

if __name__ == '__main__':
    main('--dry-run' in sys.argv)
