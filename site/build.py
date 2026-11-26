"""Build the EventBench program page from the results files.

    python site/build.py               # writes site/index.html (page body, for an Artifact or an embed)
    python site/build.py --standalone  # wraps it in a full HTML document, for static hosting

Standard library only. Every figure on the page is read from results/ and judgments/ at build time, so
rerunning this after a new scoring pass refreshes the page. A few figures that have no results file yet
(precision) fall back to the published defaults below; drop a results/precision.csv with the same columns
to override them. The cost table is computed from the measured results/cost.csv.
"""
from __future__ import annotations

import argparse, csv, html, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PRIV = ROOT / 'internal' / 'aliases.private.json'
_P = json.loads(_PRIV.read_text()) if _PRIV.exists() else {}
COLS, TEXT, PATHS = _P.get('columns', {}), _P.get('text', {}), _P.get('paths', {})

NAMES = {'cloud_monitor': 'GDELT Cloud', 'cloud_filters': 'GDELT Cloud, first page of each list', 'cloud_event': 'GDELT Cloud, Events only', 'gdelt_project': 'GDELT Project 2.0',
         'web_a': 'AI web search A', 'web_b': 'AI web search B', 'web_c': 'AI web search C',
         'web_a_llm': 'Web search A + LLM', 'web_b_llm': 'Web search B + LLM', 'web_c_llm': 'Web search C + LLM'}
COLOR = {'cloud_monitor': 'cloud', 'cloud_filters': 'cloud', 'cloud_event': 'cloud', 'gdelt_project': 'gdelt', 'web_a': 'wa', 'web_b': 'wb', 'web_c': 'wc',
         'web_a_llm': 'wa', 'web_b_llm': 'wb', 'web_c_llm': 'wc'}
SECONDARY = {'cloud_filters', 'cloud_event', 'web_a_llm', 'web_b_llm', 'web_c_llm'}
WEB = ('web_a', 'web_b', 'web_c')
esc = html.escape


def anon(s: str) -> str:
    for k, v in TEXT.items():
        s = s.replace(k, v)
    return s


def path(public: str) -> Path:
    p = ROOT / public
    if p.exists() or public not in PATHS:
        return p
    return ROOT / PATHS[public]


def read_csv(public: str) -> list[dict]:
    p = path(public)
    if not p.exists():
        return []
    return [{COLS.get(k, k): anon(v or '') for k, v in r.items()} for r in csv.DictReader(p.open(newline=''))]


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def pct(x):
    return f'{x * 100:.0f}%'


# ------------------------------------------------------------------ data

def like_for_like(rows):
    """Release 2026.11.1: conflict counts only lethal cases (`scope`), and GDELT Cloud is its blind country-week
    lists under the same single review as every service (`cloud_pages`; first pages `cloud_calls2`; Events
    `cloud_lethal_events`). On news GDELT Cloud is its first review. The first release's columns stay in the file."""
    if not rows or 'scope' not in rows[0] or 'cloud_pages' not in rows[0]:
        return rows
    out = []
    for r in rows:
        r = dict(r)
        if r['family'] == 'conflict':
            if r.get('scope') != 'lethal':
                continue
            r.update(cloud_monitor=r['cloud_pages'], cloud_filters=r['cloud_calls2'], cloud_event=r['cloud_lethal_events'])
        else:
            r.update(cloud_monitor=r.get('cloud_filters', ''), cloud_filters='')
        out.append(r)
    return out


OCC = like_for_like(read_csv('results/occurrences.csv'))
FAM = {'conflict': [r for r in OCC if r['family'] == 'conflict'], 'non-conflict': [r for r in OCC if r['family'] != 'conflict']}
# The headline GDELT Cloud column: place filters plus the second look and recheck when the results carry it.
HEAD = 'cloud_monitor' if any(r.get('cloud_monitor', '') != '' for r in OCC) else 'cloud_filters'


def recall(rows, col):
    t = [r for r in rows if r.get(col, '') != '']
    return sum(r[col] == '1' for r in t), len(t)


def found(rows, col):
    return {r['uid'] for r in rows if r.get(col) == '1'}


def anyweb(rows):
    return {r['uid'] for r in rows if any(r.get(w) == '1' for w in WEB + ('web_c_shared',))}


def listing():
    """Listing test: web A from results/taxonomy_cells.csv; web B from its cell judgments, when present."""
    cells = [r for r in read_csv('results/taxonomy_cells.csv') if not r['cell'].startswith('GOVERNANCE')]
    if not cells:
        return None
    n_cloud = {r['cell']: int(r['cloud_records']) for r in cells}
    i = lambda k: sum(int(r[k] or 0) for r in cells)
    out = {'cells': len(cells), 'cloud_records': sum(n_cloud.values())}
    a = dict(results=i('web_results'), on=i('web_on_cell'), occ=i('web_distinct'), m=i('web_found_in_cloud'),
             samp=i('cloud_sample'), fit=i('cloud_sample_fit'), inweb=i('cloud_sample_in_web'))
    a['cloud_fit_est'] = sum(n_cloud[r['cell']] * (int(r['cloud_sample_fit']) / int(r['cloud_sample']) if int(r['cloud_sample']) else 0) for r in cells)
    out['web_a'] = a
    folder = path('judgments/cells_web_b')
    if folder.exists():
        J = {}
        for f in sorted(folder.glob('*.json')):
            J.update(json.loads(f.read_text()))
        b = dict(results=0, on=0, occ=0, m=0, samp=0, fit=0, inweb=0, cloud_fit_est=0.0)
        for cell, o in J.items():
            if cell not in n_cloud:
                continue
            web, samp = o.get('web', {}), o.get('sample', {})
            groups = {}
            for wid, v in web.items():
                if str(v.get('in_cell')).lower() == 'yes':
                    groups.setdefault(v.get('group') or wid, []).append(v)
            b['results'] += len(web); b['on'] += sum(len(g) for g in groups.values()); b['occ'] += len(groups)
            b['m'] += sum(1 for g in groups.values() if any(x.get('cloud_match') for x in g))
            fit = sum(1 for v in samp.values() if str(v.get('fits')).lower() == 'yes')
            b['samp'] += len(samp); b['fit'] += fit
            b['inweb'] += sum(1 for v in samp.values() if str(v.get('fits')).lower() == 'yes' and v.get('in_web'))
            b['cloud_fit_est'] += n_cloud[cell] * (fit / len(samp) if samp else 0)
        out['web_b'] = b
    for k in ('web_a', 'web_b'):
        s = out.get(k)
        if s and s['m']:
            s['N'] = s['cloud_fit_est'] * s['occ'] / s['m']
    return out


PRECISION_DEFAULT = [
    # label, what was checked, value 0-1, ci_low, ci_high, color key. Accuracy from results/precision_audit.csv;
    # on-topic shares from results/on_topic.csv (40 random conflict country-weeks).
    ('GDELT Cloud Events, fully right', '200 drawn at random; 149 source articles readable', 128 / 149, 0.79, 0.91, 'cloud'),
    ('GDELT Cloud Events, right action', 'Same sample', 148 / 149, 0.96, 1.0, 'cloud'),
    ('GDELT Project rows, fully right', 'All 259 rows coded from the same 98 articles, judged blind', 0.09, None, None, 'gdelt'),
    ('GDELT Project rows, right action', 'Same rows', 0.40, None, None, 'gdelt'),
    ('GDELT Cloud lethal Events on topic', '97 of 102 placed in the country asked, 40 random conflict country-weeks', 97 / 102, None, None, 'cloud'),
    ('AI web search B results on topic', '10 results a question, same country-weeks', 0.61, None, None, 'wb'),
    ('AI web search A results on topic', '10 results a question, same country-weeks', 0.32, None, None, 'wa'),
    ('AI web search C results on topic', 'About 10 results a question, same country-weeks', 0.118, None, None, 'wc'),
    ('GDELT Cloud conflict Stories on topic (the broad list)', 'A random 18 of about 261 records a question', 0.123, None, None, 'cloud'),
    ('Web search + LLM records on topic (relevance, not accuracy)', '123 extracted conflict records', 0.97, None, None, 'wa'),
]


def precision():
    rows = read_csv('results/precision.csv')
    if not rows:
        return PRECISION_DEFAULT
    f = lambda v: float(v) if v not in ('', None) else None
    return [(r['label'], r['checked'], float(r['value']), f(r.get('ci_low')), f(r.get('ci_high')), r.get('color', 'cloud')) for r in rows]


TASKS = {'monitor_conflict': 'Watch a country-week for lethal violence', 'lookup_nonconflict': 'Topic in a country around a date',
         'listing_cell': 'Every X in a country-week'}
SERVICE_NAMES = {'web_a': 'AI web search A', 'web_b': 'AI web search B', 'web_c': 'AI web search C', 'web_a_llm': 'Web search A + LLM',
                 'web_b_llm': 'Web search B + LLM', 'cloud_full': 'GDELT Cloud, full list', 'cloud_filtered': 'GDELT Cloud, filtered',
                 'cloud_monitor': 'GDELT Cloud Monitor (scheduled)'}
QU_PLAN, QU_OVERAGE = 0.033, 0.067  # USD per GDELT Cloud call: per-call rate inside a plan, highest overage rate


def cents(usd):
    return f'{usd * 100:.1f}¢' if usd < 1 else f'${usd:.2f}'


def cost():
    """Rows of (task, service, calls, time, cost per question, cost per find) from the measured results/cost.csv."""
    out = []
    for r in read_csv('results/cost.csv'):
        name = SERVICE_NAMES.get(r['service'], r['service']); task = TASKS.get(r['task'], r['task'])
        if r['service'] == 'cloud_monitor':
            continue
        q, f = int(r['questions'] or 0), int(r['reference_found'] or 0)
        per_q = float(r['api_usd_per_question_mean'] or 0) + float(r['llm_usd_per_question'] or 0)
        calls = r['calls_per_question_mean'] + (f" (median {r['calls_per_question_p50']})" if r['calls_per_question_mean'] != r['calls_per_question_p50'] else '')
        per_f = per_q * q / f if f else None
        if per_f is None: find = ''
        elif r['service'].startswith('cloud'): find = f"{cents(per_f)} ({cents(per_f * QU_OVERAGE / QU_PLAN)} at overage)"
        else: find = cents(per_f)
        if r['task'] == 'listing_cell' and f: find = f'{find} per correct item'
        out.append((task, name, calls, f"{r['latency_s_p50']} s" if r['latency_s_p50'] else '', cents(per_q), find))
    return out


# ------------------------------------------------------------------ components

def bars(rows, cols):
    out = []
    for c in cols:
        k, n = recall(rows, c)
        if not n:
            continue
        lo, hi = wilson(k, n)
        p = k / n
        cls = 'bar sec' if c in SECONDARY else 'bar'
        note = f'{k} of {n} found · 95% interval {pct(lo)}–{pct(hi)}'
        out.append(
            f'<div class="{cls}" title="{esc(note)}"><span class="bl">{esc(NAMES[c])}{"" if n == len(rows) else f" <small>({n} tested)</small>"}</span>'
            f'<span class="bt"><span class="bf c-{COLOR[c]}" style="width:{p * 100:.1f}%"></span>'
            f'<span class="ci" style="left:{lo * 100:.1f}%;width:{(hi - lo) * 100:.1f}%"></span></span>'
            f'<span class="bv">{pct(p)}</span></div>')
    return ''.join(out)


def venn(a, b, c, labels, colors, caption, total):
    reg = {'a': len(a - b - c), 'b': len(b - a - c), 'c': len(c - a - b), 'ab': len((a & b) - c), 'ac': len((a & c) - b),
           'bc': len((b & c) - a), 'abc': len(a & b & c)}
    none = total - len(a | b | c)
    pos = {'a': (120, 128), 'b': (240, 128), 'c': (180, 228), 'ab': (180, 112), 'ac': (140, 192), 'bc': (220, 192), 'abc': (180, 162)}
    s = [f'<figure class="venn"><svg viewBox="0 0 360 330" role="img" aria-label="{esc(caption)}">']
    for (cx, cy), col in zip([(140, 145), (220, 145), (180, 210)], colors):
        s.append(f'<circle cx="{cx}" cy="{cy}" r="88" class="vc c-{col}"/>')
    for k, (x, y) in pos.items():
        s.append(f'<text x="{x}" y="{y}" class="vn">{reg[k]}</text>')
    s.append(f'<text x="12" y="30" class="vl t-{colors[0]}">{esc(labels[0])} · {len(a)}</text>')
    s.append(f'<text x="348" y="30" class="vl t-{colors[1]}" text-anchor="end">{esc(labels[1])} · {len(b)}</text>')
    s.append(f'<text x="180" y="318" class="vl t-{colors[2]}" text-anchor="middle">{esc(labels[2])} · {len(c)}</text>')
    s.append('</svg>')
    s.append(f'<figcaption><b>{esc(caption)}</b><span>{total} occurrences · {none} found by none</span></figcaption></figure>')
    return ''.join(s)


def mark(v):
    return '<span class="ok">found</span>' if v == '1' else ('<span class="no">missed</span>' if v == '0' else '<span class="na">not run</span>')


def case_flow():
    r = next((x for x in OCC if x['uid'] == 'U646770'), None)
    if not r:
        return ''
    lanes = [
        ('cloud', 'GDELT Cloud', 'events and stories, every page: 150 km radius, country (either actor), all categories', '476 records back · 42 best place matches shown', r.get(HEAD)),
        ('gdelt', 'GDELT Project 2.0', 'public 15-minute export files, CAMEO 18–20, within 100 km, Oct 20–24', '114 rows from 70 articles · 25 nearest shown', r.get('gdelt_project')),
        ('wa', 'AI web search A', '“people killed in attacks, clashes or violence in Ukraine October 19-25 2026”', 'top 10, shared by every Ukrainian case that week', r.get('web_a')),
        ('wb', 'AI web search B', 'the same question, news category, publication window', 'top 10, shared that week', r.get('web_b')),
        ('wc', 'AI web search C', 'the keyword form “Ukraine attack killed”, news mode, date range', 'top 20, shared that week', r.get('web_c')),
        ('wa', 'Web search + LLM', 'an LLM turns each results page into distinct incident records', 'records from A, B and C', '1' if '1' in (r.get('web_a_llm'), r.get('web_b_llm'), r.get('web_c_llm')) else r.get('web_a_llm')),
    ]
    lane_html = ''.join(
        f'<li class="lane"><span class="dot c-{c}"></span><div><b>{esc(n)}</b><span class="ask">{esc(ask)}</span><span class="got">{esc(got)}</span></div>{mark(v)}</li>'
        for c, n, ask, got, v in lanes)
    return f'''
<div class="flow">
  <div class="step ref"><span class="eyebrow">Reference · UCDP row U646770</span><b>21 Oct 2026 · Lymanivka, Lozova raion, Kharkiv oblast</b><span>Russia vs Ukraine · 1 killed</span></div>
  <div class="arrow" aria-hidden="true"></div>
  <div class="step q"><span class="eyebrow">What every service is asked</span><b>Place, week and topic. Never the incident.</b><span>Ukraine · Oct 19–25 · lethal violence</span></div>
  <div class="arrow" aria-hidden="true"></div>
  <ul class="lanes">{lane_html}</ul>
  <div class="arrow" aria-hidden="true"></div>
  <div class="step judge"><span class="eyebrow">Blind review</span><b>67 records for this case plus the week's shared results, shuffled, source names removed</b><span>Verdict: two records describe it, both GDELT Cloud (an Event and a Story). “Lymanivka Oct 22 woman killed 4 hurt; one day later than reference, plausible same.”</span></div>
</div>'''


# ------------------------------------------------------------------ page

CSS = r'''
:root{
  /* Layout: one reading column with a section rail on wide screens; charts and diagrams sit full width inside it. */
  --bg:#f2f4f6; --paper:#ffffff; --ink:#121a22; --muted:#5b6672; --rule:#d8dee5; --soft:#e8ecf0;
  --cloud:#1f5bd8; --gdelt:#b8740b; --wa:#66727f; --wb:#7a52c8; --wc:#9b7560; --ok:#17784a; --no:#b4392e;
  --display:"Archivo","Arial Narrow",system-ui,sans-serif; --body:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1217;--paper:#141b22;--ink:#e6ebf0;--muted:#98a4b0;--rule:#26303a;--soft:#1c242d;--cloud:#6b96ff;--gdelt:#e2a640;--wa:#9aa6b3;--wb:#a98af0;--wc:#c9a690;--ok:#4cc38a;--no:#f07a6c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0d1217;--paper:#141b22;--ink:#e6ebf0;--muted:#98a4b0;--rule:#26303a;--soft:#1c242d;--cloud:#6b96ff;--gdelt:#e2a640;--wa:#9aa6b3;--wb:#a98af0;--wc:#c9a690;--ok:#4cc38a;--no:#f07a6c;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.6 var(--body);margin:0}
.wrap{max-width:1080px;margin:0 auto;padding-block:40px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:56px}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0;letter-spacing:-.01em}
h1{font-size:clamp(34px,6vw,60px);line-height:1.02;font-weight:800}
h2{font-size:clamp(24px,3.2vw,32px);font-weight:700}
h3{font-size:18px;font-weight:700}
p{margin:0;max-width:66ch}
small{color:var(--muted);font-size:.8em}
.eyebrow{font:500 12px/1.2 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
section{display:grid;grid-template-columns:180px minmax(0,1fr);gap:24px}
section>.rail{padding-top:6px;border-top:2px solid var(--ink)}
section>.body{display:flex;flex-direction:column;gap:20px;min-width:0}
@media (max-width:820px){section{grid-template-columns:minmax(0,1fr);gap:12px}section>.rail{border-top-width:1px}}
.hero{display:flex;flex-direction:column;gap:22px}
.hero .lede{font-size:clamp(18px,2.2vw,22px);line-height:1.45;color:var(--ink);max-width:40ch}
.hero .board{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}
.panel{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:20px;min-width:0}
.panel h3{margin-bottom:12px}
.bar{display:grid;grid-template-columns:minmax(0,190px) minmax(0,1fr) 48px;align-items:center;gap:12px;padding:5px 0}
.bar.sec{opacity:.75}
.bar.sec .bl{font-size:13px}
.bl{font-size:14px;line-height:1.25}
.bt{position:relative;height:14px;background:var(--soft);border-radius:3px}
.bf{position:absolute;left:0;top:0;bottom:0;border-radius:3px}
.bar.sec .bf{opacity:.55}
.ci{position:absolute;top:50%;height:2px;margin-top:-1px;background:var(--ink);opacity:.55}
.ci::before,.ci::after{content:"";position:absolute;top:-4px;width:2px;height:10px;background:var(--ink)}
.ci::before{left:0}.ci::after{right:0}
.bv{font:600 15px var(--mono);text-align:right;font-variant-numeric:tabular-nums}
@media (max-width:520px){.bar{grid-template-columns:minmax(0,1fr) 44px}.bar .bl{grid-column:1/-1}.bar .bt{grid-column:1}}
.c-cloud{background:var(--cloud)} .c-gdelt{background:var(--gdelt)} .c-wa{background:var(--wa)} .c-wb{background:var(--wb)} .c-wc{background:var(--wc)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:2px;display:inline-block}
.ctx{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}
.ctx .panel{display:flex;flex-direction:column;gap:10px}
.ctx svg{width:100%;height:auto;max-width:100%}
.ctx .tag{align-self:flex-start;font:500 12px var(--mono);padding:3px 8px;border-radius:999px;background:var(--cloud);color:var(--paper)}
.ctx .tag.later{background:var(--soft);color:var(--muted)}
.ctx q{font-family:var(--mono);font-size:14px;quotes:none}
.flow{display:flex;flex-direction:column;align-items:stretch;gap:0}
.step{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:4px}
.step span:not(.eyebrow){color:var(--muted);font-size:14px}
.arrow{width:2px;height:22px;background:var(--rule);margin:0 auto;position:relative}
.arrow::after{content:"";position:absolute;bottom:-1px;left:-4px;border:5px solid transparent;border-top-color:var(--rule)}
.lanes{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:10px}
.lane{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px 14px;display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:10px;align-items:start}
.lane .dot{width:10px;height:10px;border-radius:50%;margin-top:6px}
.lane div{display:flex;flex-direction:column;gap:2px;min-width:0}
.lane .ask{font-size:13px;color:var(--muted)}
.lane .got{font:12px var(--mono);color:var(--muted)}
.ok,.no,.na{font:600 12px var(--mono);padding:3px 8px;border-radius:999px;white-space:nowrap}
.ok{color:var(--ok);background:color-mix(in srgb,var(--ok) 14%,transparent)}
.no{color:var(--no);background:color-mix(in srgb,var(--no) 12%,transparent)}
.na{color:var(--muted);background:var(--soft)}
.venns{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}
.venn{margin:0;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px}
.venn svg{width:100%;height:auto}
.vc{fill-opacity:.16;stroke-width:2}
.vc.c-cloud{fill:var(--cloud);stroke:var(--cloud)} .vc.c-gdelt{fill:var(--gdelt);stroke:var(--gdelt)} .vc.c-wa{fill:var(--wa);stroke:var(--wa)} .vc.c-wb{fill:var(--wb);stroke:var(--wb)} .vc.c-wc{fill:var(--wc);stroke:var(--wc)}
.vn{font:700 17px var(--mono);fill:var(--ink);text-anchor:middle;dominant-baseline:central}
.vl{font:600 12px var(--body)}
.t-cloud{fill:var(--cloud)} .t-gdelt{fill:var(--gdelt)} .t-wa{fill:var(--wa)} .t-wb{fill:var(--wb)} .t-wc{fill:var(--wc)}
.venn figcaption{display:flex;flex-direction:column;font-size:14px}
.venn figcaption span{color:var(--muted);font-size:13px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:14px}
.stat{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:10px}
.stat .row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:baseline;font-size:14px}
.stat .row b{font:600 18px var(--mono);font-variant-numeric:tabular-nums}
.dots{display:flex;flex-wrap:wrap;gap:3px}
.dots i{width:7px;height:7px;border-radius:50%;display:block}
.tbl{overflow-x:auto;background:var(--paper);border:1px solid var(--rule);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
tr:last-child td{border-bottom:0}
td.k{font-weight:600}
.pipes{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px}
.pipe{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:8px}
.pipe ol{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;counter-reset:s}
.pipe li{display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;font-size:14px;counter-increment:s}
.pipe li::before{content:counter(s);font:600 12px var(--mono);color:var(--muted);padding-top:2px}
.pipe .out{margin-top:6px;padding-top:10px;border-top:1px solid var(--rule);display:flex;gap:18px;flex-wrap:wrap}
.pipe .out b{font:700 26px var(--mono);display:block}
.pipe h3{display:flex;align-items:center;gap:8px}.pipe h3::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--pc)}
.pipe.cloud{--pc:var(--cloud)} .pipe.gdelt{--pc:var(--gdelt)}
.stream{font:13px var(--mono);color:var(--muted);text-align:center;padding:8px;border:1px dashed var(--rule);border-radius:10px}
.qa{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}
.qa details{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px 14px}
.qa summary{cursor:pointer;font-weight:600}
.qa details p{margin-top:8px;color:var(--muted);font-size:14px}
pre{margin:0;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px;overflow-x:auto;font:13px/1.6 var(--mono)}
a{color:var(--cloud)}
:focus-visible{outline:2px solid var(--cloud);outline-offset:2px}
.foot{font-size:13px;color:var(--muted);display:flex;flex-direction:column;gap:6px}
'''


def pooled_lede():
    """The pooled headline, from results/pooled_summary.csv and pooled_compare.csv (pool_report.py): armed conflict, first juror,
    as each service's share of every incident any service found, with the same share averaged week by week beside it."""
    if not (path('results/pooled_compare.csv').exists() and path('results/pooled_summary.csv').exists()):
        return ''
    cmp = next((x for x in read_csv('results/pooled_compare.csv') if x['juror'] == 'juror_a' and x['scope'] == 'armed_conflict' and x['service'] == 'cloud' and x['versus'] == 'web_b'), None)
    row = {x['service']: x for x in read_csv('results/pooled_summary.csv') if x['juror'] == 'juror_a' and x['scope'] == 'armed_conflict'}
    if not cmp or not cmp['ratio'] or 'cloud' not in row or 'web_b' not in row:
        return ''
    c, w = row['cloud'], row['web_b']
    pc = lambda v: f'{round(float(v) * 100)}%'
    weekly = f'; averaged week by week, {pc(c["mean_question_share"])} against {pc(w["mean_question_share"])}' if c.get('mean_question_share') and w.get('mean_question_share') else ''
    return (f'Asked who was killed in armed conflict in a country and week, GDELT Cloud returned {pc(c["share_of_pool"])} of the {c["pool"]} distinct incidents '
            f'any service found in {c["questions"]} country-weeks, against {pc(w["share_of_pool"])} for the best AI web search ({float(cmp["ratio"]):.1f}×{weekly}). ')


def page():
    cf, nc = FAM['conflict'], FAM['non-conflict']
    kc, nc_n = recall(cf, HEAD); kn, nn = recall(nc, HEAD)
    best = max(WEB, key=lambda w: (recall(cf, w)[0] / max(1, recall(cf, w)[1])) if recall(cf, w)[1] > 100 else 0)
    bk, bn = recall(cf, best); bkn, bnn = recall(nc, best)
    order = [HEAD] + (['cloud_filters'] if HEAD != 'cloud_filters' else []) + ['cloud_event', 'gdelt_project', 'web_b', 'web_a', 'web_c', 'web_b_llm', 'web_a_llm', 'web_c_llm']
    legend = ''.join(f'<span><i class="c-{COLOR[c]}"></i>{esc(NAMES[c])}</span>' for c in (HEAD, 'gdelt_project', 'web_a', 'web_b', 'web_c'))

    C, G, W = found(cf, HEAD), found(cf, 'gdelt_project'), anyweb(cf)
    venns = [venn(C, G, W, ['GDELT Cloud', 'GDELT Project', 'Any AI web search'], ['cloud', 'gdelt', 'wa'], 'Conflict: who found what', len(cf)),
             venn(C, found(cf, 'web_a'), found(cf, 'web_b'), ['GDELT Cloud', 'Web search A', 'Web search B'], ['cloud', 'wa', 'wb'], 'Conflict: GDELT Cloud and two AI web searches', len(cf)),
             venn(found(nc, HEAD), found(nc, 'web_a'), found(nc, 'web_b'), ['GDELT Cloud', 'Web search A', 'Web search B'], ['cloud', 'wa', 'wb'], 'Non-conflict: GDELT Cloud and two AI web searches', len(nc))]
    only_cloud = len(C - G - W); only_web = len(W - C - G); nobody = len(cf) - len(C | G | W)

    L = listing()
    listing_html = ''
    if L:
        per_cell_cloud = L['web_a']['cloud_fit_est'] / L['cells']
        cards = []
        for key, label, col in (('web_a', 'AI web search A', 'wa'), ('web_b', 'AI web search B', 'wb')):
            s = L.get(key)
            if not s:
                continue
            per = s['occ'] / L['cells']
            cards.append(f'''<div class="stat"><span class="eyebrow">{label} · one search per cell</span>
<div class="row"><span>Distinct in-cell occurrences per search</span><b>{per:.1f}</b></div>
<div class="dots" aria-hidden="true">{''.join(f'<i class="c-{col}"></i>' for _ in range(round(per)))}</div>
<div class="row"><span>Results that fit the cell</span><b>{pct(s['on'] / s['results'])}</b></div>
<div class="row"><span>GDELT Cloud's list holds</span><b title="{s['m']} of {s['occ']} verified web items">{pct(s['m'] / s['occ'])} of these</b></div>
<div class="row"><span>This search returned</span><b title="{s['inweb']} of {s['fit']} sampled Cloud records that fit">{pct(s['inweb'] / s['fit'])} of Cloud's</b></div>
<div class="row"><span>Estimated share of everything</span><b title="Lincoln–Petersen: N ≈ {s['N']:.0f} occurrences across the cells; an upper bound">{pct(s['occ'] / s['N'])}</b></div></div>''')
        cloud_card = f'''<div class="stat"><span class="eyebrow">GDELT Cloud · complete list per cell</span>
<div class="row"><span>In-cell records per cell</span><b>{per_cell_cloud:.0f}</b></div>
<div class="dots" aria-hidden="true">{''.join('<i class="c-cloud"></i>' for _ in range(round(per_cell_cloud)))}</div>
<div class="row"><span>Records that fit the cell</span><b title="{L['web_a']['fit']} of {L['web_a']['samp']} sampled">{pct(L['web_a']['fit'] / L['web_a']['samp'])}</b></div>
<div class="row"><span>Records returned</span><b>{L['cloud_records']:,}</b></div>
<div class="row"><span>Estimated share of everything</span><b title="Lincoln–Petersen against each web search; upper bounds">{'–'.join(sorted({pct(L[k]['cloud_fit_est'] / L[k]['N']) for k in ('web_a', 'web_b') if L.get(k) and L[k].get('N')}))}</b></div></div>'''
        listing_html = f'<div class="stats">{cloud_card}{"".join(cards)}</div>'

    prec = ''.join(
        f'<div class="bar" title="{esc(chk)}"><span class="bl">{esc(lbl)}</span><span class="bt"><span class="bf c-{col}" style="width:{v * 100:.1f}%"></span>'
        + (f'<span class="ci" style="left:{lo * 100:.1f}%;width:{(hi - lo) * 100:.1f}%"></span>' if lo is not None else '')
        + f'</span><span class="bv">{pct(v)}</span></div>' for lbl, chk, v, lo, hi, col in precision())

    struct = read_csv('results/structure.csv')
    srows = ''.join(f'<tr><td class="k">{esc(r["field"][:1].upper() + r["field"][1:])}</td><td>{esc(r["gdelt_cloud_event_present"])}'
                    f'{(" · " + esc(r["gdelt_cloud_event_correct"])) if r["gdelt_cloud_event_correct"] else ""}</td>'
                    f'<td>{esc(r["search_plus_llm_record_present"])}</td><td>{esc(r["web_result_present"])}</td></tr>' for r in struct)

    costs = ''.join(f'<tr><td><small>{esc(t)}</small></td><td class="k">{esc(n)}</td><td>{esc(c)}</td><td>{esc(tm)}</td><td>{esc(q)}</td><td>{esc(f)}</td></tr>' for t, n, c, tm, q, f in cost())

    qa = [
        ('UCDP is the wrong denominator', 'It is independent of every service, public, and counts single deaths, so it is hard for everyone. Indepaz, SATP and five non-conflict lists are added, and every panel is reported on its own.'),
        ('UCDP is human-built and not real time', 'UCDP researchers code each event by hand from news, NGO and local sources; the Candidate release comes about a month after the events and the final dataset once a year. That makes it an independent yardstick, and a hard one.'),
        ('Web search was not given a fair chance', 'Each web service was asked in the query style its own documentation recommends, in its own news or date-window mode. A deeper-search configuration and a lookup mode, where web search is strongest, come next.'),
        ('An AI judged it', 'Claude reviewers, a different model family from the one GDELT Cloud uses for coding. Records shuffled, sources hidden. A second reviewer re-judged 40 incidents: κ = 0.83. The pooled run had two jurors from different labs judging every record, and a third model audited a sample blind. Every verdict is published.'),
        ('Searching after the fact', 'Web indexes gain follow-up coverage with hindsight, so web figures are, if anything, high. Timeliness is not measured.'),
        ('Why are the web services anonymous?', 'Their terms restrict publishing named comparisons. The scores describe how this kind of tool behaves on monitoring questions. To compare a service you use, plug it in: any web search service works through a small adapter.'),
        ('What is web search + LLM?', 'The pipeline a developer builds to imitate an event feed: run the search, hand the results page to an LLM, get back de-duplicated records with date, place, parties, deaths and sources. It cannot find what the search did not return.'),
        ('GDELT Cloud depends on how you query it', 'It does, which is why release 2026.11\'s conflict figures are withdrawn: they searched around each incident and gave GDELT Cloud alone a second look. Every figure here comes from country-week queries any customer would send, reviewed like everyone else\'s. Its first page of each list alone returned ' + pct(recall(FAM['conflict'], 'cloud_filters')[0] / max(1, recall(FAM['conflict'], 'cloud_filters')[1])) + ' of lethal conflict incidents, every page ' + pct(recall(FAM['conflict'], HEAD)[0] / max(1, recall(FAM['conflict'], HEAD)[1])) + '.'),
    ]
    qa_html = ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in qa)

    return f'''<title>GDELT Cloud EventBench</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header class="hero">
  <span class="eyebrow">Release 2026.11.1 · {len(OCC)} reference occurrences</span>
  <h1>EventBench</h1>
  <p class="lede">{pooled_lede()}Against the reference lists, asked by place, time and topic without naming the incident, GDELT Cloud returned {pct(kc / nc_n)} of {nc_n} lethal conflict incidents and {pct(kn / nn)} of {nn} news and official items; the best AI web search API returned {pct(bk / bn)} and {pct(bkn / bnn)}.</p>
  <div class="legend">{legend}</div>
  <div class="board">
    <div class="panel"><h3>Conflict · {len(cf)} incidents</h3>{bars(cf, order)}</div>
    <div class="panel"><h3>Non-conflict · {len(nc)} news and official items</h3>{bars(nc, order)}</div>
  </div>
  <small>Bars show recall: the share of reference occurrences a service returned. Whiskers are 95% intervals. Hover a bar for counts. Faded rows are variants.</small>
</header>

<section><div class="rail"><span class="eyebrow">Two contexts</span></div><div class="body">
  <h2>Monitoring or lookup</h2>
  <div class="ctx">
    <div class="panel"><span class="tag">Measured here</span><h3>Monitoring: you don't know it happened yet</h3>
      <svg viewBox="0 0 300 120" role="img" aria-label="A filter by place, week and topic sweeps a field of unknown events">
        <rect x="1" y="1" width="298" height="118" rx="8" fill="none" stroke="var(--rule)"/>
        <g fill="var(--muted)" opacity=".5"><circle cx="40" cy="30" r="4"/><circle cx="70" cy="80" r="4"/><circle cx="120" cy="45" r="4"/><circle cx="160" cy="95" r="4"/><circle cx="210" cy="30" r="4"/><circle cx="250" cy="70" r="4"/><circle cx="270" cy="100" r="4"/><circle cx="95" cy="20" r="4"/></g>
        <rect x="100" y="25" width="130" height="80" rx="6" fill="var(--cloud)" fill-opacity=".12" stroke="var(--cloud)" stroke-dasharray="4 3"/>
        <g fill="var(--cloud)"><circle cx="120" cy="45" r="5"/><circle cx="160" cy="95" r="5"/><circle cx="210" cy="30" r="5"/><circle cx="185" cy="62" r="5"/></g>
      </svg>
      <q>people killed in attacks in Mali, Oct 5–11</q>
      <p>A watch desk, a risk feed or an analyst scanning a region asks by place, time and topic. Every recall figure on this page is this context.</p></div>
    <div class="panel"><span class="tag later">Next release</span><h3>Lookup: you already know it happened</h3>
      <svg viewBox="0 0 300 120" role="img" aria-label="A named event leads straight to one result">
        <rect x="1" y="1" width="298" height="118" rx="8" fill="none" stroke="var(--rule)"/>
        <g fill="var(--muted)" opacity=".35"><circle cx="40" cy="30" r="4"/><circle cx="70" cy="80" r="4"/><circle cx="160" cy="95" r="4"/><circle cx="250" cy="70" r="4"/><circle cx="270" cy="100" r="4"/><circle cx="95" cy="20" r="4"/></g>
        <line x1="40" y1="60" x2="196" y2="60" stroke="var(--wb)" stroke-width="2"/>
        <circle cx="210" cy="60" r="12" fill="var(--wb)" fill-opacity=".2" stroke="var(--wb)" stroke-width="2"/><circle cx="210" cy="60" r="5" fill="var(--wb)"/>
      </svg>
      <q>Boulkessi base attack, 7 October</q>
      <p>A reporter following up a known event asks by name. Web search is built for this: describe the item and the top result is usually it.</p></div>
  </div>
</div></section>

<section><div class="rail"><span class="eyebrow">One case</span></div><div class="body">
  <h2>One incident, every service</h2>
  <p>A single death in Kharkiv oblast, from the UCDP reference list, followed through the benchmark.</p>
  {case_flow()}
</div></section>

<section><div class="rail"><span class="eyebrow">Overlap</span></div><div class="body">
  <h2>Who found what</h2>
  <p>On conflict, GDELT Cloud alone found {only_cloud} incidents and web search alone found {only_web}. {nobody} of {len(cf)} were found by no service.</p>
  <div class="venns">{''.join(venns)}</div>
  <small>Region counts are exact. Circle sizes are not to scale. "Any AI web search" is A, B or C.</small>
</div></section>

<section><div class="rail"><span class="eyebrow">Listing</span></div><div class="body">
  <h2>Every X in country Y this week</h2>
  <p>{L['cells'] if L else 40} cells: 8 categories in 5 countries, plus Protests in 5 more, Nov 9–15. Reviewers verified every web result, looked it up in GDELT Cloud's list, and checked a sample of Cloud's records.</p>
  {listing_html}
  <small>Shares of everything come from a two-list capture–recapture estimate. Both services favour prominent news, so the true totals are larger and every share is an upper bound.</small>
</div></section>

<section><div class="rail"><span class="eyebrow">Precision</span></div><div class="body">
  <h2>Of what came back, how much was right</h2>
  <div class="panel">{prec}</div>
</div></section>

<section><div class="rail"><span class="eyebrow">Structure</span></div><div class="body">
  <h2>What a record carries</h2>
  <div class="tbl"><table><thead><tr><th>Field</th><th>GDELT Cloud Event: present · correct</th><th>Web search + LLM record</th><th>Web result</th></tr></thead><tbody>{srows}</tbody></table></div>
</div></section>

<section><div class="rail"><span class="eyebrow">Same input</span></div><div class="body">
  <h2>Why GDELT Cloud beats the GDELT Project on the same article stream</h2>
  <div class="stream">The GDELT Project article stream · plus, for GDELT Cloud only, 440+ regional native feeds and translated non-English sources</div>
  <div class="pipes">
    <div class="pipe gdelt"><h3>GDELT Project 2.0</h3><ol><li>Dictionary coding, one row per actor–action pattern in a sentence</li><li>Actor strings and the first place named</li><li>Publication date</li><li>Rows never merged across articles</li></ol>
      <div class="out"><span><b>4.1</b><small>rows per incident</small></span><span><b>9%</b><small>rows fully right</small></span></div></div>
    <div class="pipe cloud"><h3>GDELT Cloud</h3><ol><li>A language model reads the article and decides whether an event happened</li><li>Parties with roles, resolved to entities; coordinates and locality</li><li>Occurrence date with its basis</li><li>Articles clustered into one Story, one Event per occurrence</li></ol>
      <div class="out"><span><b>1.2</b><small>records per incident</small></span><span><b>88%</b><small>fully right, same 98 articles</small></span></div></div>
  </div>
</div></section>

<section><div class="rail"><span class="eyebrow">Cost</span></div><div class="body">
  <h2>Cost, time and value per task</h2>
  <div class="tbl"><table><thead><tr><th>Task</th><th>Service</th><th>Calls per question</th><th>Time (median)</th><th>Cost per question</th><th>Cost per reference item found</th></tr></thead><tbody>{costs}</tbody></table></div>
  <small>Measured, at list prices; a GDELT Cloud call at 3.3¢ in a plan, 6.7¢ at the highest overage. A single search is the cheapest way to check on something; spending more on search does not reach GDELT Cloud's coverage; per correct item in a list the cost is the same, and scheduled Monitors use no query units.</small>
</div></section>

<section><div class="rail"><span class="eyebrow">Limits</span></div><div class="body">
  <h2>Criticisms we expect</h2>
  <div class="qa">{qa_html}</div>
</div></section>

<section><div class="rail"><span class="eyebrow">Reproduce</span></div><div class="body">
  <h2>Run it yourself</h2>
  <p>Python 3.10+, standard library only, and a GDELT Cloud API key. Any web search service plugs in through a small adapter, and any event list through a CSV; AGENTS.md walks a person or a coding agent through it. Every paid call is reserved in a local ledger and stops at your cap.</p>
  <pre>python -m unittest discover tests
python bench.py refs
python bench.py cloud
python bench.py gdelt
python bench.py check-adapter --adapter adapters/my_search.py
python bench.py web --adapter adapters/my_search.py --label my_search --max-usd 5
python bench.py eventlist --file my_events.csv --label my_list
python bench.py packets
python bench.py score
python report.py --results run/occurrences.csv</pre>
</div></section>

<footer class="foot">
  <span>Reference lists: UCDP Candidate Events (CC BY 4.0) · Wikipedia Current Events (CC BY-SA 4.0) · USGS (public domain) · Indepaz, SATP, WHO, GDACS, election and rate calendars (facts and links). GDELT Project 2.0 open data.</span>
  <span>Code MIT. Results and judgments CC BY 4.0. Reviewers: Claude models, a different model family from the one GDELT Cloud uses for coding.</span>
</footer>
</div>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--standalone', action='store_true', help='wrap in a full HTML document for static hosting')
    ap.add_argument('--out', default=str(ROOT / 'site' / 'index.html'))
    a = ap.parse_args()
    body = page()
    if a.standalone:
        body = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' + body.replace('<div class="wrap">', '</head><body><div class="wrap">', 1) + '</body></html>')
    Path(a.out).write_text(body)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
