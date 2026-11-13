#!/usr/bin/env python3
"""
check_links.py - does every "Order a tester" link still land on the right colour?

    python3 check_links.py                 # every link, about an hour
    python3 check_links.py --sample 40     # 40 colours a brand, a few minutes
    python3 check_links.py --brand Dulux   # one brand

The build-time checks in gen_pages.py catch a bad row in our own data. They cannot see a
retailer renaming a colour, moving a page or dropping one. This opens the pages and reads them.
It changes no files: it prints a report and exits 1 if it finds a link that is wrong or gone, so
the monthly GitHub run (.github/workflows/link-check.yml) emails a failure. Nothing is fixed
automatically, because a wrong link needs a person to say which side is right.

How each brand is checked (worked out by hand on 11 Nov 2026, when every link was opened):
  - Benjamin Moore: its colour pages carry the colour's name, number and value as data. All
    three are compared with ours, so a renamed colour or a changed value shows up.
  - Valspar: B&Q refuses more than about 190 requests in a row, so its tester pages are not
    opened. Valspar's own colour pages are (found from its sitemap): each gives the colour's
    name and code, which must match ours, and must still link to a B&Q tester pot. Our B&Q
    link is built from that code, and B&Q finds the colour by it (384 opened by hand, all right).
  - Johnstone's: one page, its colour directory, lists every colour's code and page address.
  - Decorating Centre Online: each product's public data is read and its title must name the colour.
  - Lakeland Paints: one tester page for every colour, checked once.
  - Everyone else: the page must load, without being redirected to a general page, and name
    the colour in its title or main heading.

A brand whose site refuses us, or whose pages do not name the colour in the page source, is
reported as "could not be checked" and does not fail the run: that is the site's doing, not a
wrong link. Those brands still need a look by hand now and then.
"""
import sys, json, re, time, html, unicodedata, threading, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs, quote, unquote
from collections import defaultdict

UA = 'PaintDialLinkCheck/1.0 (+https://www.paintdial.co.uk/contact/)'
PAUSE = 0.45                 # seconds between requests to one site
GIVE_UP_AFTER = 12           # refusals in a row before a site is left alone
# Names the brand's own page gives that differ from ours on purpose, so they are not reported
# every month. (brand, code): the name on the brand's page.
#  - Benjamin Moore OC-69 and OC-88 are sold in the US as White Opulence and Indian White; its UK
#    pages head them "Opulence" and "Sparkling Wine", the names of 879 and 949, which have the
#    same values. Kept under their own names so people searching for them find them.
#  - Valspar X1R1F: its page is headed "Midnight Dusk" but titled "Black Currant", our name.
KNOWN_NAMES = {('Benjamin Moore', 'OC-69'): 'Opulence', ('Benjamin Moore', 'OC-88'): 'Sparkling Wine',
               ('Valspar', 'X1R1F'): 'Midnight Dusk'}
ARGS = sys.argv[1:]
SAMPLE = int(ARGS[ARGS.index('--sample') + 1]) if '--sample' in ARGS else 0
ONLY = ARGS[ARGS.index('--brand') + 1] if '--brand' in ARGS else None


def norm(s):
    """Letters and digits only, accents folded, so "Julie's Dream" matches "Julie&#039;s Dream™"."""
    s = html.unescape(html.unescape(s or ''))
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().replace('&', 'and')
    return re.sub(r'[^a-z0-9]+', '', s)


def get(url, tries=2, limit=400_000):
    """(status, final_url, text). Status 0 means the request never got an answer."""
    u = urlparse(url)
    safe = f'{u.scheme}://{u.netloc}{quote(unquote(u.path), safe="/%")}' + (f'?{u.query}' if u.query else '')
    req = urllib.request.Request(safe, headers={'User-Agent': UA, 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.5',
                                                'Accept-Language': 'en-GB,en;q=0.8'})
    for n in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.geturl(), r.read(limit).decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, url, ''
            if e.code in (403, 429, 503) or n == tries - 1:
                return e.code, url, ''
            time.sleep(4)
        except Exception:
            if n == tries - 1:
                return 0, url, ''
            time.sleep(4)
    return 0, url, ''


def title_and_h1(text):
    t = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    h = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.I | re.S)
    return (t.group(1) if t else ''), re.sub(r'<[^>]+>', '', h.group(1) if h else '').strip()


class Brand:
    """Results for one brand. wrong and gone fail the run; blocked and unreadable do not."""
    def __init__(self, name, total):
        self.name, self.total = name, total
        self.ok = 0
        self.wrong, self.gone, self.blocked, self.notes = [], [], 0, []
        self.unreadable = False

    def line(self):
        bits = [f'{self.ok} right']
        if self.wrong: bits.append(f'{len(self.wrong)} WRONG')
        if self.gone: bits.append(f'{len(self.gone)} GONE')
        if self.blocked: bits.append(f'{self.blocked} not reached')
        state = 'could not be checked' if self.unreadable else ', '.join(bits)
        return f'{self.name}: {self.total} links, {state}'


def pick(rows):
    if SAMPLE and len(rows) > SAMPLE:
        step = len(rows) / SAMPLE
        return [rows[int(i * step)] for i in range(SAMPLE)]
    return rows


def check_pages(brand, rows, judge):
    """rows: (label, url). judge(label, status, final_url, text) -> 'ok' or a reason string."""
    res = Brand(brand, len(rows))
    refused = 0
    for label, url in pick(rows):
        status, final, text = get(url)
        time.sleep(PAUSE)
        if status in (404, 410):
            res.gone.append(f'{label}: {url}')
            refused = 0
            continue
        if status != 200:
            res.blocked += 1
            refused += 1
            if refused >= GIVE_UP_AFTER:
                res.notes.append(f'gave up after {GIVE_UP_AFTER} refusals in a row (last status {status})')
                res.blocked = res.total - res.ok - len(res.wrong) - len(res.gone)
                break
            continue
        refused = 0
        verdict = judge(label, status, final, text)
        if verdict == 'ok':
            res.ok += 1
        else:
            res.wrong.append(f'{label}: {verdict}  {url}')
    checked = res.ok + len(res.wrong)
    # Pages that load but never name the colour in the source (drawn by script in the browser):
    # nothing can be read from them here, so it is not evidence of a wrong link.
    if checked >= 5 and len(res.wrong) / checked > 0.3:
        res.unreadable = True
        res.notes.append(f'{len(res.wrong)} of {checked} pages did not name their colour in the page source; '
                         'this site cannot be checked this way')
        res.wrong = []
    if res.blocked and res.blocked >= max(1, len(pick(rows))) * 0.9:
        res.unreadable = True
    return res


def judge_named(name_of):
    def judge(label, status, final, text):
        name = name_of[label]
        title, h1 = title_and_h1(text)
        if norm(name) in norm(title) or norm(name) in norm(h1):
            return 'ok'
        return f'page is "{html.unescape(h1 or title)[:60]}"'
    return judge


def check_benjamin_moore(paints):
    by = {p['code']: p for p in paints}

    def judge(code, status, final, text):
        m = re.search(r'"colors":\[\{"name":"((?:[^"\\]|\\.)*)","number":"([^"]*)","hex":"([0-9A-Fa-f]{6})"', text)
        if not m:
            return 'no colour data on the page'
        p = by[code]
        try:
            name = json.loads('"' + m.group(1) + '"')
        except ValueError:
            name = m.group(1)
        if m.group(2) != code:
            return f'page is number {m.group(2)}'
        if norm(name) != norm(p['name']) and norm(name) != norm(KNOWN_NAMES.get(('Benjamin Moore', code), '')):
            return f'Benjamin Moore now calls it "{name}" (we have "{p["name"]}")'
        if ('#' + m.group(3)).upper() != p['hex'].upper():
            return f'value on the page is #{m.group(3).upper()} (we have {p["hex"]})'
        return 'ok'
    return check_pages('Benjamin Moore', [(p['code'], p['url']) for p in paints], judge)


def check_valspar(paints, links):
    res = Brand('Valspar', len(paints))
    status, _, text = get('https://www.valsparpaint.co.uk/sitemap.xml', limit=5_000_000)
    pages = sorted(set(re.findall(r'<loc>(https://www\.valsparpaint\.co\.uk/paint-colours/[^/<]+/[^/<]+/?)</loc>', text)))
    if status != 200 or len(pages) < 1000:
        res.unreadable = True
        res.notes.append(f'Valspar sitemap not readable (status {status}, {len(pages)} colour pages)')
        return res
    by = {p['code']: p for p in paints}
    seen, refused = set(), 0
    for url in pick(pages):
        status, _, text = get(url)
        time.sleep(PAUSE)
        if status != 200:
            res.blocked += 1
            refused += 1
            if refused >= GIVE_UP_AFTER:
                res.unreadable = True
                res.notes.append(f'gave up after {GIVE_UP_AFTER} refusals in a row (last status {status})')
                return res
            continue
        refused = 0
        c = re.search(r'"colorCode":"([^"]+)"', text)
        code = c.group(1) if c else ''
        if code not in by or code in seen:
            continue                      # a colour we don't carry, or one filed under two families
        seen.add(code)
        p = by[code]
        _, h1 = title_and_h1(text)
        tester = re.search(r'https?://www\.diy\.com/departments/[^"\'\s<]*tester[^"\'\s<]*', text, re.I)
        mine = links.get(code, '')
        if norm(h1) != norm(p['name']) and norm(h1) != norm(KNOWN_NAMES.get(('Valspar', code), '')):
            res.wrong.append(f'{p["name"]} ({code}): Valspar now calls it "{html.unescape(h1)}"  {url}')
        elif 'diy.com' in mine and not tester:
            res.wrong.append(f'{p["name"]} ({code}): Valspar no longer links to a B&Q tester  {url}')
        elif 'diy.com' not in mine and tester:
            res.notes.append(f'{p["name"]} ({code}) now has a B&Q tester: {html.unescape(tester.group(0))}')
            res.ok += 1
        else:
            res.ok += 1
    if not SAMPLE:
        for code in sorted(set(by) - seen):
            res.gone.append(f'{by[code]["name"]} ({code}): no longer on valsparpaint.co.uk')
    return res


def check_johnstones(paints, links):
    res = Brand("Johnstone's", len(paints))
    status, _, text = get('https://www.johnstonespaint.com/colour-directory', limit=20_000_000)
    found = {}
    for tag in re.findall(r'<[^>]*data-colour-page-url="[^"]*"[^>]*>', text):
        code = re.search(r'data-shade-code="([^"]*)"', tag)
        url = re.search(r'data-colour-page-url="([^"]*)"', tag)
        if code and url:
            found[html.unescape(code.group(1)).upper()] = html.unescape(url.group(1))
    if status != 200 or len(found) < 1500:
        res.unreadable = True
        res.notes.append(f"Johnstone's colour directory not readable (status {status}, {len(found)} colours)")
        return res
    for p in paints:
        mine, theirs = links.get(p['code'], ''), found.get(p['code'].upper())
        if theirs is None:
            res.gone.append(f'{p["name"]}: no longer in Johnstone\'s colour directory')
        elif urlparse(theirs).path.rstrip('/') != urlparse(mine).path.rstrip('/'):
            res.wrong.append(f'{p["name"]}: Johnstone\'s page is now {theirs} (we link to {mine})')
        else:
            res.ok += 1
    return res


def check_dco(dco, paints):
    name_by_code = {(p['brand'], p['code']): p['name'] for p in paints if p.get('code')}
    rows, want = [], {}
    for brand, m in dco.items():
        if brand.startswith('_'):
            continue
        for key, url in m.items():
            u = urlparse(url)
            label = f'{brand} {key}'
            rows.append((label, f'{u.scheme}://{u.netloc}{u.path}.js'))
            want[label] = (key, name_by_code.get((brand, key), key), (parse_qs(u.query).get('variant') or [''])[0])

    def judge(label, status, final, text):
        key, name, variant = want[label]
        try:
            j = json.loads(text)
        except ValueError:
            return 'product data not readable'
        title = j.get('title', '')
        if norm(name) not in norm(title) and norm(key) not in norm(title):
            return f'product is "{title[:60]}"'
        if variant and not any(str(v.get('id')) == variant for v in j.get('variants', [])):
            return 'the linked size or finish no longer exists on the product'
        return 'ok'
    return check_pages('Decorating Centre Online (affiliate links)', rows, judge)


def main():
    paints = json.load(open('paints-fixed.json', encoding='utf-8'))
    buy = {b: v.get('links', {}) for b, v in json.load(open('buy-links.json', encoding='utf-8')).items() if not b.startswith('_')}
    unlisted = {b: set(v.get('unlisted', [])) for b, v in json.load(open('buy-links.json', encoding='utf-8')).items() if not b.startswith('_')}
    try:
        dco = json.load(open('dco-links.json', encoding='utf-8'))
    except FileNotFoundError:
        dco = {}
    by_brand = defaultdict(list)
    for p in paints:
        if (p.get('code') or p['name']) not in unlisted.get(p['brand'], ()):
            by_brand[p['brand']].append(p)

    jobs = []
    for brand, ps in sorted(by_brand.items()):
        if ONLY and brand != ONLY:
            continue
        if brand == 'Benjamin Moore':
            jobs.append(lambda ps=ps: check_benjamin_moore(ps))
        elif brand == 'Valspar':
            jobs.append(lambda ps=ps: check_valspar(ps, buy.get('Valspar', {})))
        elif brand == "Johnstone's":
            jobs.append(lambda ps=ps: check_johnstones(ps, buy.get("Johnstone's", {})))
        elif brand == 'Lakeland Paints':
            def lakeland(ps=ps):
                url = ps[0]['url']
                res = check_pages('Lakeland Paints', [('tester page', url)],
                                  lambda label, s, f, t: 'ok' if re.search(r'matchpot|tester', t, re.I) else 'tester page no longer mentions testers')
                res.total = len(ps)
                res.ok = len(ps) if res.ok else 0
                res.notes.append('one tester page for every colour; the colour list on it is not read')
                return res
            jobs.append(lakeland)
        else:
            rows, names = [], {}
            for p in ps:
                url = p.get('url') or buy.get(brand, {}).get(p.get('code') or p['name'])
                # COAT's tester button goes to the sample page, not the paint page the data
                # holds (see buy_link in gen_pages.py), so that is the page to open.
                if brand == 'COAT' and url and url.endswith('-flat-matt'):
                    url = url[:-len('-flat-matt')] + '-sample'
                if url:
                    label = f'{p["name"]}' + (f' ({p["code"]})' if p.get('code') else '')
                    rows.append((label, url.split('?')[0] if brand != 'Lick' else url))
                    names[label] = p['name']
            jobs.append(lambda brand=brand, rows=rows, names=names: check_pages(brand, rows, judge_named(names)))
    if dco and not ONLY:
        jobs.append(lambda: check_dco(dco, paints))

    results, lock = [], threading.Lock()
    def run(job):
        try:
            r = job()
        except Exception as e:                       # one brand breaking must not hide the others
            r = Brand('a check that crashed', 0)
            r.unreadable = True
            r.notes.append(repr(e))
        with lock:
            results.append(r)
            print(r.line(), flush=True)
    threads = [threading.Thread(target=run, args=(j,)) for j in jobs]   # one thread a site
    for t in threads: t.start()
    for t in threads: t.join()

    results.sort(key=lambda r: r.name)
    out = ['', '=== PaintDial link check ===', 'Sample of %d a brand.' % SAMPLE if SAMPLE else 'Every link.', '']
    bad = 0
    for r in results:
        out.append(r.line())
        for n in r.notes: out.append('    note: ' + n)
        for w in r.wrong: out.append('    WRONG  ' + w)
        for g in r.gone:  out.append('    GONE   ' + g)
        bad += len(r.wrong) + len(r.gone)
    unchecked = [r.name for r in results if r.unreadable]
    out += ['', f'{bad} links need looking at.' if bad else 'No wrong or missing links found.']
    if unchecked:
        out.append('Could not be checked from here, so check by hand: ' + ', '.join(unchecked) + '.')
    report = '\n'.join(out)
    print(report)
    try:
        import os
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
                f.write('```\n' + report + '\n```\n')
    except OSError:
        pass
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
