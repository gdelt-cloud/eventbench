"""EventBench pooled-truth report: every table the results page shows for the conflict monitoring task.

    python3 pool_report.py                      # reads judgments/pool, writes results/pooled_*.csv
    python3 pool_report.py --pool DIR --out DIR # any pool laid out the same way (bench.py pool + pool-judge)

The pool for one question is every distinct lethal incident any juror label names: what every service returned plus
the reference incidents the question covers (JUDGE_POOL.md). A service delivers an incident when one of its
records carries that label. Jurors are scored separately, never merged. Standard library only.

Inputs (judgments/pool/):
  questions.json        id -> country, scope, dates
  key.json              "<question>:<record>" -> source (cloud_event, cloud_story, gdelt_project, web_a, web_b, web_c, reference),
                        its id or URL, and for GDELT Cloud records the route and position in the API's answer
  verdicts/<juror>/     one JSON per question: record -> {on_topic, incident}
  incident_types.csv    juror, question, incident, type (JUDGE_POOL.md, "Incident type")
  audit.csv             the blind audit of a sample of pooled incidents (optional)
  extra_filters.csv     wider GDELT Cloud filters, judged against the pool (optional)
"""
from __future__ import annotations

import argparse, collections, csv, json, math, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ('web_a', 'web_b', 'web_c')
FIRST_PAGE = 100  # one API call returns up to 100 records per list
SERVICES = {
    'cloud': ('GDELT Cloud, every record', lambda k: k['src'].startswith('cloud')),
    'cloud_first_page': ('GDELT Cloud, first page of each list', lambda k: k['src'].startswith('cloud') and (k.get('rank') or 10**9) <= FIRST_PAGE),
    'cloud_deaths_flag': ('GDELT Cloud, Events and Stories flagged with deaths', lambda k: k['src'] == 'cloud_event' or (k['src'] == 'cloud_story' and k.get('deaths_flag'))),
    'cloud_events': ('GDELT Cloud, Events only', lambda k: k['src'] == 'cloud_event'),
    'gdelt_project': ('GDELT Project 2.0, CAMEO 18-20 rows located in the country', lambda k: k['src'] == 'gdelt_project'),
    'web_a': ('Web search A', lambda k: k['src'] == 'web_a'),
    'web_b': ('Web search B', lambda k: k['src'] == 'web_b'),
    'web_c': ('Web search C', lambda k: k['src'] == 'web_c'),
    'any_web': ('Any web search', lambda k: k['src'] in WEB),
}
SCOPES = {'all': lambda t: True, 'armed_conflict': lambda t: t != 'criminal_homicide', 'criminal_homicide': lambda t: t == 'criminal_homicide'}
TYPE_ORDER = ['battle', 'remote_violence', 'attack_on_civilians', 'security_force_killing', 'mob_or_riot', 'criminal_homicide', 'other']
norm = lambda s: ' '.join((s or '').lower().split())


def place(m):
    """A question's place as a table row: its country, or its wider scope in short (no explanatory clause)."""
    scope = (m.get('scope') or m['country']).split(', which')[0].replace('including the ', '')
    return scope if scope != m['country'] else m['country']


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 4), round((c + h) / d, 4)


def boot(diffs, n=10000, seed=20261125):
    """Paired bootstrap over questions: 95% interval of the mean difference."""
    rnd = random.Random(seed); m = len(diffs)
    xs = sorted(sum(rnd.choice(diffs) for _ in range(m)) / m for _ in range(n))
    return round(xs[int(0.025 * n)], 2), round(xs[int(0.975 * n)], 2)


def write(path, rows):
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8') as fo:
        w = csv.DictWriter(fo, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pool', default=str(ROOT / 'judgments' / 'pool')); ap.add_argument('--out', default=str(ROOT / 'results'))
    a = ap.parse_args(); pool_dir, out = Path(a.pool), Path(a.out)
    meta = json.loads((pool_dir / 'questions.json').read_text())
    key = json.loads((pool_dir / 'key.json').read_text())
    by_q = collections.defaultdict(dict)
    for k, v in key.items():
        by_q[v['q']][k.split(':', 1)[1]] = v
    types = {}
    if (pool_dir / 'incident_types.csv').exists():
        for r in csv.DictReader(open(pool_dir / 'incident_types.csv', encoding='utf-8')):
            types[(r['juror'], r['question'], norm(r['incident']))] = r['type']
    occ = {}
    if (ROOT / 'suite' / 'occurrences_v2.csv').exists():
        occ = {r['uid']: r for r in csv.DictReader(open(ROOT / 'suite' / 'occurrences_v2.csv', encoding='utf-8'))}
    panel = lambda uid: next((p for p in ('UCDP', 'SATP', 'Indepaz') if (occ.get(uid, {}).get('panel') or '').startswith(p)), 'other')
    jurors = sorted(d.name for d in (pool_dir / 'verdicts').iterdir() if d.is_dir())
    summary, compare, by_type, by_country, by_panel, by_question, overlap, labels_of = [], [], [], [], [], [], [], {}
    for j in jurors:
        V = {q: json.loads((pool_dir / 'verdicts' / j / f'{q}.json').read_text()) for q in meta if (pool_dir / 'verdicts' / j / f'{q}.json').exists()}
        qs = [q for q in meta if q in V]
        per_q = {s: [] for s in SCOPES}
        ov = {s: collections.Counter() for s in SCOPES}
        agg = {s: collections.defaultdict(collections.Counter) for s in SCOPES}
        t_agg = collections.defaultdict(collections.Counter); c_agg = collections.defaultdict(collections.Counter); p_agg = collections.defaultdict(collections.Counter)
        for q in qs:
            recs = by_q[q]
            lab = {r: norm(x.get('incident')) for r, x in V[q].items() if x.get('on_topic') == 'yes' and x.get('incident')}
            labels_of[(j, q)] = lab
            typ = lambda l: types.get((j, q, l), 'other')
            for scope, keep in SCOPES.items():
                sl = {r: l for r, l in lab.items() if keep(typ(l))}
                pool = set(sl.values()); refs = {sl[r] for r, k in recs.items() if k['src'] == 'reference' and r in sl}
                row = {'pool': len(pool)}
                for s, (_, test) in SERVICES.items():
                    ids = [r for r, k in recs.items() if test(k)]
                    got = {sl[r] for r in ids if r in sl}
                    row[s] = len(got)
                    agg[scope][s].update(delivered=len(got), refs=len(got & refs), records=len(ids), on_topic=sum(r in sl for r in ids))
                agg[scope]['_'].update(pool=len(pool), refs=len(refs))
                cl = {sl[r] for r, k in recs.items() if k['src'].startswith('cloud') and r in sl}; wb = {sl[r] for r, k in recs.items() if k['src'] in WEB and r in sl}
                gp = {sl[r] for r, k in recs.items() if k['src'] == 'gdelt_project' and r in sl}
                ov[scope].update(pool=len(pool), cloud_only=len(cl - wb - gp), cloud_and_other=len(cl & (wb | gp)), gdelt_only=len(gp - cl - wb),
                                 web_only=len(wb - cl - gp), gdelt_and_web=len((gp & wb) - cl), references_only=len(refs - cl - wb - gp))
                per_q[scope].append(row)
                if scope == 'all':
                    by_question.append({'juror': j, 'question': q, 'country': meta[q]['country'], 'pool': len(pool), **{s: row[s] for s in SERVICES}})
            pool_all = set(lab.values())
            got_all = {s: {lab[r] for r, k in recs.items() if t(k) and r in lab} for s, (_, t) in SERVICES.items()}
            for l in pool_all:
                t = typ(l); t_agg[t]['pool'] += 1
                for s in SERVICES: t_agg[t][s] += l in got_all[s]
            c = c_agg[place(meta[q])]; c['weeks'] += 1; c['pool'] += len(pool_all)
            for s in SERVICES: c[s] += len(got_all[s])
            for r, k in recs.items():
                if k['src'] != 'reference': continue
                p = p_agg[panel(k['id'])]; p['references'] += 1
                if r in lab:
                    p['judged_lethal'] += 1
                    for s in SERVICES: p[s] += lab[r] in got_all[s]
        nq = len(qs)
        for scope in SCOPES:
            pool_n = agg[scope]['_']['pool']; refs_n = agg[scope]['_']['refs']
            for s, (name, _) in SERVICES.items():
                x = agg[scope][s]; lo, hi = wilson(x['on_topic'], x['records'])
                summary.append({'juror': j, 'scope': scope, 'service': s, 'description': name, 'questions': nq, 'pool': pool_n,
                                'incidents': x['delivered'], 'per_question': round(x['delivered'] / nq, 2), 'share_of_pool': round(x['delivered'] / pool_n, 4) if pool_n else '',
                                'reference_incidents': refs_n, 'reference_incidents_found': x['refs'], 'records': x['records'], 'records_on_topic': x['on_topic'],
                                'on_topic_share': round(x['on_topic'] / x['records'], 4) if x['records'] else '', 'on_topic_lo': lo, 'on_topic_hi': hi})
            for s in ('cloud', 'cloud_first_page', 'cloud_deaths_flag', 'cloud_events'):
                for w in ('web_b', 'any_web', 'gdelt_project'):
                    d = [r[s] - r[w] for r in per_q[scope]]; lo, hi = boot(d)
                    tot_s = sum(r[s] for r in per_q[scope]); tot_w = sum(r[w] for r in per_q[scope])
                    compare.append({'juror': j, 'scope': scope, 'service': s, 'versus': w, 'per_question': round(tot_s / nq, 2), 'versus_per_question': round(tot_w / nq, 2),
                                    'ratio': round(tot_s / tot_w, 2) if tot_w else '', 'mean_difference': round(sum(d) / nq, 2), 'ci_lo': lo, 'ci_hi': hi,
                                    'questions_ahead': sum(x > 0 for x in d), 'questions_tied': sum(x == 0 for x in d), 'questions_behind': sum(x < 0 for x in d)})
        for scope in SCOPES:
            overlap.append({'juror': j, 'scope': scope, **{k: ov[scope][k] for k in ('pool', 'cloud_only', 'cloud_and_other', 'gdelt_only', 'gdelt_and_web', 'web_only', 'references_only')}})
        for t in sorted(t_agg, key=lambda t: TYPE_ORDER.index(t) if t in TYPE_ORDER else 99):
            by_type.append({'juror': j, 'type': t, 'pool': t_agg[t]['pool'], **{s: t_agg[t][s] for s in SERVICES}})
        for cn, c in sorted(c_agg.items(), key=lambda x: (-x[1]['pool'], x[0])):
            by_country.append({'juror': j, 'country': cn, 'questions': c['weeks'], 'pool': c['pool'], **{s: c[s] for s in SERVICES}})
        for pn, p in sorted(p_agg.items()):
            by_panel.append({'juror': j, 'panel': pn, 'references': p['references'], 'judged_lethal': p['judged_lethal'], **{s: p[s] for s in SERVICES}})
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (('pooled_summary.csv', summary), ('pooled_compare.csv', compare), ('pooled_by_type.csv', by_type), ('pooled_by_country.csv', by_country),
                       ('pooled_by_panel.csv', by_panel), ('pooled_by_question.csv', by_question), ('pooled_overlap.csv', overlap)):
        write(out / name, rows)
    # Agreement between the first two jurors, record by record (on topic or not).
    if len(jurors) >= 2:
        # Agreement on topic or not, record by record: over every record, then by source (GDELT Project records carry
        # coded rows and a URL but no text, so they are the hardest to judge and are reported apart).
        pairs = collections.defaultdict(lambda: ([], []))
        group = lambda s: 'gdelt_project' if s == 'gdelt_project' else 'cloud' if s.startswith('cloud') else 'web' if s in WEB else 'reference'
        for q in meta:
            fa, fb = pool_dir / 'verdicts' / jurors[0] / f'{q}.json', pool_dir / 'verdicts' / jurors[1] / f'{q}.json'
            if fa.exists() and fb.exists():
                va, vb = json.loads(fa.read_text()), json.loads(fb.read_text())
                for r in set(va) & set(vb):
                    x, y = va[r].get('on_topic') == 'yes', vb[r].get('on_topic') == 'yes'
                    for g in ('all', group(by_q[q][r]['src'])):
                        pairs[g][0].append(x); pairs[g][1].append(y)
        rows = []
        for g in ('all', 'cloud', 'web', 'gdelt_project', 'reference'):
            if g not in pairs:
                continue
            a1, b1 = pairs[g]; n = len(a1); po = sum(x == y for x, y in zip(a1, b1)) / n; pa, pb = sum(a1) / n, sum(b1) / n; pe = pa * pb + (1 - pa) * (1 - pb)
            rows.append({'juror_1': jurors[0], 'juror_2': jurors[1], 'records_from': g, 'records': n, 'agreement': round(po, 4), 'kappa': round((po - pe) / (1 - pe), 3) if pe < 1 else ''})
        write(out / 'pooled_agreement.csv', rows)
    if (pool_dir / 'audit.csv').exists():
        rows = list(csv.DictReader(open(pool_dir / 'audit.csv', encoding='utf-8'))); agg = collections.defaultdict(collections.Counter)
        for r in rows:
            ok = r['real'] == 'yes' and not r['repeats']
            for scope in ('all', 'criminal_homicide' if r['type'] == 'criminal_homicide' else 'armed_conflict'):
                agg[(r['found_by'], scope)].update(checked=1, real_and_distinct=ok)
        write(out / 'pooled_audit.csv', [{'found_by': f, 'scope': s, 'checked': c['checked'], 'real_and_distinct': c['real_and_distinct'],
                                          'share': round(c['real_and_distinct'] / c['checked'], 4), 'lo': wilson(c['real_and_distinct'], c['checked'])[0],
                                          'hi': wilson(c['real_and_distinct'], c['checked'])[1]} for (f, s), c in sorted(agg.items())])
    if (pool_dir / 'extra_filters.csv').exists():
        rows = list(csv.DictReader(open(pool_dir / 'extra_filters.csv', encoding='utf-8'))); agg = collections.defaultdict(collections.Counter); new = collections.defaultdict(set)
        ja = jurors[0]
        for r in rows:
            agg[r['query']]['events'] += 1
            if r['on_topic'] != 'yes': continue
            agg[r['query']]['lethal'] += 1
            lab = labels_of.get((ja, r['question']), {})
            cloud_labels = {l for rid, l in lab.items() if by_q[r['question']][rid]['src'].startswith('cloud')}
            inc = norm(r['same_as']) or ('new:' + norm(r['new_incident']))
            if inc.startswith('new:') or inc not in cloud_labels: new[r['query']].add((r['question'], inc))
        write(out / 'pooled_extra_filters.csv', [{'query': q, 'events': c['events'], 'lethal': c['lethal'], 'incidents_new_to_cloud': len(new[q])} for q, c in agg.items()])
    print(f'wrote {out}: {len(jurors)} jurors, {len(meta)} questions')


if __name__ == '__main__':
    main()
