#!/usr/bin/env python3
"""Mock search adapter: deterministic, offline, free. Use it for a dry run and in tests.

As a module:   python bench.py web --adapter adapters/mock.py --label mock --max-usd 0
As a command:  python bench.py web --adapter "python3 adapters/mock.py" --label mock --max-usd 0

It returns three fake results per request, dated inside the requested window, so every later step
(extract, packets, score) can be exercised without a key. The results are not real news.
"""
import datetime as dt, hashlib, json, sys

USD_PER_CALL = 0.0

def search(request: dict) -> dict:
    start = dt.date.fromisoformat(request['start_date'])
    n = min(int(request.get('max_results') or 10), 3)
    h = hashlib.sha1(request['id'].encode()).hexdigest()[:8]
    results = [{'url': f'https://example.org/mock/{h}/{i}', 'title': f"[MOCK] {request['country']}: example result {i + 1} for {request['mode']} question",
                'published': (start + dt.timedelta(days=i)).isoformat(),
                'excerpt': f"[MOCK] Placeholder text for the question \"{request['query']}\". Not a real report."} for i in range(n)]
    return {'results': results, 'usd': 0.0}

if __name__ == '__main__':
    json.dump(search(json.load(sys.stdin)), sys.stdout)
