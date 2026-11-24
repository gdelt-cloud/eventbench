# Adapters: plug in any search service

An adapter turns one benchmark question into one request to a search service, and the service's answer
back into a list of results. Write one and the benchmark runs against any service you choose.

## The contract

The runner sends one **request** per question
([schemas/search_request.schema.json](../schemas/search_request.schema.json)):

```json
{"id": "UKR-2026-10-19", "mode": "monitor",
 "query": "people killed in attacks, clashes or violence in Ukraine October 19-25 2026",
 "keyword_query": "Ukraine attack killed",
 "intent": "Find news reports of distinct lethal violent incidents that occurred in Ukraine between 2026-10-19 and 2026-10-25. Prefer reports that name the place and date.",
 "country": "Ukraine", "start_date": "2026-10-19", "end_date": "2026-10-25", "max_results": 10}
```

The adapter returns **results** ([schemas/search_results.schema.json](../schemas/search_results.schema.json)):
either a list, or a dict that also reports the real cost and status.

```json
{"results": [{"url": "https://…", "title": "…", "published": "2026-10-21", "excerpt": "up to 700 characters"}],
 "usd": 0.005, "status": 200}
```

`published` may be an ISO date or timestamp or an RFC 2822 date; anything else is treated as unknown.

## Two ways to write one

| Kind | How the runner calls it | Start from |
|---|---|---|
| Python | `--adapter adapters/my_search.py`. The file exposes `search(request)` and, optionally, `USD_PER_CALL` | [template.py](template.py) |
| Any command | `--adapter "bash adapters/my_search.sh"`. Reads one JSON request on stdin, writes JSON on stdout | [template_curl.sh](template_curl.sh) |

[mock.py](mock.py) works both ways and costs nothing. Use it for a dry run.

## News databases (article search, or clusters of articles)

A news database is not a search engine: it takes structured filters and lists everything that matches. Start from
[template_news_api.py](template_news_api.py).

- **Ask the published questions.** `--questions suite/questions_2026_11.csv` sends the exact 582 questions the
  2026.11 round asked, each listing the occurrences it covers (`covers`), so your service is judged on what every
  other service was asked. `--ids` picks a subset for a pilot; `--start-after <date>` keeps only questions your plan
  can search (some plans reach only recent data; say so beside the results).
- **Use its filters.** Each request carries `country`, `start_date`, `end_date` and `keywords` (the keyword form
  without the country). Map them onto the service's country, location or concept filter, its date filter and its
  keyword filter.
- **Take a full call.** Set `--max-results` to what one call returns (often 50 or 100). Paging further is allowed;
  every call is counted and priced.
- **Optional fields.** `occurred` (the date the service gives the occurrence itself, for clusters), `place`,
  `first_seen` (when the service first stored the record, for timeliness), and `units` (cost in the service's own
  billing units). A record with no web URL can carry any stable id such as `urn:event:<id>`; reviewers never see it.
- Packets built from `--questions` runs share each question's records once, above the occurrences it covers.

## Fair-comparison rules

- Never add the incident's name, place or the reference list to the request. Use the fields as given.
- Use the service's own date filter and news mode when it has them.
- Use the query style the service's documentation recommends: `query` (natural-language) or `keyword_query`
  (short keywords). Record which.
- Return the service's results unchanged, in its order. No filtering, no re-ranking.
- State the depth (`--max-results`) and the price (`--usd-per-call`) you used.

## Check it, then run it

```bash
python bench.py check-adapter --adapter adapters/my_search.py
```

```bash
python bench.py web --adapter adapters/my_search.py --label my_search --limit 5 --max-usd 0.10
```

```bash
python bench.py web --adapter adapters/my_search.py --label my_search --max-usd 5
```

`check-adapter` sends one sample question and lists problems: no results, undated results, results
outside the window, missing excerpts. `--label` becomes the column name in `run/occurrences.csv`.
