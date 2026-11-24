#!/usr/bin/env python3
"""Template: plug a NEWS DATABASE API (article search, or clusters of articles about one event) into the benchmark.
Copy this file, fill in the TODOs, then:

    python bench.py check-adapter --adapter adapters/my_news.py
    python bench.py web --questions suite/questions_2026_11.csv --adapter adapters/my_news.py --label my_news \
        --max-results 100 --ids my_pilot.txt --max-usd 1          # a pilot on chosen question ids first
    python bench.py web --questions suite/questions_2026_11.csv --adapter adapters/my_news.py --label my_news \
        --max-results 100 --max-usd 20

`suite/questions_2026_11.csv` holds the exact questions the published round asked (582: one per conflict
country-week, one per non-conflict item), so your service answers what every other service answered. If your plan
only searches recent data, add --start-after <date> and say so beside your results.

How a news database differs from a web search engine, and how to ask it fairly:
- Use the structured filters it has instead of a sentence. The request carries `country`, `start_date`, `end_date`
  and `keywords` (the keyword form without the country: ["attack", "killed"] for a conflict week, the topic words
  otherwise). Map the country onto the service's country, location or concept filter, the window onto its date
  filter, and the keywords onto its keyword filter (any of them, unless its guidance says otherwise).
- A database lists, so take what one call returns (often 50 or 100 records) and set --max-results to that. Paging
  further is allowed: count every call and report it.
- Clusters (one record per event) are a result each. Give a cluster's own date as `occurred` and its place as
  `place`. If it has no web URL, use any stable identifier (for example "urn:event:<id>"): it is kept in the key and
  never shown to reviewers.
- If records say when the service first stored them, return it as `first_seen` (ISO timestamp). It feeds the
  timeliness analysis; `published` stays the publisher's date.
- If the service bills in its own units (tokens, credits), return them as `units` beside `usd`.
- Never put the incident's name, place or the reference list into a request. Return results unchanged, in order.
"""
import json, os, sys, urllib.error, urllib.request

USD_PER_CALL = 0.01                                       # TODO 1: list price per call in US dollars
ENDPOINT = 'https://news.example.com/v1/search'           # TODO 2: the article or cluster search endpoint
KEY_ENV = 'NEWS_API_KEY'


def search(request: dict) -> dict:
    body = {                                              # TODO 3: map the request onto the service's filters
        'country': request['country'],                    # often a code or an entity id: look it up once and cache it
        'keywords': request['keywords'], 'keywords_operator': 'or',
        'from': request['start_date'], 'to': request['end_date'],
        'limit': request.get('max_results', 100), 'deduplicate': True,
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ[KEY_ENV]})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, data = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'error': e.read()[:300].decode(errors='replace'), 'results': []}
    results = [{                                          # TODO 4: map the response back
        'url': x.get('url') or f"urn:event:{x.get('id')}",
        'title': x.get('title'),
        'published': x.get('published_at'),               # the publisher's date
        'excerpt': (x.get('summary') or x.get('body') or '')[:700],
        'occurred': x.get('event_date'),                  # optional: clusters, or records dated to the occurrence
        'place': x.get('location'),                       # optional
        'first_seen': x.get('ingested_at'),               # optional: when the service first stored it
    } for x in data.get('results', [])]
    return {'status': status, 'results': results, 'usd': USD_PER_CALL, 'units': data.get('cost'), 'total': data.get('total')}


if __name__ == '__main__':  # also usable as a command: reads one JSON request on stdin
    json.dump(search(json.load(sys.stdin)), sys.stdout)
