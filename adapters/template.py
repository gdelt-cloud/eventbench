#!/usr/bin/env python3
"""Template: plug any HTTP search API into the benchmark. Copy this file, fill in the three TODOs, then:

    python bench.py check-adapter --adapter adapters/my_search.py          # one request, validated
    python bench.py web --adapter adapters/my_search.py --label my_search --limit 5 --max-usd 0.10
    python bench.py web --adapter adapters/my_search.py --label my_search --max-usd 5

The runner calls search(request) once per question. `request` follows schemas/search_request.schema.json:

    {"id": "UKR-2026-10-19", "mode": "monitor" | "topic" | "list",
     "query": "people killed in attacks, clashes or violence in Ukraine October 19-25 2026",
     "keyword_query": "Ukraine attack killed",          # short form, for services that prefer keywords
     "intent": "Find news reports of distinct lethal violent incidents ...",   # one-sentence goal
     "country": "Ukraine", "start_date": "2026-10-19", "end_date": "2026-10-25", "max_results": 10}

Return a list of results, or a dict {"results": [...], "usd": <actual cost>, "status": <HTTP status>, "error": <text>}.
Each result follows schemas/search_results.schema.json:

    {"url": "...", "title": "...", "published": "2026-10-21" (ISO or RFC 2822 date, or null), "excerpt": "up to 700 chars"}

Rules that keep the comparison fair:
- Never put the incident's name, place or the reference list into the request. Use the fields as given.
- Use the service's own date filter when it has one (start_date..end_date), and its news mode if it has one.
- Use the query style the service's own documentation recommends: "query" (a natural-language question)
  or "keyword_query" (a short keyword form). Say which in your results.
- Return what the service returned, in its order. Do not filter or re-rank.
"""
import json, os, sys, urllib.error, urllib.request

USD_PER_CALL = 0.005                                   # TODO 1: your list price per request, in US dollars
ENDPOINT = 'https://search.example.com/v1/search'      # TODO 2: your service's search endpoint
KEY_ENV = 'SEARCH_API_KEY'                             # the environment variable holding your key


def search(request: dict) -> dict:
    body = {                                           # TODO 3: map the request onto your service's parameters
        'q': request['query'],                         # or request['keyword_query']
        'from': request['start_date'],
        'to': request['end_date'],
        'limit': request.get('max_results', 10),
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ[KEY_ENV]})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, data = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'error': e.read()[:300].decode(errors='replace'), 'results': []}
    # ...and map your service's response fields back onto url / title / published / excerpt.
    results = [{'url': x.get('url'), 'title': x.get('title'), 'published': x.get('date'), 'excerpt': (x.get('snippet') or '')[:700]}
               for x in data.get('results', [])]
    return {'status': status, 'results': results}


if __name__ == '__main__':  # also usable as a command: reads one JSON request on stdin
    json.dump(search(json.load(sys.stdin)), sys.stdout)
