# Changelog

## 2026.11

**Scored results.**
- 955 occurrences: 604 conflict incidents in 59 countries (UCDP Candidate Events, Indepaz, SATP and Wikipedia's armed conflicts and attacks) and 351 non-conflict items (Wikipedia Current Events, election, rate-change, WHO and GDACS lists).
- 40 country × category × week listing cells.
- Relevance and yield per question on 40 random conflict country-weeks, with every returned record judged blind.
- Recall at an equal number of calls on all 604 conflict incidents, and calls, time and fees per question.
- Services: GDELT Cloud, GDELT Project 2.0, AI web search A, B and C, and web search + LLM for A, B and C. C was asked in the keyword style its documentation recommends on every question; its run with the long question (the first 120 conflict incidents) is kept as a disclosed variant.
- GDELT Cloud is reported two ways: place filters alone (`cloud_filters`), and with a second look at the same calls' candidates and a recheck of incidents only web search found (`cloud_monitor`).
- GDELT Project rows were re-judged with each source article's headline; a row counts when either reading matches.
- Wikipedia items whose country had been misread (for example from a news agency's dateline) were corrected and asked again.
- 78 USGS earthquakes are in the suite, judged for GDELT Cloud only and not in the scored tables.

**Suite v2.** `suite/occurrences_v2.csv` adds 520 occurrences to the 436 of rounds 1–3: UCDP top-ups to 15 per country where UCDP has that many, and every in-scope Wikipedia Current Events item with a country, conflict and non-conflict, Sep 20 – Nov 20.

**Runner: any service, any event list (provider-neutral).**
- `bench.py web --adapter` takes any search service: a Python file exposing `search(request)` or any command that reads one JSON request on stdin and writes JSON results on stdout. `--label` names the result column.
- `bench.py check-adapter` sends one sample question and lists problems; `bench.py eventlist` matches rows of any event list (CSV or JSONL) to the cases.
- `bench.py extract` works with any LLM endpoint that speaks the chat-completions or responses protocol.
- `schemas/` (search request, search results, extracted records, event-list row), `adapters/` (Python and shell templates, an offline mock), `templates/event_list.csv`, `AGENTS.md`, and an offline end-to-end test in `tests/`.
- Every question now also carries a short keyword form (`keyword_query`); weeks that cross a month boundary are written in full ("October 26-November 1").
- Web search C re-run in the keyword style its documentation recommends; the long-question run is kept as a disclosed variant.
- `suite/questions_2026_11.csv` holds the 582 questions the round asked, each with the occurrences it covers. `bench.py web --questions` asks exactly those; `--ids` and `--start-after` run a subset.
- News databases (article search or article clusters) plug in through `adapters/template_news_api.py`. Results may carry `occurred`, `place`, `first_seen` and `units`; packets built from a question file show each question's records once, above the occurrences it covers.
