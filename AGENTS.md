# Running EventBench with a coding agent

Step-by-step instructions for an agent (or a person) adding a search service, an event list or an LLM step, and
running the suite. Everything is Python 3.10+ standard library. Work from the repository root.

## 0. Check the runner works (offline, free)

```bash
python -m unittest discover tests
```

Expect `Ran 6 tests ... OK`. The tests run the mock adapter end to end: web, eventlist, LLM extraction against a
local stub, packets and score.

## 1. Build the cases

```bash
python bench.py refs
```

Writes `run/refs.json`: UCDP Candidate Events drawn by seed, the curated lists in `references/`, and USGS
earthquakes. It needs network access to the UCDP and USGS download pages, and costs nothing.

## 2. Add a search service

1. Copy `adapters/template.py` to `adapters/<name>.py`, or `adapters/template_curl.sh` for a shell command.
2. Fill in the three TODOs: price per request, endpoint, and the field mapping both ways. The contract is in
   `adapters/README.md` and `schemas/search_request.schema.json` → `schemas/search_results.schema.json`.
3. Choose the query field the service's documentation recommends: `query` (natural-language) or
   `keyword_query` (short keywords). Use the service's own date filter and news mode if it has them.
4. Put the key in an environment variable. Never hard-code it, and never commit it.

Fair-comparison rules (also in `adapters/README.md`): never add the incident's name, place or the reference list
to a request; return the service's results unchanged and in order.

## 3. Check the adapter (one request)

```bash
python bench.py check-adapter --adapter adapters/<name>.py
```

Expected output is JSON with `"status": 200`, a result count, the first two results, and `"problems": []`. Each
problem names a fix:

| Problem | Fix |
|---|---|
| `no results with a url` | Wrong response mapping, or the request is malformed |
| `results have no parseable published date` | Map the service's date field; ISO or RFC 2822 both work |
| `published outside the window` | The date filter is not applied; check parameter names |
| `no excerpts` | Map the snippet or text field; reviewers judge from title and excerpt |

## 4. Capped trial, then the full run

```bash
python bench.py web --adapter adapters/<name>.py --label <name> --limit 5 --max-usd 0.10
```

```bash
python bench.py web --adapter adapters/<name>.py --label <name> --max-usd 5
```

- `--label` becomes the column in the results. Use lowercase letters, digits and `_`.
- Every call is reserved in `run/spend_web_<label>.sqlite` before it is sent, and the run stops before it would
  pass `--max-usd`. If the adapter reports `"usd"`, the real cost replaces the reservation.
- Output: one file per question, `run/web/<question_id>-<label>.json`, holding the request, results, status,
  cost and latency. A rerun skips files that exist.
- A full run of the 2026.11 suite is about 300 questions per service in rounds 1–3, and 630 with suite v2.

## 5. Optional: web search + LLM

This is the pipeline a developer builds to imitate an event feed. Each results page goes to an LLM, which returns
de-duplicated records with date, place, parties, deaths and source URLs. It cannot find anything the search did
not return. Any endpoint that speaks the chat-completions protocol (default) or the responses protocol works. Use
a small, low-cost LLM; any model works.

```bash
export LLM_API_KEY=...
```

```bash
python bench.py extract --label <name> --base-url <endpoint base URL> --model <model> --usd-in <$/M input> --usd-out <$/M output> --max-usd 1
```

Output: `run/extract/<question_id>-<label>.json`, with `records` in the shape of
`schemas/extracted_records.schema.json`.

## 6. Optional: compare an event list (another dataset, your own log)

Export it as CSV or JSONL with the columns of `templates/event_list.csv`, which are documented in
`schemas/event_list.schema.json`. Only `id`, `date` and `country` are required. Coordinates, admin1, locality and
description make matching better.

```bash
python bench.py eventlist --file my_events.csv --label my_list
```

Rows are matched to cases the way the GDELT Project arm is matched:
- **Coordinates:** within 100 km and from −1 to +3 days for conflict, or −2 to +5 days otherwise.
- **No coordinates:** the same country, plus a place name (conflict) or shared words (non-conflict).

Output: `run/eventlists/<label>.json`. The rows then enter the blind packets beside every other source. Check the
licence of the list first: some datasets forbid competitive evaluation.

## 7. Judge, score, report

```bash
python bench.py packets
```

This writes `run/packets/<ISO>.md`, one per country, plus `run/packet_key.json`. **Never show the key to a
reviewer.** Reviewers follow `JUDGING.md` and write `run/judgments/<ISO>.json` in this form:

```json
{"<uid>": {"S": ["R00012"], "A": [], "note": "one short line on a hard call"}}
```

```bash
python bench.py score
```

```bash
python report.py --results run/occurrences.csv
```

- `score` prints recall per panel and source, and writes `run/scores.json` and `run/occurrences.csv` (one 0/1
  column per source: `cloud_filters`, `gdelt_project`, `<label>`, `<label>_llm`).
- `report.py` turns that CSV into a self-contained HTML report.

## Checklist before you publish a result

- [ ] `check-adapter` shows no problems.
- [ ] You state the depth (`--max-results`), the query field (`query` or `keyword_query`) and the price.
- [ ] The run finished, or you report the share of questions answered (`grep -L '"status": 200' run/web/*-<label>.json`).
- [ ] Reviewers never saw `packet_key.json` or the labels.
- [ ] You do not publish raw responses unless the service's terms allow it. `run/` is gitignored for this reason.
