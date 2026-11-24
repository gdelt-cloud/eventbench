"""Offline end-to-end test of the pluggable runner: no key, no network, no cost.

    python -m unittest discover tests
"""
import csv, http.server, json, os, sqlite3, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = [  # two conflict cases in two different weeks -> two monitor questions
    {'uid': 'T001', 'source': 'Test panel', 'family': 'conflict', 'iso': 'MLI', 'country': 'Mali', 'date': '2026-10-07', 'lat': '14.9', 'lon': '-1.6',
     'place': 'Example town (Mopti; Douentza)', 'place_terms': 'Example town Mopti Douentza', 'what': 'Side A vs Side B; deaths 3', 'deaths': 3},
    {'uid': 'T002', 'source': 'Test panel', 'family': 'conflict', 'iso': 'MLI', 'country': 'Mali', 'date': '2026-10-15', 'lat': '12.6', 'lon': '-8.0',
     'place': 'Other town (Koulikoro; Kati)', 'place_terms': 'Other town Koulikoro Kati', 'what': 'Side C vs civilians; deaths 2', 'deaths': 2},
]


def bench(run_dir, *args, env=None):
    e = dict(os.environ, BENCH_RUN_DIR=str(run_dir), **(env or {}))
    return subprocess.run([sys.executable, str(ROOT / 'bench.py'), *args], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.run = Path(self.tmp.name)
        (self.run / 'refs.json').write_text(json.dumps(REFS))

    def tearDown(self):
        self.tmp.cleanup()

    def web_files(self, label):
        return sorted((self.run / 'web').glob(f'*-{label}.json'))

    def test_module_adapter_runs_two_questions(self):
        p = bench(self.run, 'web', '--adapter', 'adapters/mock.py', '--label', 'mock', '--max-usd', '0')
        self.assertEqual(p.returncode, 0, p.stderr)
        files = self.web_files('mock'); self.assertEqual(len(files), 2)
        for f in files:
            o = json.loads(f.read_text())
            self.assertEqual(o['status'], 200); self.assertEqual(len(o['results']), 3)
            req = o['request']
            for k in ('query', 'keyword_query', 'intent', 'start_date', 'end_date', 'mode', 'max_results'): self.assertIn(k, req)
            self.assertEqual(req['keyword_query'], 'Mali attack killed')
            for r in o['results']:
                self.assertTrue(req['start_date'] <= r['published'] <= req['end_date'])

    def test_command_adapter_and_ledger(self):
        p = bench(self.run, 'web', '--adapter', f'{sys.executable} adapters/mock.py', '--label', 'mockcmd', '--usd-per-call', '0.001', '--max-usd', '0.01')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(self.web_files('mockcmd')), 2)
        # the mock reports usd 0.0, and a reported cost overrides the reserved price
        spent = sqlite3.connect(self.run / 'spend_web_mockcmd.sqlite').execute('select count(*), sum(usd) from req').fetchone()
        self.assertEqual(spent, (2, 0.0))

    def test_spend_cap_stops_before_passing(self):
        bad = ROOT / 'tests' / '_priced_adapter.py'
        bad.write_text('import json,sys\nsys.path.insert(0,"adapters")\nimport mock\nUSD_PER_CALL=0.001\ndef search(r):\n    o=mock.search(r); o.pop("usd"); return o\n')
        try:
            p = bench(self.run, 'web', '--adapter', str(bad), '--label', 'priced', '--max-usd', '0.0015')
        finally:
            bad.unlink()
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn('spend cap', p.stdout)
        self.assertEqual(len(self.web_files('priced')), 1)

    def test_check_adapter(self):
        p = bench(self.run, 'check-adapter', '--adapter', 'adapters/mock.py')
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        o = json.loads(p.stdout); self.assertEqual(o['status'], 200); self.assertEqual(o['problems'], [])

    def test_eventlist_packets_and_score(self):
        self.assertEqual(bench(self.run, 'web', '--adapter', 'adapters/mock.py', '--label', 'mock', '--max-usd', '0').returncode, 0)
        lst = self.run / 'list.csv'
        with lst.open('w', newline='') as fo:
            w = csv.writer(fo); w.writerow(['id', 'date', 'country', 'admin1', 'locality', 'lat', 'lon', 'category', 'actors', 'deaths', 'source_url', 'description'])
            w.writerow(['L1', '2026-10-08', 'Mali', 'Mopti', 'Example town', '14.95', '-1.62', 'clash', 'Side A; Side B', '3', '', 'Clash near Example town'])
            w.writerow(['L2', '2026-12-01', 'Mali', '', '', '', '', '', '', '', '', 'Out of window'])
        p = bench(self.run, 'eventlist', '--file', str(lst), '--label', 'mylist'); self.assertEqual(p.returncode, 0, p.stderr)
        m = json.loads((self.run / 'eventlists' / 'mylist.json').read_text())
        self.assertEqual([r['id'] for r in m.get('T001', [])], ['L1']); self.assertNotIn('T002', m)
        p = bench(self.run, 'packets'); self.assertEqual(p.returncode, 0, p.stderr)
        key = json.loads((self.run / 'packet_key.json').read_text())
        srcs = {v['source'] for v in key.values()}; self.assertTrue({'web_mock', 'list_mylist'} <= srcs)
        packet = (self.run / 'packets' / 'MLI.md').read_text()
        for label in ('web_mock', 'list_mylist', 'mylist'):  # source labels never reach reviewers
            self.assertNotIn(label, packet)
        list_rid = next(k for k, v in key.items() if v['source'] == 'list_mylist')
        web_rid = next(k for k, v in key.items() if v['source'] == 'web_mock')
        (self.run / 'judgments').mkdir()
        (self.run / 'judgments' / 'MLI.json').write_text(json.dumps({'T001': {'S': [list_rid], 'A': []}, 'T002': {'S': [web_rid], 'A': []}}))
        p = bench(self.run, 'score'); self.assertEqual(p.returncode, 0, p.stderr)
        rows = {r['uid']: r for r in csv.DictReader((self.run / 'occurrences.csv').open())}
        self.assertEqual((rows['T001']['mylist'], rows['T001']['mock']), ('1', '0'))
        self.assertEqual((rows['T002']['mylist'], rows['T002']['mock']), ('0', '1'))

    def test_news_database_through_fixed_questions(self):
        """A news-database adapter (clusters without web URLs, articles with ingest times) asked a fixed question set:
        optional fields survive, each question's records are shared once in the packets, ids and labels stay hidden."""
        qfile = self.run / 'questions.csv'
        with qfile.open('w', newline='') as fo:
            w = csv.writer(fo); w.writerow(['id', 'mode', 'family', 'country', 'start_date', 'end_date', 'query', 'keyword_query', 'intent', 'covers'])
            for qid, s, e, cov in (('Q-MLI-w41', '2026-10-05', '2026-10-11', 'T001'), ('Q-MLI-w42', '2026-10-12', '2026-10-18', 'T002'), ('Q-OLD', '2026-09-01', '2026-09-07', 'T999')):
                w.writerow([qid, 'monitor', 'conflict', 'Mali', s, e, f'people killed in Mali {s}', 'Mali attack killed', 'Find lethal incidents.', cov])
        ad = ROOT / 'tests' / '_news_adapter.py'
        ad.write_text(
            'USD_PER_CALL = 0.01\n'
            'def search(r):\n'
            '    assert r["keywords"] == ["attack", "killed"] and "covers" not in r\n'
            '    return {"status": 200, "usd": 0.0, "units": {"tokens": 1}, "total": 2, "results": [\n'
            '        {"url": "urn:event:c-" + r["id"], "title": "Clash near Example town", "published": r["start_date"], "occurred": r["start_date"],\n'
            '         "place": "Example town, Mali", "excerpt": "Three killed."},\n'
            '        {"url": "https://news.example/" + r["id"], "title": "Attack report", "published": r["start_date"] + "T09:00:00Z",\n'
            '         "first_seen": r["start_date"] + "T09:12:00Z", "excerpt": "Gunmen attacked."}]}\n')
        try:
            p = bench(self.run, 'web', '--questions', str(qfile), '--start-after', '2026-10-01', '--adapter', str(ad), '--label', 'mynews', '--max-usd', '0.05')
        finally:
            ad.unlink()
        self.assertEqual(p.returncode, 0, p.stderr)
        files = self.web_files('mynews'); self.assertEqual([f.name for f in files], ['Q-MLI-w41-mynews.json', 'Q-MLI-w42-mynews.json'])
        o = json.loads(files[0].read_text())
        self.assertEqual(o['covers'], ['T001']); self.assertEqual(o['units'], {'tokens': 1}); self.assertEqual(o['total'], 2)
        self.assertEqual((o['results'][0]['occurred'], o['results'][0]['place']), ('2026-10-05', 'Example town, Mali'))
        self.assertEqual(o['results'][1]['first_seen'], '2026-10-05T09:12:00Z')
        self.assertEqual(bench(self.run, 'packets').returncode, 0)
        packet = (self.run / 'packets' / 'Q00.md').read_text()
        self.assertEqual(packet.count('## QUESTION Q-MLI-w41'), 1); self.assertIn('### OCCURRENCE T001', packet)
        for hidden in ('mynews', 'urn:event'): self.assertNotIn(hidden, packet)
        key = json.loads((self.run / 'packet_key.json').read_text())
        cl = next(k for k, v in key.items() if v['ref'] == 'urn:event:c-Q-MLI-w41')
        ar = next(k for k, v in key.items() if v['ref'] == 'https://news.example/Q-MLI-w42')
        self.assertEqual((key[cl]['question'], key[cl]['rank']), ('Q-MLI-w41', 1))
        (self.run / 'judgments').mkdir()
        (self.run / 'judgments' / 'Q00.json').write_text(json.dumps({'T001': {'S': [cl], 'A': []}, 'T002': {'S': [ar], 'A': []}}))
        self.assertEqual(bench(self.run, 'score').returncode, 0)
        rows = {r['uid']: r for r in csv.DictReader((self.run / 'occurrences.csv').open())}
        self.assertEqual((rows['T001']['mynews'], rows['T002']['mynews']), ('1', '1'))

    def test_extract_through_any_chat_endpoint(self):
        self.assertEqual(bench(self.run, 'web', '--adapter', 'adapters/mock.py', '--label', 'mock', '--max-usd', '0').returncode, 0)
        seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((self.path, body['model']))
                out = {'choices': [{'message': {'content': json.dumps({'records': [{'date': '2026-10-07', 'place': 'Example town', 'actors': 'Side A', 'what': 'Clash',
                                                                                        'deaths': 3, 'source_urls': ['https://example.org/mock/x/0']}]})}}],
                       'usage': {'prompt_tokens': 1000, 'completion_tokens': 100}}
                b = json.dumps(out).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            p = bench(self.run, 'extract', '--label', 'mock', '--base-url', f'http://127.0.0.1:{srv.server_port}/v1', '--model', 'any-model',
                      '--usd-in', '0.1', '--usd-out', '0.5', '--max-usd', '0.01', env={'LLM_API_KEY': 'test'})
        finally:
            srv.shutdown(); srv.server_close()
        self.assertEqual(p.returncode, 0, p.stderr)
        files = sorted((self.run / 'extract').glob('*-mock.json')); self.assertEqual(len(files), 2)
        self.assertEqual(json.loads(files[0].read_text())['records'][0]['deaths'], 3)
        self.assertEqual(seen[0], ('/v1/chat/completions', 'any-model'))


if __name__ == '__main__':
    unittest.main()
