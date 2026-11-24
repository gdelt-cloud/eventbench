"""Build a self-contained HTML report from results/occurrences.csv.

    python report.py                          # writes results/report.html
    python report.py --aliases aliases.json   # map service columns to display names

The report puts the two contexts first (monitoring for what you don't know yet vs looking up
what you already know), then recall with 95% intervals, Venn diagrams of who found what, and a
case browser. Standard library only.
"""
from __future__ import annotations

import argparse, csv, html, json, math
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Column in occurrences.csv -> default display name. Web services carry anonymous labels.
DEFAULT_ALIASES = OrderedDict([
    ('cloud_monitor', 'GDELT Cloud'),
    ('cloud_filters', 'GDELT Cloud, place filters only'),
    ('gdelt_project', 'GDELT Project 2.0'),
    ('web_a', 'AI web search A'),
    ('web_b', 'AI web search B'),
    ('web_c', 'AI web search C'),
    ('web_c_shared', 'AI web search C, long question'),
    ('web_a_llm', 'Web search A + LLM'),
    ('web_b_llm', 'Web search B + LLM'),
    ('web_c_llm', 'Web search C + LLM'),
])
WEB = ('web_a', 'web_b', 'web_c', 'web_c_shared')
PRIVATE = ROOT / 'internal' / 'aliases.private.json'


def canonical(rows):
    """Working copies may still carry service-specific column names; rename them when the private map exists."""
    if not PRIVATE.exists():
        return rows
    cols = json.loads(PRIVATE.read_text()).get('columns', {})
    return [{cols.get(k, k): v for k, v in r.items()} for r in rows]


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def tested(v):
    return v not in ('', None)


def venn_svg(a, b, c, labels, colors):
    """Three-set Venn with exact region counts (not area-proportional). a, b, c are sets of ids."""
    regions = {
        'a': len(a - b - c), 'b': len(b - a - c), 'c': len(c - a - b),
        'ab': len((a & b) - c), 'ac': len((a & c) - b), 'bc': len((b & c) - a), 'abc': len(a & b & c),
    }
    pos = {'a': (150, 150), 'b': (250, 150), 'c': (200, 235), 'ab': (200, 125), 'ac': (160, 210),
           'bc': (240, 210), 'abc': (200, 175)}
    s = ['<svg viewBox="0 0 400 340" width="100%" style="max-width:420px" role="img" aria-label="Venn diagram">']
    for (cx, cy), col in zip([(150, 150), (250, 150), (200, 235)], colors):
        s.append(f'<circle cx="{cx}" cy="{cy}" r="95" fill="{col}" fill-opacity=".18" stroke="{col}" stroke-width="2"/>')
    for k, (x, y) in pos.items():
        s.append(f'<text x="{x}" y="{y + 5}" text-anchor="middle" class="vn">{regions[k]}</text>')
    s.append(f'<text x="70" y="40" class="vl" fill="{colors[0]}">{html.escape(labels[0])} · {len(a)}</text>')
    s.append(f'<text x="330" y="40" text-anchor="end" class="vl" fill="{colors[1]}">{html.escape(labels[1])} · {len(b)}</text>')
    s.append(f'<text x="200" y="335" text-anchor="middle" class="vl" fill="{colors[2]}">{html.escape(labels[2])} · {len(c)}</text>')
    s.append('</svg>')
    return ''.join(s)


def build(rows, aliases, title, run_label):
    cols = [c for c in aliases if c in rows[0]]
    # The headline GDELT Cloud column: with the second look and recheck when the results carry it.
    cloud = 'cloud_monitor' if 'cloud_monitor' in cols else 'cloud_filters'
    panels = OrderedDict()
    for r in rows:
        panels.setdefault(r['panel'], []).append(r)

    def recall(sub, col):
        t = [r for r in sub if tested(r.get(col))]
        k = sum(int(r[col]) for r in t)
        return k, len(t)

    fams = OrderedDict([('conflict', [r for r in rows if r['family'] == 'conflict']),
                        ('non-conflict', [r for r in rows if r['family'] != 'conflict'])])
    head = ''.join(f'<th>{html.escape(aliases[c])}</th>' for c in cols)
    def cells(sub):
        out = []
        for c in cols:
            k, n = recall(sub, c)
            if not n:
                out.append('<td class="na">not tested</td>'); continue
            lo, hi = wilson(k, n)
            out.append(f'<td class="n"><b>{k / n:.0%}</b><span class="ci">{k}/{n} · {lo:.0%}–{hi:.0%}</span></td>')
        return ''.join(out)
    top = ''.join(f'<tr><td>{f.capitalize()} · {len(s)} occurrences</td>{cells(s)}</tr>' for f, s in fams.items() if s)
    by_panel = ''.join(f'<tr><td>{html.escape(p)} · {len(s)}</td>{cells(s)}</tr>' for p, s in panels.items())

    venns = []
    colors = ['#3b6fd6', '#a5803f', '#7d8794']
    for fam, sub in fams.items():
        if not sub:
            continue
        A = {r['uid'] for r in sub if r.get(cloud) == '1'}
        B = {r['uid'] for r in sub if r.get('gdelt_project') == '1'}
        C = {r['uid'] for r in sub if any(r.get(w) == '1' for w in WEB)}
        if any(tested(r.get('gdelt_project')) for r in sub):
            venns.append(f'<figure><figcaption>{fam.capitalize()}: who found what ({len(sub)} occurrences, {len(sub) - len(A | B | C)} found by none)</figcaption>'
                         + venn_svg(A, B, C, [aliases[cloud], aliases['gdelt_project'], 'Any AI web search'], colors) + '</figure>')
        web_cols = [w for w in WEB if any(tested(r.get(w)) for r in sub)][:2]
        if len(web_cols) == 2:
            W1 = {r['uid'] for r in sub if r.get(web_cols[0]) == '1'}
            W2 = {r['uid'] for r in sub if r.get(web_cols[1]) == '1'}
            venns.append(f'<figure><figcaption>{fam.capitalize()}: GDELT Cloud and two AI web searches</figcaption>'
                         + venn_svg(A, W1, W2, [aliases[cloud], aliases[web_cols[0]], aliases[web_cols[1]]], ['#3b6fd6', '#7d8794', '#8a5cc4']) + '</figure>')

    data = [{'uid': r['uid'], 'panel': r['panel'], 'country': r['country'], 'date': r['date'], 'what': r['what'][:160],
             'note': r.get('note', '')[:200], **{c: r.get(c, '') for c in cols}} for r in rows]
    alias_js = json.dumps({c: aliases[c] for c in cols})
    return TEMPLATE.format(title=html.escape(title), run=html.escape(run_label), head=head, top=top, by_panel=by_panel,
                           venns=''.join(venns), data=json.dumps(data), aliases=alias_js, n=len(rows), cloud=json.dumps(cloud))


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f6f7f8;--paper:#fff;--fg:#15181c;--muted:#5a626c;--rule:#dde1e6;--good:#1e7a4a;--bad:#b3362c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111418;--paper:#191d22;--fg:#e8ebef;--muted:#9aa3ad;--rule:#2c3238;--good:#57c08a;--bad:#ef7a6f;color-scheme:dark}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;padding:28px max(16px,4vw)}}
main{{max-width:980px;margin:0 auto;display:flex;flex-direction:column;gap:24px}}
section{{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:20px;min-width:0}}
h1{{margin:0;font-size:30px}} h2{{margin:0 0 10px;font-size:20px}} p{{max-width:72ch;margin:6px 0}}
.ctx{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}} .ctx div{{border-top:3px solid var(--rule);padding-top:8px}}
.tbl{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}} th{{font-size:12px;color:var(--muted);text-transform:uppercase}}
td.n{{text-align:right;white-space:nowrap}} .ci{{display:block;font-size:11px;color:var(--muted)}} .na{{color:var(--muted);font-style:italic}}
.venns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}} figure{{margin:0}} figcaption{{font-size:13px;color:var(--muted);margin-bottom:4px}}
.vn{{font:700 15px system-ui;fill:var(--fg)}} .vl{{font:600 12px system-ui}}
.y{{color:var(--good);font-weight:700}} .x{{color:var(--bad)}} input,select{{font:inherit;padding:4px 6px}}
</style></head><body><main>
<header><h1>{title}</h1><p>{run} · {n} occurrences</p></header>
<section><h2>Two contexts</h2><div class="ctx">
<div><b>Monitoring: you don't know it happened yet.</b><p>Each service gets a place, a time and a topic, never the incident. This is what a watch desk, a risk feed or an analyst scanning a region does. Every recall figure below is this context.</p></div>
<div><b>Lookup: you already know it happened.</b><p>Each service is told the incident's name. Web search is strongest here. It is reported separately when the lookup mode is run.</p></div>
</div></section>
<section><h2>Recall: share of reference occurrences each service returned</h2><div class="tbl"><table><thead><tr><th></th>{head}</tr></thead><tbody>{top}</tbody></table></div>
<h2 style="margin-top:16px">By reference panel</h2><div class="tbl"><table><thead><tr><th>Panel</th>{head}</tr></thead><tbody>{by_panel}</tbody></table></div></section>
<section><h2>Who found what</h2><div class="venns">{venns}</div><p style="font-size:13px;color:var(--muted)">Region counts are exact; circle sizes are not to scale.</p></section>
<section><h2>Every case</h2><p><input id="q" placeholder="Filter by country, panel or text"> <select id="m"><option value="">All</option><option value="miss">Missed by GDELT Cloud</option><option value="only">Found only by GDELT Cloud</option></select></p>
<div class="tbl"><table id="t"></table></div></section>
</main><script>
const D={data}, A={aliases}, CL={cloud};
const cols=Object.keys(A), web=['web_a','web_b','web_c','web_c_shared'];
function draw(){{
 const q=document.getElementById('q').value.toLowerCase(), m=document.getElementById('m').value;
 let rows=D.filter(r=>!q||(r.country+' '+r.panel+' '+r.what).toLowerCase().includes(q));
 if(m==='miss') rows=rows.filter(r=>r[CL]==='0');
 if(m==='only') rows=rows.filter(r=>r[CL]==='1'&&r.gdelt_project!=='1'&&!web.some(w=>r[w]==='1'));
 const h='<tr><th>Case</th>'+cols.map(c=>'<th>'+A[c]+'</th>').join('')+'</tr>';
 document.getElementById('t').innerHTML=h+rows.slice(0,400).map(r=>'<tr><td><b>'+r.date+' · '+r.country+'</b><br>'+r.what.replace(/</g,'&lt;')+'<br><small>'+r.note.replace(/</g,'&lt;')+'</small></td>'+cols.map(c=>'<td>'+(r[c]==='1'?'<span class=y>✓</span>':r[c]==='0'?'<span class=x>✗</span>':'–')+'</td>').join('')+'</tr>').join('');
}}
document.getElementById('q').oninput=draw; document.getElementById('m').onchange=draw; draw();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=str(ROOT / 'results' / 'occurrences.csv'))
    ap.add_argument('--aliases', help='JSON file mapping result columns to display names')
    ap.add_argument('--out', default=str(ROOT / 'results' / 'report.html'))
    ap.add_argument('--title', default='GDELT Cloud EventBench results')
    ap.add_argument('--run', default='Run 2026.11')
    a = ap.parse_args()
    rows = canonical(list(csv.DictReader(open(a.results))))
    aliases = OrderedDict(DEFAULT_ALIASES)
    if a.aliases:
        aliases.update(json.load(open(a.aliases)))
    Path(a.out).write_text(build(rows, aliases, a.title, a.run))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
