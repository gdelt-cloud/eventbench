#!/usr/bin/env python3
"""GDELT Cloud event benchmark: one runner for every step.

Reproduce the published round, or compare any search service or event list you like:

    python bench.py refs                       # build the reference panels (downloads UCDP and USGS)
    python bench.py cloud                      # GDELT Cloud candidates for every reference occurrence
    python bench.py gdelt                      # GDELT Project 2.0 event rows near each conflict occurrence
    python bench.py check-adapter --adapter adapters/mock.py      # one test request through an adapter
    python bench.py web --adapter <file.py | module | "command"> --label my_search --usd-per-call 0.005 --max-usd 2
    python bench.py extract --label my_search --base-url <LLM endpoint> --model <name> \
        --usd-in <$/M input tokens> --usd-out <$/M output tokens> --max-usd 0.50   # optional: web search + LLM
    python bench.py eventlist --file my_events.csv --label my_list   # optional: any event list export
    python bench.py packets                    # blinded judge packets + the key that unblinds them
    python bench.py score                      # recall table and run/occurrences.csv from the judgments
    python bench.py monitor | pool | pool-judge | pool-score   # pooled truth: credit every real incident any service returns

Any search service plugs in through an adapter: a Python file exposing search(request) or any command
that reads one JSON request on stdin and writes JSON results on stdout. See adapters/README.md,
schemas/ and AGENTS.md. Keys come from the environment only: GDELT_CLOUD_API_KEY (required for
`cloud`), whatever key your adapter reads, and LLM_API_KEY for `extract`. Every paid call is reserved
in a local ledger before it is sent, and a run stops before it would pass --max-usd. Nothing here
writes to any service.

Standard library only (Python 3.10+).
"""
from __future__ import annotations

import argparse, csv, concurrent.futures, datetime as dt, email.utils, gzip, hashlib, importlib, importlib.util, io, json, math, os, random, re
import shlex, sqlite3, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = Path(os.environ.get('BENCH_RUN_DIR', ROOT / 'run'))
UA = 'gdelt-cloud-event-benchmark/1.0'
CLOUD = os.environ.get('GDELT_CLOUD_BASE', 'https://gdeltcloud.com/api/v2/')
SEED = 20261122

# ---------------------------------------------------------------- helpers

def norm(s: str | None) -> str:
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()

def day(s: str, k: int = 0) -> str:
    return (dt.date.fromisoformat(s[:10]) + dt.timedelta(days=k)).isoformat()

def hav(a, b, c, d):
    a, b, c, d = map(math.radians, (a, b, c, d))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2))

def http_json(url, body=None, headers=None, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'User-Agent': UA, 'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read()[:400].decode(errors='replace')}
    except Exception as e:  # network errors are recorded, never retried silently
        return 0, {'error': str(e)}

def wjson(p: Path, o):
    """Write atomically: a failed write never leaves a partial file that a rerun would then skip."""
    p.parent.mkdir(parents=True, exist_ok=True); tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8'); tmp.replace(p)

def clean(s) -> str:
    """Text as UTF-8 can hold it: a service's text can carry half of an emoji pair (a lone surrogate)."""
    return str(s).encode('utf-8', 'replace').decode('utf-8')

def rjson(p: Path):
    return json.loads(p.read_text())

# ---------------------------------------------------------------- spend ledger

class Ledger:
    """Reserve before sending; refuse anything that would pass the cap."""
    def __init__(self, name: str, cap_usd: float):
        RUN.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(RUN / f'spend_{name}.sqlite')
        self.db.execute('create table if not exists req(id text primary key, usd real, status text, t text)')
        self.cap = cap_usd
    def spent(self):
        return self.db.execute('select coalesce(sum(usd),0) from req').fetchone()[0]
    def reserve(self, rid, usd):
        if self.spent() + usd > self.cap: return False
        self.db.execute('insert or replace into req values(?,?,?,?)', (rid, usd, 'reserved', time.strftime('%FT%TZ', time.gmtime())))
        self.db.commit(); return True
    def settle(self, rid, usd, status):
        self.db.execute('update req set usd=?, status=? where id=?', (usd, status, rid)); self.db.commit()

# ---------------------------------------------------------------- references

UCDP_URL = 'https://ucdp.uu.se/downloads/candidateged/GEDEvent_v{v}.csv'
UCDP_PANEL = {  # country name in UCDP -> ISO3
    'Ukraine': 'UKR', 'Colombia': 'COL', 'Mexico': 'MEX', 'Ethiopia': 'ETH', 'Pakistan': 'PAK', 'Nigeria': 'NGA',
    'Sudan': 'SDN', 'DR Congo (Zaire)': 'COD', 'Myanmar (Burma)': 'MMR', 'Mali': 'MLI', 'Somalia': 'SOM', 'India': 'IND',
    'Yemen (North Yemen)': 'YEM', 'Syria': 'SYR', 'Israel': 'ISR', 'Burkina Faso': 'BFA', 'Brazil': 'BRA',
    'Ecuador': 'ECU', 'Afghanistan': 'AFG', 'Cameroon': 'CMR', 'Haiti': 'HTI', 'Iran': 'IRN'}
UCDP_PANEL_3 = {  # round 3: 6 per country, place known at least to admin1
    'South Africa': 'ZAF', 'Russia (Soviet Union)': 'RUS', 'Saudi Arabia': 'SAU', 'Venezuela': 'VEN', 'Bangladesh': 'BGD', 'Chad': 'TCD',
    'Mozambique': 'MOZ', 'Niger': 'NER', 'Indonesia': 'IDN', 'Lebanon': 'LBN', 'Burundi': 'BDI', 'Central African Republic': 'CAF',
    'Iraq': 'IRQ', 'Kenya': 'KEN', 'Philippines': 'PHL'}

def cmd_refs(a):
    """UCDP sample (seeded), USGS catalog, plus the curated lists shipped in references/."""
    refs = []
    raw = urllib.request.urlopen(urllib.request.Request(UCDP_URL.format(v=a.ucdp_version), headers={'User-Agent': UA}), timeout=120).read().decode('utf-8', 'replace')
    rows = [x for x in csv.DictReader(io.StringIO(raw)) if x['date_start'][:7] == a.month and x['date_end'] == x['date_start']]
    first12 = list(UCDP_PANEL)[:12]
    rngs = (random.Random(SEED), random.Random(SEED + 1))  # round 1 and round 2 drew with separate seeds
    rng3 = random.Random(SEED + 3)
    for c, iso in list(UCDP_PANEL.items()) + list(UCDP_PANEL_3.items()):
        r3 = c in UCDP_PANEL_3
        rng = rng3 if r3 else (rngs[0] if c in first12 else rngs[1])
        pool = sorted([x for x in rows if x['country'] == c and int(x['where_prec']) <= (5 if r3 else 4)], key=lambda x: x['id'])
        for x in rng.sample(pool, min(6 if r3 else a.per_country, len(pool))):
            refs.append({'uid': 'U' + x['id'], 'source': f'UCDP Candidate {a.ucdp_version}', 'family': 'conflict', 'iso': iso,
                         'country': c.split(' (')[0], 'date': x['date_start'][:10], 'lat': x['latitude'], 'lon': x['longitude'],
                         'place': f"{x['where_description']} ({x['adm_1']}; {x['adm_2']})",
                         'place_terms': ' '.join([x['where_description'], x['adm_1'], x['adm_2']]),
                         'what': f"{x['side_a']} vs {x['side_b']}; deaths (best) {x['best']}", 'deaths': int(x['best'])})
    for f in sorted((ROOT / 'references').glob('*.csv')):
        if f.name.startswith('usgs'): continue
        for x in csv.DictReader(f.open()):
            x['lat'] = x.get('lat') or None; x['lon'] = x.get('lon') or None
            x['deaths'] = int(x['deaths']) if x.get('deaths') else None
            refs.append(x)
    q = urllib.parse.urlencode({'format': 'csv', 'starttime': a.usgs_start, 'endtime': a.usgs_end, 'minmagnitude': 5.5})
    usgs = urllib.request.urlopen('https://earthquake.usgs.gov/fdsnws/event/1/query?' + q, timeout=60).read().decode()
    for i, x in enumerate(csv.DictReader(io.StringIO(usgs))):
        refs.append({'uid': f'USGS{i + 1:03d}', 'source': 'USGS M5.5+ catalog', 'family': 'non-conflict', 'category': 'ENVIRONMENT',
                     'iso': '', 'country': x['place'], 'date': x['time'][:10], 'lat': x['latitude'], 'lon': x['longitude'],
                     'place': x['place'], 'place_terms': x['place'], 'what': f"M{x['mag']} earthquake", 'deaths': None})
    wjson(RUN / 'refs.json', refs)
    print(len(refs), 'reference occurrences ->', RUN / 'refs.json')

# ---------------------------------------------------------------- GDELT Cloud

def cloud_get(path, params):
    key = os.environ.get('GDELT_CLOUD_API_KEY')
    if not key: sys.exit('GDELT_CLOUD_API_KEY is not set')
    url = CLOUD + path + '?' + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    cache = RUN / 'cloud_cache' / (hashlib.sha1(url.encode()).hexdigest()[:20] + '.json.gz')
    if cache.exists(): return json.loads(gzip.decompress(cache.read_bytes()))
    for attempt in range(3):
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key, 'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r: o = json.loads(r.read()); st = r.status
        except urllib.error.HTTPError as e: o = {'error': e.read()[:300].decode(errors='replace')}; st = e.code
        except Exception as e: o = {'error': str(e)}; st = 0
        with (RUN / 'cloud_requests.jsonl').open('a') as lg:
            lg.write(json.dumps({'url': url, 'status': st, 't': time.strftime('%FT%TZ', time.gmtime())}) + '\n')
        if st in (0, 429, 503) and attempt < 2: time.sleep(5 * (attempt + 1)); continue
        break
    o['_status'] = st
    if st == 200: cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(gzip.compress(json.dumps(o).encode()))
    return o

def cloud_pages(path, params, pages):
    rows, cur = [], None
    for _ in range(pages):
        o = cloud_get(path, dict(params, limit=100, cursor=cur))
        if o['_status'] != 200: break
        rows += o.get('data') or []
        cur = (o.get('pagination') or {}).get('next_cursor')
        if not cur: break
    return rows

TOPIC = {
    'conflict': r'kill|dead|death|fatal|attack|strike|clash|shoot|shot|gunm|bomb|explo|drone|ambush|massacre|murder|militant|terror|bandit|armed|insurg|rebel|asesin|masacre|muert|homicid|slain|execut|airstrike|shell',
    'POLITICAL': r'elect|vote|ballot|poll|runoff|presiden|parliament|knesset|senate|midterm|candidate',
    'ECONOMIC': r'rate|interest|monetary|central bank|basis point|inflation|riksbank|bank of',
    'HEALTH': r'ebola|virus|outbreak|fever|mers|chikungunya|shamonda|disease|infect|case',
    'ENVIRONMENT': r'earthquake|quake|cyclone|storm|landfall|tremor|magnitude|evacuat'}
STOP = set('district region province state oblast raion village town city area near county department municipality governorate zone north south east west central the and between road'.split())

def place_terms(x):
    return {w for w in re.findall(r"[a-z][a-z'\-]{3,}", norm(x['place_terms'])) if w not in STOP}

def rec_text(r):
    return norm(' '.join([r.get('title') or '', r.get('summary') or '', ' '.join((t.get('title') or '') for t in r.get('top_articles') or []), json.dumps(r.get('geo') or {})]))

def cmd_cloud(a):
    """Every route a customer has, across ALL categories: radius, country (any role), the category itself, and search=."""
    refs = rjson(RUN / 'refs.json'); out = {}
    def work(x):
        fam = 'conflict' if x['family'] == 'conflict' else x['category']
        topic, pt = re.compile(TOPIC[fam], re.I), place_terms(x)
        w = {'date_start': day(x['date'], -2), 'date_end': day(x['date'], 5)}
        cands = {}
        def take(rows, route, typ):
            for r in rows:
                t = rec_text(r); hits = [p for p in pt if p in t]
                if topic.search(t) and (hits or x['family'] != 'conflict'):
                    c = cands.setdefault(r['id'], {'id': r['id'], 'type': typ, 'date': r.get('event_date') or r.get('story_date'),
                        'category': r.get('category'), 'title': r.get('title'), 'summary': (r.get('summary') or '')[:260],
                        'geo': {k: (r.get('geo') or {}).get(k) for k in ('country', 'admin1', 'location')},
                        'articles': [(t2.get('title') or '')[:150] for t2 in (r.get('top_articles') or [])[:4]], 'routes': [], 'place_hits': hits})
                    if route not in c['routes']: c['routes'].append(route)
        for typ, path in (('event', 'events'), ('story', 'stories')):
            if x.get('lat'):
                take(cloud_pages(path, dict(w, near=f"{float(x['lat']):.4f},{float(x['lon']):.4f}", radius_km=150), 3), 'radius_150km', typ)
            if x.get('iso'):
                take(cloud_pages(path, dict(w, country=x['iso'], country_match='location_or_actor_origin'), 8), 'country_any_role', typ)
            if x['family'] != 'conflict' and x.get('iso'):
                p = dict(w, country=x['iso'])
                p['category' if typ == 'event' else 'story_category'] = x['category'] if typ == 'event' else 'cameoplus_' + x['category'].lower()
                take(cloud_pages(path, p, 3), 'category', typ)
            if a.allow_search:  # search= runs an embedding and a name step on the server
                q = ' '.join(sorted(pt, key=len, reverse=True)[:2]) + (' killed' if fam == 'conflict' else '')
                o = cloud_get(path, dict(w, country=x.get('iso') or None, search=q, limit=25))
                take(o.get('data') or [], 'search', typ)
        ranked = sorted(cands.values(), key=lambda c: (-len(c['place_hits']), -len(c['routes'])))[:a.cap]
        return x['uid'], {'candidates': ranked, 'before_cap': len(cands)}
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for uid, res in ex.map(work, refs): out[uid] = res
    wjson(RUN / 'cloud_candidates.json', out); print('cloud candidates for', len(out), 'occurrences')

# ---------------------------------------------------------------- GDELT Project 2.0

GCOLS = {'id': 0, 'sqldate': 1, 'a1': 6, 'a2': 16, 'code': 26, 'root': 28, 'geo': 52, 'lat': 56, 'lon': 57, 'url': 60}

def cmd_gdelt(a):
    """Stream the public 15-minute export + translation files; keep CAMEO 18-20 rows; match by distance or place."""
    refs = [x for x in rjson(RUN / 'refs.json') if x['family'] == 'conflict']
    lo = min(day(x['date'], -1) for x in refs); hi = max(day(x['date'], 7) for x in refs)
    t, end, stamps = dt.datetime.fromisoformat(lo), dt.datetime.fromisoformat(hi), []
    while t <= end: stamps.append(t); t += dt.timedelta(minutes=15)
    def one(t):
        rows = []
        for kind in ('export', 'translation.export'):
            u = f'http://data.gdeltproject.org/gdeltv2/{t:%Y%m%d%H%M%S}.{kind}.CSV.zip'
            try:
                z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60).read()))
                for line in z.read(z.namelist()[0]).decode('utf-8', 'replace').split('\n'):
                    f = line.split('\t')
                    if len(f) > 60 and f[28] in ('18', '19', '20'): rows.append({k: f[i] for k, i in GCOLS.items()})
            except Exception: pass
        return rows
    allrows = []
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for rs in ex.map(one, stamps): allrows += rs
    out = {}
    for x in refs:
        d0, pt = dt.date.fromisoformat(x['date']), place_terms(x); near = []
        for r in allrows:
            try: rd = dt.date(int(r['sqldate'][:4]), int(r['sqldate'][4:6]), int(r['sqldate'][6:8]))
            except ValueError: continue
            if not -1 <= (rd - d0).days <= 3: continue
            if x.get('lat'):
                try: dist = hav(float(x['lat']), float(x['lon']), float(r['lat']), float(r['lon']))
                except ValueError: continue
                if dist <= 100: near.append((dist, r))
            elif any(p in norm(r['geo']) for p in pt): near.append((0, r))
        near.sort(key=lambda z: z[0])
        out[x['uid']] = {'rows_near': len(near), 'rows': [r for _, r in near][:a.cap]}
    wjson(RUN / 'gdelt_candidates.json', out); print('GDELT rows scanned', len(allrows))

# ---------------------------------------------------------------- web search arms (pluggable)
#
# Any search service plugs in through an ADAPTER, which is one of:
#   * a Python file (or importable module) exposing  search(request: dict) -> list[dict] | dict
#     and, optionally, USD_PER_CALL = <float>;
#   * any command that reads ONE JSON request on stdin and writes JSON on stdout.
# Request: schemas/search_request.schema.json. Response: a list of results, or
# {"results": [...], "usd": <actual cost>, "status": <int>, "error": <str>}; schemas/search_results.schema.json.
# Worked examples: adapters/template.py, adapters/template_curl.sh, adapters/mock.py.

LABEL_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
TOPIC_KEYWORDS = {
    'crimes, arrests, trials and court rulings': 'arrest court trial',
    'political developments and elections': 'election politics',
    'disasters and accidents': 'disaster accident',
    'business and economic developments': 'business economy',
    'diplomatic and international developments': 'diplomatic talks',
    'health and environmental developments': 'health outbreak',
    'science and technology developments': 'science technology',
}
KW_STOP = {'and', 'or', 'of', 'the', 'in', 'a', 'an', 'to', 'for', 'on', 'developments'}

class AdapterError(Exception):
    pass

def keyword_query(country: str, family: str, subject: str | None = None) -> str:
    """The short keyword form of a question, for services whose own guidance prefers keywords."""
    if family == 'conflict':
        return f'{country} attack killed'
    kw = TOPIC_KEYWORDS.get(subject or '') or ' '.join(w for w in re.findall(r'[a-z]+', (subject or '').lower()) if w not in KW_STOP)[:60]
    return f'{country} {kw}'.strip()

def keywords_of(keyword_query: str, country: str) -> list[str]:
    """The keyword form without the country, as a list: for news databases that take the country as a filter."""
    rest = keyword_query[len(country):] if keyword_query.lower().startswith(country.lower()) else keyword_query
    return [w for w in rest.split() if w]

def week_label(mon: dt.date, sun: dt.date) -> str:
    return f'{mon:%B} {mon.day}-{sun.day} {mon.year}' if mon.month == sun.month else f'{mon:%B} {mon.day}-{sun:%B} {sun.day} {sun.year}'

def web_questions(refs):
    """Conflict: one blind question per country-week. Non-conflict: one blind topic question per occurrence.
    No question ever names the incident."""
    jobs = []
    for iso, c, wk in sorted({(x['iso'], x['country'], dt.date.fromisocalendar(*dt.date.fromisoformat(x['date']).isocalendar()[:2], 1).isoformat())
                              for x in refs if x['family'] == 'conflict'}):
        mon = dt.date.fromisoformat(wk); sun = mon + dt.timedelta(days=6)
        jobs.append({'id': f'{iso}-{wk}', 'mode': 'monitor', 'country': c, 'start_date': mon.isoformat(), 'end_date': sun.isoformat(),
                     'query': f'people killed in attacks, clashes or violence in {c} {week_label(mon, sun)}',
                     'keyword_query': keyword_query(c, 'conflict'),
                     'intent': f'Find news reports of distinct lethal violent incidents that occurred in {c} between {mon} and {sun}. Prefer reports that name the place and date.'})
    for x in refs:
        if x['family'] == 'conflict' or x['uid'].startswith('USGS'): continue
        d0 = dt.date.fromisoformat(x['date']); subject = x.get('topic') or 'news developments'
        jobs.append({'id': x['uid'], 'mode': 'topic', 'country': x['country'], 'start_date': day(x['date'], -2), 'end_date': day(x['date'], 5),
                     'query': f"{subject} in or affecting {x['country']} around {d0:%B} {d0.day} {d0.year}",
                     'keyword_query': keyword_query(x['country'], 'non-conflict', subject),
                     'intent': f"What {subject} were reported in or affecting {x['country']} around {d0}? Give distinct developments with dated sources."})
    for j in jobs: j['keywords'] = keywords_of(j['keyword_query'], j['country'])
    return jobs

def read_questions(path: Path):
    """A fixed question set (CSV or JSON list) in the request shape, e.g. suite/questions_2026_11.csv: the exact
    questions the published round asked. `covers` lists the occurrence uids each question answers (; separated)."""
    rows = rjson(path) if path.suffix.lower() == '.json' else list(csv.DictReader(path.open(newline='', encoding='utf-8')))
    out = []
    for r in rows:
        q = {k: v for k, v in r.items() if v not in (None, '')}
        for k in ('covers', 'keywords', 'keyword_queries'):
            if isinstance(q.get(k), str): q[k] = [s for s in re.split(r'[;|]', q[k]) if s]
        q.setdefault('keywords', keywords_of(q['keyword_query'], q['country']))
        out.append(q)
    return out

def pick_ids(spec: str | None):
    if not spec: return None
    p = Path(spec)
    if p.is_file(): return set(rjson(p)) if p.suffix == '.json' else {l.strip() for l in p.read_text().splitlines() if l.strip()}
    return set(spec.split(','))

def load_adapter(spec: str):
    """Return (search_fn, declared_usd_per_call). spec is a .py path, an importable module, or a shell command."""
    p = Path(spec)
    if spec.endswith('.py') and p.is_file():
        s = importlib.util.spec_from_file_location(f'bench_adapter_{p.stem}', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        return m.search, getattr(m, 'USD_PER_CALL', None)
    if re.fullmatch(r'[A-Za-z_][\w.]*', spec):
        try:
            m = importlib.import_module(spec)
            if hasattr(m, 'search'): return m.search, getattr(m, 'USD_PER_CALL', None)
        except ImportError:
            pass
    argv = shlex.split(spec)
    def run(req):
        pr = subprocess.run(argv, input=json.dumps(req), capture_output=True, text=True, timeout=180)
        if pr.returncode != 0: raise AdapterError(f'exit {pr.returncode}: {pr.stderr.strip()[-300:]}')
        try: return json.loads(pr.stdout)
        except ValueError: raise AdapterError('stdout was not JSON: ' + pr.stdout[:200])
    return run, None

def as_date(v) -> str | None:
    """ISO date from an ISO timestamp or an RFC 2822 date; None if neither."""
    if not v: return None
    s = str(v).strip(); m = re.match(r'\d{4}-\d{2}-\d{2}', s)
    if m: return m.group(0)
    try: return email.utils.parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError, IndexError): return None

def normalize_results(o):
    """An adapter returns a list of results, or a dict with "results" and optional "usd", "status", "error"."""
    meta = {}
    if isinstance(o, dict):
        meta = {k: o[k] for k in ('usd', 'status', 'error', 'units', 'total') if k in o}; o = o.get('results') or []
    if not isinstance(o, list): raise AdapterError('expected a list of results or {"results": [...]}')
    out = []
    for r in o:
        if isinstance(r, dict) and r.get('url'):
            x = {'url': clean(r['url']), 'title': clean(r.get('title') or '')[:300], 'published': as_date(r.get('published')),
                 'excerpt': clean(r.get('excerpt') or '')[:1000]}
            # Optional, for news databases: the date the service gives the occurrence itself, when it first had the
            # item (an ingest or first-seen timestamp, kept as given), and the place it assigns.
            if r.get('occurred'): x['occurred'] = as_date(r['occurred'])
            if r.get('first_seen'): x['first_seen'] = str(r['first_seen'])[:40]
            if r.get('place'): x['place'] = clean(r['place'])[:200]
            out.append(x)
    return out, meta

def call_adapter(search, req):
    t0 = time.time()
    try:
        res, meta = normalize_results(search(req)); st = int(meta.get('status') or 200); err = meta.get('error')
    except Exception as e:  # an adapter failure is recorded, never retried silently
        res, meta, st, err = [], {}, 0, f'{type(e).__name__}: {e}'[:400]
    return res, meta, st, err, round(time.time() - t0, 2)

def need_label(label):
    if not LABEL_RE.match(label or ''): sys.exit('--label must start with a letter and use lowercase letters, digits or _ (e.g. my_search)')

def cmd_web(a):
    need_label(a.label)
    search, declared = load_adapter(a.adapter)
    usd = a.usd_per_call if a.usd_per_call is not None else declared
    if usd is None: sys.exit('--usd-per-call is required: the adapter does not declare USD_PER_CALL')
    jobs = read_questions(Path(a.questions)) if a.questions else web_questions(rjson(RUN / 'refs.json'))
    ids = pick_ids(a.ids)
    if ids is not None: jobs = [j for j in jobs if j['id'] in ids]
    if a.start_after: jobs = [j for j in jobs if j['start_date'] >= a.start_after]
    if a.only: jobs = [j for j in jobs if j['id'].startswith(a.only)]
    if a.limit: jobs = jobs[:a.limit]
    led = Ledger('web_' + a.label, a.max_usd); ok = bad = 0
    for j in jobs:
        f = RUN / 'web' / f"{j['id']}-{a.label}.json"
        if f.exists(): continue
        rid = f"{j['id']}-{a.label}"
        if not led.reserve(rid, usd): print(f'spend cap ${a.max_usd:.2f} reached'); break
        covers = j.get('covers')
        req = dict({k: v for k, v in j.items() if k != 'covers'}, max_results=a.max_results)
        res, meta, st, err, secs = call_adapter(search, req)
        cost = meta['usd'] if isinstance(meta.get('usd'), (int, float)) else (usd if st == 200 else 0)
        led.settle(rid, cost, str(st)); ok += st == 200; bad += st != 200
        wjson(f, {'id': j['id'], 'label': a.label, 'status': st, 'error': err, 'request': req, 'results': res, 'usd': cost,
                  'units': meta.get('units'), 'total': meta.get('total'), 'covers': covers,
                  'secs': secs, 't': time.strftime('%FT%TZ', time.gmtime())})
        print(f"{j['id']:28s} {st} {len(res):3d} results {secs:5.1f}s", flush=True)
        if a.sleep: time.sleep(a.sleep)
    print(f'{a.label}: {ok} ok, {bad} failed; spend so far ${led.spent():.3f} of ${a.max_usd:.2f}')

def cmd_check_adapter(a):
    """Send one sample monitoring question through an adapter and validate what comes back."""
    search, declared = load_adapter(a.adapter)
    usd = a.usd_per_call if a.usd_per_call is not None else (declared or 0.0)
    led = Ledger('check', a.max_usd)
    if not led.reserve(f'check-{time.time():.0f}', usd): sys.exit('spend cap reached')
    mon, sun = dt.date(2026, 10, 19), dt.date(2026, 10, 25)
    req = {'id': 'check', 'mode': 'monitor', 'country': 'Ukraine', 'start_date': mon.isoformat(), 'end_date': sun.isoformat(),
           'query': f'people killed in attacks, clashes or violence in Ukraine {week_label(mon, sun)}', 'keyword_query': keyword_query('Ukraine', 'conflict'),
           'intent': f'Find news reports of distinct lethal violent incidents that occurred in Ukraine between {mon} and {sun}.', 'max_results': a.max_results}
    req['keywords'] = keywords_of(req['keyword_query'], req['country'])
    res, meta, st, err, secs = call_adapter(search, req)
    problems = []
    if st != 200: problems.append(f'status {st}: {err}')
    if st == 200 and not res: problems.append('no results with a url')
    if len(res) > a.max_results: problems.append(f'{len(res)} results, more than max_results={a.max_results}')
    undated = sum(1 for r in res if not r['published']); outside = sum(1 for r in res if r['published'] and not (day(req['start_date'], -1) <= r['published'] <= day(req['end_date'], 8)))
    if undated: problems.append(f'{undated} results have no parseable published date (ISO or RFC 2822)')
    if outside: problems.append(f'{outside} results were published outside the window (is the date filter applied?)')
    if not any(r['excerpt'] for r in res): problems.append('no excerpts; reviewers judge from title and excerpt')
    optional = {k: sum(1 for r in res if r.get(k)) for k in ('occurred', 'first_seen', 'place')}  # news-database fields, informational
    print(json.dumps({'status': st, 'secs': secs, 'results': len(res), 'usd': meta.get('usd', usd), 'units': meta.get('units'),
                      'optional_fields': optional, 'first': res[:2], 'problems': problems}, indent=1, ensure_ascii=False))
    sys.exit(1 if st != 200 or not res else 0)

# ---------------------------------------------------------------- web search + LLM

EXTRACT_INSTR = {
    'monitor': ('You turn web search results into a list of DISTINCT real-world incidents of the requested kind. One record per incident: '
                'when several results describe the same incident, return one record listing all their URLs. Only incidents the result text '
                'itself supports, that occurred in the requested country and date range, and that killed at least one person.'),
    'topic': ('You turn web search results into a list of DISTINCT real-world developments of the requested kind. One record per development: '
              'when several results describe the same one, return one record listing all their URLs. Only developments the result text '
              'itself supports, in or affecting the requested country, inside the requested dates.'),
    'list': ('You turn web search results into a list of DISTINCT real-world occurrences of the requested kind. One record per occurrence: '
             'merge results that describe the same one. Only occurrences the result text itself supports, in the requested country and dates.'),
}
EXTRACT_SHAPE = (' Do not invent dates, places or numbers; use null when the text does not give them. Return JSON only: '
                 '{"records":[{"date":"YYYY-MM-DD"|null,"place":string|null,"actors":string|null,"what":string,"deaths":number|null,"source_urls":[string]}]}')

def parse_json_object(text: str):
    try: return json.loads(text)
    except ValueError:
        m = re.search(r'\{.*\}', text or '', re.S)
        if m:
            try: return json.loads(m.group(0))
            except ValueError: pass
    return None

def llm_call(a, key, instr, user):
    """Any LLM endpoint that speaks the chat-completions protocol (default) or the responses protocol."""
    base = a.base_url.rstrip('/'); h = {'Authorization': 'Bearer ' + key}
    if a.api == 'responses':
        st, o = http_json(base + '/responses', {'model': a.model, 'instructions': instr, 'input': user, 'max_output_tokens': a.max_tokens,
                                               'text': {'format': {'type': 'json_object'}}}, h, timeout=180)
        u = o.get('usage') or {}; tin, tout = u.get('input_tokens', 0), u.get('output_tokens', 0)
        text = ''.join(c.get('text', '') for item in o.get('output') or [] for c in item.get('content') or [])
    else:
        st, o = http_json(base + '/chat/completions', {'model': a.model, 'messages': [{'role': 'system', 'content': instr}, {'role': 'user', 'content': user}],
                                                      a.token_param: a.max_tokens, 'response_format': {'type': 'json_object'}}, h, timeout=180)
        u = o.get('usage') or {}; tin, tout = u.get('prompt_tokens', 0), u.get('completion_tokens', 0)
        text = ((o.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    return st, o, tin or 0, tout or 0, text

def cmd_extract(a):
    """Web search + LLM: the pipeline a developer builds to imitate an event feed. One LLM call per results page
    turns the page into de-duplicated records. It cannot find anything the search did not return."""
    key = os.environ.get('LLM_API_KEY')
    if not key: sys.exit('LLM_API_KEY is not set')
    a.base_url = a.base_url or os.environ.get('LLM_BASE_URL')
    if not a.base_url: sys.exit('--base-url (or LLM_BASE_URL) is required')
    led = Ledger('extract', a.max_usd); n = 0
    files = sorted((RUN / 'web').glob('*.json'))
    if a.label: files = [f for f in files if f.stem.rsplit('-', 1)[-1] == a.label]
    for f in files:
        out = RUN / 'extract' / f.name
        if out.exists(): continue
        r = rjson(f); req = r.get('request') or {}
        if r.get('status') != 200 or not r.get('results'): continue
        instr = EXTRACT_INSTR.get(req.get('mode'), EXTRACT_INSTR['topic']) + EXTRACT_SHAPE
        user = (f"Requested: {req.get('intent')}\nCountry: {req.get('country')}\nDates: {req.get('start_date')} to {req.get('end_date')}\n\nResults:\n"
                + '\n\n'.join(f"[{i + 1}] {x['title']}\nURL: {x['url']}\nPublished: {x.get('published') or 'unknown'}\n{x.get('excerpt') or ''}" for i, x in enumerate(r['results'])))
        est = (len(instr) + len(user)) / 3.5 / 1e6 * a.usd_in + a.max_tokens / 1e6 * a.usd_out
        if not led.reserve(f.name, est): print('spend cap reached'); break
        t0 = time.time(); st, o, tin, tout, text = llm_call(a, key, instr, user)
        led.settle(f.name, (tin * a.usd_in + tout * a.usd_out) / 1e6, str(st))
        parsed = parse_json_object(text) if st == 200 else None
        recs = parsed.get('records') if isinstance(parsed, dict) else None
        wjson(out, {'id': r['id'], 'label': r.get('label') or r.get('provider'), 'status': st, 'records': recs if isinstance(recs, list) else [],
                    'error': None if isinstance(recs, list) else (str(o.get('error'))[:300] if st != 200 else 'unparseable: ' + (text or '')[:200]),
                    'tokens': [tin, tout], 'secs': round(time.time() - t0, 2)})
        n += 1
    print(f'extracted {n} result pages; extract spend ${led.spent():.3f} of ${a.max_usd:.2f}')

# ---------------------------------------------------------------- pooled truth (release 2026.11.1)
#
# Recall against a reference list counts only the incidents on that list. A pooled truth also credits every
# other real incident a service returns: every record every service returned to the same monitoring question,
# plus the reference incidents, is pooled in one shuffled, blind packet; jurors mark each record on topic or not
# and give records about the same incident one label; the pool is every incident found. Rules: JUDGE_POOL.md.
#
#   python bench.py monitor   --questions suite/pool_questions_2026_11.csv        # GDELT Cloud's answer to each question
#   python bench.py web       --questions suite/pool_questions_2026_11.csv --adapter ... --label ... --max-results 20 --max-usd 2
#   python bench.py pool      --questions suite/pool_questions_2026_11.csv --labels web_a,web_b,web_c
#   python bench.py pool-judge --juror my_llm --model <name> --base-url <endpoint> --usd-in .. --usd-out .. --max-usd 2
#   python bench.py pool-score

VIOLENT = 'Battles,Explosions/Remote violence,Violence against civilians,Riots'
POOL_TEXT = 600

def cmd_monitor(a):
    """GDELT Cloud's answer to each monitoring question, through the API's own filters for "people killed in
    attacks, clashes or violence in {country}, {week}": conflict Events located in the country with deaths, crime
    Events (CR01, homicide or violent crime) located in the country, and the conflict and crime Stories about the
    country (a Story's own country; Stories are dated by reporting, so they get the question's publication tail)."""
    for q in read_questions(Path(a.questions)):
        f = RUN / 'monitor' / f"{q['id']}.json"
        if f.exists(): continue
        iso, start, end = q.get('iso3') or q['country'], q['start_date'], q['end_date']
        tail = day(end, int(q.get('publication_tail_days') or 0))
        calls = {
            'event_conflict': ('events', dict(country=iso, country_match='location', date_start=start, date_end=end, category=VIOLENT, has_fatalities='true')),
            'event_crime': ('events', dict(country=iso, country_match='location', date_start=start, date_end=end, category='CRIME', subcategory='CR01')),
            'story': ('stories', dict(country=iso, date_start=start, date_end=tail, story_category='conflict_security,cameoplus_crime')),
        }
        out, n_calls = {'id': q['id'], 'country': q['country'], 'calls': {}, 'records': []}, 0
        for route, (path, params) in calls.items():
            rows, cur, pages = [], None, 0
            for _ in range(a.max_pages):
                o = cloud_get(path, dict(params, limit=100, cursor=cur)); pages += 1
                if o['_status'] != 200:
                    out['calls'][route] = {'status': o['_status'], 'error': str(o.get('error') or o)[:300]}; break
                rows += o.get('data') or []
                cur = (o.get('pagination') or {}).get('next_cursor')
                if not cur: break
            out['calls'].setdefault(route, {'status': 200, 'pages': pages, 'rows': len(rows), 'params': params}); n_calls += pages
            for r in rows:
                g = r.get('geo') or {}
                heads = [t.get('title') for t in (r.get('top_articles') or [])[:3] if t.get('title')]
                out['records'].append({'id': r.get('id'), 'route': route, 'type': 'event' if path == 'events' else 'story',
                                       'date': r.get('event_date') or r.get('story_date'), 'title': r.get('title'),
                                       'summary': r.get('summary') or r.get('event_description'), 'category': r.get('category'),
                                       'subcategory': r.get('subcategory'), 'has_fatalities': r.get('has_fatalities'),
                                       'country': g.get('country'), 'place': ', '.join(x for x in (g.get('location'), g.get('admin1'), g.get('country')) if x),
                                       'headlines': heads})
        # A Story matches a country it is about, or one of its Events' actors is from: keep the Stories about it.
        names = {norm(q['country'])} | {norm(x) for x in (q.get('country_aliases') or '').split(';') if x}
        if any(norm(r['country']) in names for r in out['records'] if r['type'] == 'story'):
            out['records'] = [r for r in out['records'] if r['type'] == 'event' or norm(r['country']) in names]
        out['n_calls'] = n_calls
        wjson(f, out)
        print(f"{q['id']:16s} {len(out['records']):5d} records in {n_calls} calls", {k: v.get('rows', v.get('status')) for k, v in out['calls'].items()}, flush=True)

def pool_clip(s, n=POOL_TEXT):
    s = re.sub(r'\s+', ' ', s or '').strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'

def cmd_pool(a):
    """One blind, shuffled packet per question: every record GDELT Cloud (`monitor`) and each web label (`web`)
    returned, plus the reference incidents the question covers. Writes run/pool/packets and run/pool/key.json."""
    occ = {r['uid']: r for r in csv.DictReader(open(ROOT / 'suite' / 'occurrences_v2.csv', encoding='utf-8'))}
    ref_text = {}
    if a.reference_text:
        ref_text = {r['uid']: r['text'] for r in csv.DictReader(open(a.reference_text, encoding='utf-8'))}
    labels = [x for x in a.labels.split(',') if x]
    key, meta = {}, {}
    (RUN / 'pool' / 'packets').mkdir(parents=True, exist_ok=True)
    for q in read_questions(Path(a.questions)):
        recs = []
        m = RUN / 'monitor' / f"{q['id']}.json"
        if m.exists():
            for r in rjson(m)['records']:
                src = 'cloud_event' if r['type'] == 'event' else 'cloud_story'
                text = f"[{r['date']}] {pool_clip(r['title'], 200)}. " + (f"{pool_clip(r['summary'], 360)} " if r.get('summary') else '') \
                       + f"Place: {r['place']}. Headlines: {pool_clip('; '.join(r['headlines']), 420)}"
                recs.append((src, r['id'], {'route': r['route'], 'strict': r['type'] == 'event' or bool(r.get('has_fatalities'))}, text))
        for lab in labels:
            w = RUN / 'web' / f"{q['id']}-{lab}.json"
            if not w.exists(): continue
            for rank, r in enumerate(rjson(w).get('results') or [], 1):
                recs.append((lab, r['url'], {'rank': rank}, f"[{r.get('published') or ''}] {pool_clip(r.get('title'), 200)}. {pool_clip(r.get('excerpt'))}"))
        for u in q.get('covers') or []:
            o = occ.get(u)
            if o: recs.append(('reference', u, {}, f"[{o['date']}] {pool_clip(ref_text.get(u) or o['what'], 500)} Place: {pool_clip(o['place'], 160)}."))
        random.Random(f"{SEED}-{q['id']}").shuffle(recs)
        items = []
        for i, (src, rid, extra, text) in enumerate(recs, 1):
            key[f"{q['id']}:R{i:04d}"] = {'q': q['id'], 'src': src, 'id': rid, **extra}
            items.append({'id': f'R{i:04d}', 'text': text})
        meta[q['id']] = {'country': q['country'], 'scope': q.get('scope') or q['country'], 'start': q['start_date'], 'end': q['end_date'],
                         'tail_days': int(q.get('publication_tail_days') or 0), 'records': len(items),
                         'by_source': dict(collections.Counter(s for s, *_ in recs))}
        mq = meta[q['id']]
        head = (f"### QUESTION {q['id']}\nAsked of every source: people killed in attacks, clashes or violence in {q['country']}, {q['start_date']} to {q['end_date']}.\n"
                + (f"Scope for this question: {q['scope']}.\n" if q.get('scope') else '') + f"Records ({len(items)}), shuffled, sources hidden:\n")
        (RUN / 'pool' / 'packets' / f"{q['id']}.md").write_text(head + '\n'.join(f"{it['id']}: {it['text']}" for it in items) + '\n', encoding='utf-8')
        wjson(RUN / 'pool' / 'packets' / f"{q['id']}.json", {'question': q['id'], **mq, 'items': items})
        print(f"{q['id']:16s} {len(items):5d} records", mq['by_source'])
    wjson(RUN / 'pool' / 'key.json', key); wjson(RUN / 'pool' / 'questions.json', meta)

POOL_GROUP = ('These records were judged on topic for one monitoring question. Group them by incident: the same act, at the same place, '
              'at the same time is one incident; different acts are different incidents, however similar. A record that only restates a '
              'reference description is the same incident as the records that report it. Every id must appear in exactly one group. '
              'Give each group one label in the form "place · date · what happened". Reply with JSON: {"incidents": [{"label": "...", "ids": ["R0001", ...]}]}.')

def cmd_pool_judge(a):
    """An LLM juror over the pooled packets: each packet in chunks (on topic or not, with a provisional incident
    label), then one grouping call per question that gives every record of one incident the same label."""
    need_label(a.juror)
    if a.require_model and a.model != a.require_model: sys.exit(f'STOP: --model {a.model} is not --require-model {a.require_model}')
    key = os.environ.get('LLM_API_KEY')
    if not key: sys.exit('LLM_API_KEY is not set')
    a.base_url = a.base_url or os.environ.get('LLM_BASE_URL')
    if not a.base_url: sys.exit('--base-url (or LLM_BASE_URL) is required')
    rules = (ROOT / 'JUDGE_POOL.md').read_text(encoding='utf-8')
    led = Ledger('pool_' + a.juror, a.max_usd)
    outdir = RUN / 'pool' / 'verdicts' / a.juror; outdir.mkdir(parents=True, exist_ok=True)

    def ask(rid, instr, user):
        est = (len(instr) + len(user)) / 3.5 / 1e6 * a.usd_in + a.max_tokens / 1e6 * a.usd_out
        if not led.reserve(rid, est): sys.exit('spend cap reached')
        for attempt in (1, 2):
            st, o, tin, tout, text = llm_call(a, key, instr, user)
            led.settle(rid, (tin * a.usd_in + tout * a.usd_out) / 1e6, str(st))
            got = parse_json_object(text) if st == 200 else None
            if isinstance(got, dict): return got
            print(f'  {rid} attempt {attempt}: status {st}, unparseable or failed', flush=True)
        raise SystemExit(f'two attempts failed for {rid}')

    for f in sorted((RUN / 'pool' / 'packets').glob('*.json')):
        if a.ids and f.stem not in set(a.ids.split(',')): continue
        out = outdir / f.name
        if out.exists(): continue
        p = rjson(f)
        ask_line = f"People killed in attacks, clashes or violence in {p['country']}, from {p['start']} to {p['end']}." + (f" Scope: {p['scope']}." if p.get('scope') != p['country'] else '')
        sys_rules = rules.replace('{COUNTRY}', p['scope']).replace('{START}', p['start']).replace('{END}', p['end']).replace('{TAIL}', str(p.get('tail_days') or 0))
        verdicts = {}
        for i in range(0, len(p['items']), a.chunk):
            chunk = p['items'][i:i + a.chunk]
            got = ask(f"{p['question']}-s1-{i}", sys_rules + '\n\nReply with JSON: {"verdicts": [{"id": "R0001", "on_topic": "yes|no", "incident": "label or null"}, ...]}, one entry per record in this batch.',
                      f"QUESTION: {ask_line}\n\n" + '\n'.join(f"{it['id']}: {it['text']}" for it in chunk))
            for v in got.get('verdicts') or []:
                if isinstance(v, dict) and v.get('id'): verdicts[v['id']] = {'on_topic': 'yes' if v.get('on_topic') == 'yes' else 'no', 'incident': v.get('incident') if v.get('on_topic') == 'yes' else None}
        on = [it for it in p['items'] if verdicts.get(it['id'], {}).get('on_topic') == 'yes']
        if on:
            got = ask(f"{p['question']}-s2", POOL_GROUP, f"QUESTION: {ask_line}\n\n" + '\n'.join(f"{it['id']} [first label: {verdicts[it['id']]['incident']}]: {it['text'][:320]}" for it in on))
            for g in got.get('incidents') or []:
                for rid in g.get('ids') or []:
                    if verdicts.get(rid, {}).get('on_topic') == 'yes': verdicts[rid]['incident'] = g.get('label')
        for it in p['items']: verdicts.setdefault(it['id'], {'on_topic': 'no', 'incident': None, 'missing': True})
        wjson(out, verdicts)
        print(f"{p['question']:16s} {len(p['items'])} records, {len(on)} on topic, {len({verdicts[it['id']]['incident'] for it in on})} incidents", flush=True)
    print(f'{a.juror}: spend ${led.spent():.3f} of ${a.max_usd:.2f}')

POOL_SERVICES = [
    ('cloud', 'GDELT Cloud, every record', lambda k: k['src'] in ('cloud_event', 'cloud_story')),
    ('cloud_strict', 'GDELT Cloud, Events and Stories with deaths', lambda k: k['src'] == 'cloud_event' or (k['src'] == 'cloud_story' and k.get('strict'))),
    ('cloud_events', 'GDELT Cloud, Events only', lambda k: k['src'] == 'cloud_event'),
]

def cmd_pool_score(a):
    """Per juror: the pool, each service's distinct incidents, its share of the pool, its records on topic; per
    question; and juror agreement. Writes results/pooled_recall.csv and results/pooled_by_question.csv."""
    key = rjson(RUN / 'pool' / 'key.json'); meta = rjson(RUN / 'pool' / 'questions.json')
    web = sorted({k['src'] for k in key.values() if k['src'] not in ('cloud_event', 'cloud_story', 'reference')})
    services = POOL_SERVICES + [(w, w, (lambda w: lambda k: k['src'] == w)(w)) for w in web] + [('any_web', 'any web search', lambda k: k['src'] in web)]
    jurors = sorted(d.name for d in (RUN / 'pool' / 'verdicts').iterdir() if d.is_dir())
    rows, byq, V = [], [], {}
    lab = lambda x: re.sub(r'\s+', ' ', (x.get('incident') or '').lower()).strip() if x.get('on_topic') == 'yes' and x.get('incident') else None
    for j in jurors:
        V[j] = {f.stem: rjson(f) for f in (RUN / 'pool' / 'verdicts' / j).glob('*.json')}
        qs = [q for q in meta if q in V[j]]
        agg = collections.defaultdict(collections.Counter); pool_n = 0
        for q in qs:
            v = V[j][q]; recs = {k.split(':', 1)[1]: x for k, x in key.items() if x['q'] == q}
            labels = {rid: lab(x) for rid, x in v.items() if lab(x)}
            pool = set(labels.values()); pool_n += len(pool)
            refs = {labels[r] for r, k in recs.items() if k['src'] == 'reference' and r in labels}
            row = {'juror': j, 'question': q, 'pool': len(pool), 'reference_incidents': len(refs)}
            for sid, _, test in services:
                ids = [r for r, k in recs.items() if test(k)]
                got = {labels[r] for r in ids if r in labels}
                agg[sid].update(records=len(ids), on_topic=sum(r in labels for r in ids), delivered=len(got), refs=len(got & refs))
                row[sid] = len(got)
            byq.append(row)
        for sid, name, _ in services:
            x = agg[sid]
            rows.append({'juror': j, 'service': sid, 'description': name, 'questions': len(qs), 'pool': pool_n, 'delivered': x['delivered'],
                         'share_of_pool': round(x['delivered'] / pool_n, 3) if pool_n else '', 'per_question': round(x['delivered'] / len(qs), 2) if qs else '',
                         'reference_incidents_delivered': x['refs'], 'records': x['records'], 'records_on_topic': x['on_topic'],
                         'on_topic_share': round(x['on_topic'] / x['records'], 3) if x['records'] else ''})
    for name, data in (('pooled_recall.csv', rows), ('pooled_by_question.csv', byq)):
        if not data: continue
        with open(ROOT / 'results' / name, 'w', newline='', encoding='utf-8') as fo:
            w = csv.DictWriter(fo, fieldnames=list(data[0]), lineterminator='\r\n'); w.writeheader(); w.writerows(data)
    for r in rows:
        print(f"{r['juror']:8s} {r['service']:14s} {r['delivered']:5d} of {r['pool']:5d}  {r['share_of_pool']!s:6s} {r['per_question']!s:6s}/q  on topic {r['on_topic_share']!s:6s} of {r['records']}")
    if len(jurors) >= 2:
        a1, b1 = [], []
        for q in set(V[jurors[0]]) & set(V[jurors[1]]):
            for rid in set(V[jurors[0]][q]) & set(V[jurors[1]][q]):
                a1.append(V[jurors[0]][q][rid].get('on_topic') == 'yes'); b1.append(V[jurors[1]][q][rid].get('on_topic') == 'yes')
        n = len(a1); po = sum(x == y for x, y in zip(a1, b1)) / n; pa, pb = sum(a1) / n, sum(b1) / n; pe = pa * pb + (1 - pa) * (1 - pb)
        print(f"agreement {jurors[0]} vs {jurors[1]}: {po:.1%} of {n} records, kappa {(po - pe) / (1 - pe):.2f}")


# ---------------------------------------------------------------- any event list (dataset export)

EVENT_LIST_COLUMNS = ['id', 'date', 'country', 'admin1', 'locality', 'lat', 'lon', 'category', 'actors', 'deaths', 'source_url', 'description']

def read_event_list(path: Path):
    if path.suffix.lower() in ('.jsonl', '.ndjson'):
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return list(csv.DictReader(path.open(newline='', encoding='utf-8')))

def cmd_eventlist(a):
    """Match rows of any event list to the reference cases by date and place, the way the GDELT Project arm is
    matched, so they enter the blind packets beside every other service. Columns: templates/event_list.csv."""
    need_label(a.label)
    rows = read_event_list(Path(a.file)); refs = rjson(RUN / 'refs.json'); out = {}
    missing = [c for c in ('id', 'date', 'country') if rows and c not in rows[0]]
    if missing: sys.exit(f'{a.file} lacks required columns {missing}; see templates/event_list.csv')
    for x in refs:
        d0 = dt.date.fromisoformat(x['date']); pt = place_terms(x) if x.get('place_terms') else set()
        lo, hi = (-a.days_before, a.days_after) if x['family'] == 'conflict' else (-2, 5)
        words = {w for w in re.findall(r'[a-z]{5,}', norm(x.get('what')))}
        hits = []
        for r in rows:
            try: rd = dt.date.fromisoformat(str(r.get('date'))[:10])
            except ValueError: continue
            if not lo <= (rd - d0).days <= hi: continue
            if x.get('lat') and r.get('lat') not in (None, ''):
                try: dist = hav(float(x['lat']), float(x['lon']), float(r['lat']), float(r['lon']))
                except (TypeError, ValueError): continue
                if dist <= a.km: hits.append((dist, r))
                continue
            rc = norm(r.get('country'))
            if not rc or rc not in (norm(x['country']), norm(x.get('iso'))): continue
            text = norm(' '.join(str(r.get(k) or '') for k in ('admin1', 'locality', 'description', 'actors')))
            if x['family'] == 'conflict':
                if any(p in text for p in pt): hits.append((0, r))
            else:
                ov = len(words & set(re.findall(r'[a-z]{5,}', text)))
                same_cat = r.get('category') and x.get('category') and norm(r['category']) == norm(x['category'])
                if ov >= 2 or (same_cat and ov >= 1): hits.append((-ov, r))
        hits.sort(key=lambda z: z[0])
        if hits: out[x['uid']] = [r for _, r in hits[:a.cap]]
    wjson(RUN / 'eventlists' / f'{a.label}.json', out)
    print(f'{a.label}: {len(rows)} rows read; {len(out)} of {len(refs)} cases have at least one nearby row')

# ---------------------------------------------------------------- blinded judge packets

def cmd_packets(a):
    refs = rjson(RUN / 'refs.json')
    cc = rjson(RUN / 'cloud_candidates.json') if (RUN / 'cloud_candidates.json').exists() else {}
    gc = rjson(RUN / 'gdelt_candidates.json') if (RUN / 'gdelt_candidates.json').exists() else {}
    web = {p.stem: rjson(p) for p in (RUN / 'web').glob('*.json')} if (RUN / 'web').exists() else {}
    ext = {p.stem: rjson(p) for p in (RUN / 'extract').glob('*.json')} if (RUN / 'extract').exists() else {}
    lists = {p.stem: rjson(p) for p in (RUN / 'eventlists').glob('*.json')} if (RUN / 'eventlists').exists() else {}
    rng, key, n, packets = random.Random(7), {}, 0, {}
    def rid(src, ref_id, text, **extra):
        nonlocal n
        n += 1; k = f'R{n:05d}'; key[k] = {'source': src, 'ref': ref_id, **extra}; return f'{k}: {text}'
    def web_lines(stem, o):
        label = o.get('label') or o.get('provider')
        # One line per record; a non-web identifier (a cluster id, say) is kept in the key, never shown to reviewers.
        return [rid('web_' + label, r['url'], ' '.join((f"[{(r.get('occurred') or r.get('published') or '')[:10]}] {r.get('title')}. {(r.get('excerpt') or '')[:a.excerpt]}"
                    + (f" Place: {r['place']}." if r.get('place') else '') + (f" URL: {r['url']}" if r['url'].startswith('http') else '')).split()),
                    question=stem.rsplit('-', 1)[0], rank=i + 1)
                for i, r in enumerate(o.get('results') or [])]
    def ext_lines(stem, o):
        label = o.get('label') or o.get('provider')
        return [rid('extract_' + label, f'{stem}#{i}', f"[{r.get('date')}] {r.get('what') or r.get('description')} Place: {r.get('place') or r.get('locality')}. Actors: {r.get('actors')}. Deaths: {r.get('deaths')}.")
                for i, r in enumerate(o.get('records') or o.get('incidents') or [])]
    qof, shared_occ = {}, {}  # occurrence uid -> the fixed question that covers it (bench.py web --questions)
    for stem, o in web.items():
        for u in o.get('covers') or []: qof.setdefault(u, stem.rsplit('-', 1)[0])
    for x in refs:
        lines = []
        for c in cc.get(x['uid'], {}).get('candidates', []):
            lines.append(rid('cloud_' + c['type'], c['id'], f"[{c['date']}] {c['title']}. {c['summary']} Place: {c['geo']}. Articles: {' | '.join(c['articles'])}"))
        for r in gc.get(x['uid'], {}).get('rows', []):
            lines.append(rid('gdelt_row', r['url'], f"[{r['sqldate']}] {r['a1'] or '?'} -> CAMEO {r['code']} -> {r['a2'] or '?'} at {r['geo']}. URL: {r['url']}"))
        for label, m in lists.items():
            for r in m.get(x['uid'], []):
                lines.append(rid('list_' + label, str(r.get('id')), f"[{r.get('date')}] {r.get('description') or ''} Place: {r.get('locality') or ''} {r.get('admin1') or ''} {r.get('country') or ''}. Actors: {r.get('actors') or '?'}. Deaths: {r.get('deaths') or '?'}. Category: {r.get('category') or '?'}."))
        wk = dt.date.fromisocalendar(*dt.date.fromisoformat(x['date']).isocalendar()[:2], 1).isoformat()
        qid = f"{x['iso']}-{wk}" if x['family'] == 'conflict' else x['uid']
        if x['uid'] in qof:  # asked through a fixed question set: its records are shared in the question's block
            rng.shuffle(lines); shared_occ.setdefault(qof[x['uid']], []).append((x, lines)); continue
        for stem, o in web.items():
            if stem.rsplit('-', 1)[0] == qid and not o.get('covers'): lines += web_lines(stem, o)
        for stem, o in ext.items():
            if stem.rsplit('-', 1)[0] == qid and not (web.get(stem) or {}).get('covers'): lines += ext_lines(stem, o)
        rng.shuffle(lines)
        packets.setdefault(x.get('iso') or 'XX', []).append(
            f"\n## OCCURRENCE {x['uid']}\nSource: {x['source']} | Date: {x['date']} | Place: {x['place']} | What: {x['what']}\nCandidates ({len(lines)}):\n" + '\n'.join(lines))
    # One block per question: its shared records once, then each occurrence it covers (as the published packets did).
    blocks, size, chunk = [], 0, 0
    for q in sorted(shared_occ):
        sl = [l for stem, o in web.items() if stem.rsplit('-', 1)[0] == q and o.get('covers') for l in web_lines(stem, o)]
        sl += [l for stem, o in ext.items() if stem.rsplit('-', 1)[0] == q and (web.get(stem) or {}).get('covers') for l in ext_lines(stem, o)]
        rng.shuffle(sl)
        b = [f"\n## QUESTION {q}: shared candidate records (apply to every occurrence under this question)"] + (sl or ['(no records)'])
        for x, own in shared_occ[q]:
            b.append(f"\n### OCCURRENCE {x['uid']}\nSource: {x['source']} | Date: {x['date']} | Place: {x['place']} | What: {x['what']}\n"
                     f"Occurrence-specific candidates ({len(own)}), also consider the QUESTION records above:" + ('\n' + '\n'.join(own) if own else ''))
        b = '\n'.join(b)
        if blocks and size + len(b) > 200_000:
            packets[f'Q{chunk:02d}'] = blocks; chunk += 1; blocks, size = [], 0
        blocks.append(b); size += len(b)
    if blocks: packets[f'Q{chunk:02d}'] = blocks
    for iso, blocks in packets.items():
        (RUN / 'packets').mkdir(parents=True, exist_ok=True)
        (RUN / 'packets' / f'{iso}.md').write_text((ROOT / 'JUDGING.md').read_text() + '\n' + '\n'.join(blocks))
    wjson(RUN / 'packet_key.json', key)
    print(len(packets), 'packets,', len(key), 'blinded records. Judges write run/judgments/<ISO>.json; never show them packet_key.json.')

# ---------------------------------------------------------------- scoring

def wilson(k, n, z=1.96):
    if not n: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d

def score_groups(key):
    """Fixed groups for GDELT Cloud and the GDELT Project, plus one group per adapter label found in the key."""
    srcs = {v['source'] for v in key.values()}
    g = {'cloud_filters': ('GDELT Cloud (Event or Story)', ('cloud_event', 'cloud_story')), 'cloud_event': ('GDELT Cloud Events only', ('cloud_event',)),
         'gdelt_project': ('GDELT Project rows', ('gdelt_row',))}
    for s in sorted(srcs):
        kind, _, label = s.partition('_')
        if kind == 'web': g[label] = (label, (s,))
        elif kind == 'extract': g[label + '_llm'] = (label + ' + LLM', (s,))
        elif kind == 'list': g[label] = (label + ' (event list)', (s,))
    return g

def cmd_score(a):
    refs = rjson(RUN / 'refs.json'); key = rjson(RUN / 'packet_key.json'); J = {}
    for f in (RUN / 'judgments').glob('*.json'):
        if not f.name.startswith('cells_'): J.update(rjson(f))
    groups = score_groups(key); rows = []; occ = []
    for x in refs:
        if x['uid'] not in J: continue
        S = J[x['uid']].get('S', [])
        occ.append({'uid': x['uid'], 'panel': x['source'], 'family': x['family'], 'country': x['country'], 'date': x['date'], 'what': x['what'][:200],
                    **{col: int(any(key.get(r, {}).get('source') in srcs for r in S)) for col, (_, srcs) in groups.items()},
                    'note': J[x['uid']].get('note', '')})
    for panel in sorted({o['panel'] for o in occ}):
        sub = [o for o in occ if o['panel'] == panel]
        for col, (name, _) in groups.items():
            k = sum(o[col] for o in sub); lo, hi = wilson(k, len(sub))
            rows.append({'panel': panel, 'column': col, 'source': name, 'found': k, 'of': len(sub), 'recall': round(k / len(sub), 3),
                         'ci95': [lo and round(lo, 3), hi and round(hi, 3)]})
    wjson(RUN / 'scores.json', rows)
    if occ:
        with (RUN / 'occurrences.csv').open('w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(occ[0])); w.writeheader(); w.writerows(occ)
    for r in rows: print(f"{r['panel'][:38]:38s} {r['source']:30s} {r['found']:4d}/{r['of']:<4d} {r['recall']:.0%}")
    print(f'{len(occ)} judged occurrences -> run/occurrences.csv (one 0/1 column per source; python report.py --results run/occurrences.csv)')

# ---------------------------------------------------------------- taxonomy listing test

CELL_LABEL = {'Protests': 'protests, demonstrations and strikes', 'CRIME': 'crimes, arrests, prosecutions and court cases',
              'ECONOMIC': 'economic policy, prices, trade and market developments', 'CORPORATE': 'company and corporate developments',
              'INFRASTRUCTURE': 'infrastructure, transport and utility disruptions or accidents', 'HEALTH': 'health developments and disease outbreaks',
              'ENVIRONMENT': 'environmental events, natural disasters and pollution'}

def cmd_cells(a):
    """For each category x country cell: Cloud's complete list, one web search, then a blinded packet.
    Reviewers verify web results, look each one up in Cloud's list, and check a random sample of Cloud's records.
    `bench.py cells --score` then gives each side's share of the other's verified items and a Lincoln-Petersen total."""
    out = RUN / 'cells'; out.mkdir(parents=True, exist_ok=True)
    if a.score:
        key = rjson(out / 'key.json'); J = {}
        for f in (RUN / 'judgments').glob('cells_*.json'): J.update(rjson(f))
        t = {'web_occ': 0, 'm': 0, 'samp': 0, 'fit': 0, 'inweb': 0, 'cloud_fit_est': 0.0}
        for cell, k in key.items():
            o = J.get(cell)
            if not o: continue
            groups = {}
            for wid, v in o.get('web', {}).items():
                if str(v.get('in_cell')).lower() == 'yes': groups.setdefault(v.get('group') or wid, []).append(v)
            fit = sum(1 for v in o.get('sample', {}).values() if str(v.get('fits')).lower() == 'yes')
            t['web_occ'] += len(groups); t['m'] += sum(1 for g in groups.values() if any(x.get('cloud_match') for x in g))
            t['samp'] += len(o.get('sample', {})); t['fit'] += fit
            t['inweb'] += sum(1 for v in o.get('sample', {}).values() if str(v.get('fits')).lower() == 'yes' and v.get('in_web'))
            t['cloud_fit_est'] += k['n_cloud'] * (fit / len(o['sample']) if o.get('sample') else 0)
        N = t['cloud_fit_est'] * t['web_occ'] / t['m'] if t['m'] else float('nan')
        print(json.dumps(dict(t, lincoln_petersen_total=round(N), cloud_share_of_web=round(t['m'] / max(1, t['web_occ']), 3),
                              web_share_of_cloud=round(t['inweb'] / max(1, t['fit']), 3)), indent=1))
        return
    led = Ledger('cells', a.max_usd); key = {}; packets = {}
    search, declared = load_adapter(a.adapter) if a.adapter else (None, None)
    usd = a.usd_per_call if a.usd_per_call is not None else (declared or 0.0)
    rng = random.Random(5)
    for country in a.countries.split(','):
        for cat in a.categories.split(','):
            cell = f'{cat}-{country}'
            rows = cloud_pages('events', {'date_start': a.start, 'date_end': a.end, 'country': country, 'category': cat, 'country_match': 'location'}, 30)
            web = []
            if search and led.reserve(cell, usd):
                req = {'id': cell, 'mode': 'list', 'country': country, 'start_date': a.start, 'end_date': a.end, 'max_results': 10,
                       'query': f'{CELL_LABEL[cat]} in {country} between {a.start} and {a.end}',
                       'keyword_query': keyword_query(country, 'non-conflict', CELL_LABEL[cat]),
                       'intent': f'List every distinct {CELL_LABEL[cat]} that happened in {country} between {a.start} and {a.end}, each with its date and place.'}
                web, meta, st, err, secs = call_adapter(search, req)
                led.settle(cell, meta['usd'] if isinstance(meta.get('usd'), (int, float)) else (usd if st == 200 else 0), str(st))
            samp = rng.sample(rows, min(10, len(rows)))
            key[cell] = {'n_cloud': len(rows), 'sample': [r['id'] for r in samp]}
            packets.setdefault(country, []).append('\n'.join(
                [f'\n## CELL {cell}: {CELL_LABEL[cat]} in {country}, {a.start} to {a.end}', '### Web results (one search, top 10)']
                + [f"W{i + 1}: [{(r.get('published') or '')[:10]}] {r.get('title')}. {(r.get('excerpt') or '')[:240]}" for i, r in enumerate(web[:10])]
                + [f'### Full list from the structured service ({len(rows)} records)'] + [f"{r['id']}: [{r.get('event_date')}] ({r.get('subcategory_label')}) {r.get('title')}" for r in rows]
                + ['### Sampled structured records to check'] + [f"S{j + 1} = {r['id']}" for j, r in enumerate(samp)]))
    for country, blocks in packets.items():
        (out / f'{country}.md').write_text((ROOT / 'JUDGING_CELLS.md').read_text() + '\n'.join(blocks))
    wjson(out / 'key.json', key)
    print(len(key), 'cells; packets in', out, '; judgments go to run/judgments/cells_<country>.json')

# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('refs'); p.add_argument('--ucdp-version', default='26_0_10'); p.add_argument('--month', default='2026-10')
    p.add_argument('--per-country', type=int, default=10); p.add_argument('--usgs-start', default='2026-10-01'); p.add_argument('--usgs-end', default='2026-11-21')
    p = sp.add_parser('cloud'); p.add_argument('--workers', type=int, default=3); p.add_argument('--cap', type=int, default=35); p.add_argument('--allow-search', action='store_true')
    p = sp.add_parser('gdelt'); p.add_argument('--cap', type=int, default=25)
    p = sp.add_parser('check-adapter', help='send one sample question through an adapter and validate the response')
    p.add_argument('--adapter', required=True); p.add_argument('--usd-per-call', type=float); p.add_argument('--max-results', type=int, default=10)
    p.add_argument('--max-usd', type=float, default=0.05)
    p = sp.add_parser('web', help='run every question through one search adapter')
    p.add_argument('--adapter', required=True, help='a .py file or module exposing search(request), or a command reading JSON on stdin')
    p.add_argument('--label', required=True, help='column name for this service in the results, e.g. my_search')
    p.add_argument('--usd-per-call', type=float, help='price reserved per call (defaults to the adapter\'s USD_PER_CALL)')
    p.add_argument('--max-usd', type=float, required=True); p.add_argument('--max-results', type=int, default=10)
    p.add_argument('--limit', type=int, help='only the first N questions (a capped trial)'); p.add_argument('--only', help='only question ids with this prefix')
    p.add_argument('--questions', help='a fixed question set (CSV or JSON), e.g. suite/questions_2026_11.csv: the questions the published round asked')
    p.add_argument('--ids', help='only these question ids: comma-separated, or a file (one per line, or a JSON list)')
    p.add_argument('--start-after', help='only questions whose window starts on or after this date (for plans limited to recent data)')
    p.add_argument('--sleep', type=float, default=0.2)
    p = sp.add_parser('extract', help='web search + LLM: turn each results page into de-duplicated records')
    p.add_argument('--label', help='only this adapter label (default: every label)'); p.add_argument('--base-url', help='LLM endpoint base URL (or LLM_BASE_URL)')
    p.add_argument('--api', choices=('chat', 'responses'), default='chat'); p.add_argument('--model', required=True)
    p.add_argument('--usd-in', type=float, required=True, help='USD per million input tokens'); p.add_argument('--usd-out', type=float, required=True)
    p.add_argument('--max-usd', type=float, required=True); p.add_argument('--max-tokens', type=int, default=4000)
    p.add_argument('--token-param', default='max_tokens', help='chat protocol only: max_tokens or max_completion_tokens')
    p = sp.add_parser('eventlist', help='match rows of any event list (CSV or JSONL) to the cases')
    p.add_argument('--file', required=True); p.add_argument('--label', required=True); p.add_argument('--km', type=float, default=100)
    p.add_argument('--days-before', type=int, default=1); p.add_argument('--days-after', type=int, default=3); p.add_argument('--cap', type=int, default=25)
    p = sp.add_parser('packets'); p.add_argument('--excerpt', type=int, default=260, help='characters of each web result shown to reviewers')
    p = sp.add_parser('monitor', help="GDELT Cloud's answer to each monitoring question (pooled truth)")
    p.add_argument('--questions', default=str(ROOT / 'suite' / 'pool_questions_2026_11.csv')); p.add_argument('--max-pages', type=int, default=30)
    p = sp.add_parser('pool', help='one blind packet per question: every service\'s records plus the reference incidents')
    p.add_argument('--questions', default=str(ROOT / 'suite' / 'pool_questions_2026_11.csv')); p.add_argument('--labels', default='web_a,web_b,web_c')
    p.add_argument('--reference-text', help='optional CSV (uid,text) with fuller reference descriptions')
    p = sp.add_parser('pool-judge', help='an LLM juror over the pooled packets')
    p.add_argument('--juror', required=True, help='name for this juror\'s verdicts, e.g. my_llm'); p.add_argument('--model', required=True)
    p.add_argument('--require-model', help='refuse to send any request unless --model equals this'); p.add_argument('--base-url')
    p.add_argument('--api', choices=('chat', 'responses'), default='chat'); p.add_argument('--token-param', default='max_tokens')
    p.add_argument('--usd-in', type=float, required=True); p.add_argument('--usd-out', type=float, required=True); p.add_argument('--max-usd', type=float, required=True)
    p.add_argument('--max-tokens', type=int, default=6000); p.add_argument('--chunk', type=int, default=40); p.add_argument('--ids', help='only these question ids')
    sp.add_parser('pool-score', help='score every juror\'s verdicts against the pooled truth')
    sp.add_parser('score')
    p = sp.add_parser('cells'); p.add_argument('--countries', default='Nigeria,Brazil,India,France,Indonesia')
    p.add_argument('--categories', default=','.join(CELL_LABEL)); p.add_argument('--start', default='2026-11-09'); p.add_argument('--end', default='2026-11-15')
    p.add_argument('--adapter', help='search adapter for the one web search per cell'); p.add_argument('--usd-per-call', type=float)
    p.add_argument('--max-usd', type=float, default=0.25); p.add_argument('--score', action='store_true')
    a = ap.parse_args(); RUN.mkdir(parents=True, exist_ok=True)
    {'refs': cmd_refs, 'cloud': cmd_cloud, 'gdelt': cmd_gdelt, 'check-adapter': cmd_check_adapter, 'web': cmd_web, 'extract': cmd_extract,
     'eventlist': cmd_eventlist, 'packets': cmd_packets, 'score': cmd_score, 'cells': cmd_cells, 'monitor': cmd_monitor, 'pool': cmd_pool,
     'pool-judge': cmd_pool_judge, 'pool-score': cmd_pool_score}[a.cmd](a)

if __name__ == '__main__':
    main()
