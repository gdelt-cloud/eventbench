# Changelog

## Documentation, 26 November 2026

- **Comparing runs** (`METHOD.md`): which numbers compare across runs and which only within one, how to add a service
  to an existing pool, and how much the pool moves when a service joins it. No figure changed.

## 2026.11.2, 25 November 2026

**Coded rows against their article.** How often a coded event row is right against the article it was coded from, for
GDELT Cloud and the GDELT Project 2.0, on one row test (`ROW_JUDGING.md`).

- **Same articles:** every row either system coded from the 149 readable articles of the accuracy audit. GDELT Cloud's
  row was right 88% of the time (131 of 149); the GDELT Project's rows 9% (23 of 259), with 31% more partly right. The
  GDELT Project coded no row from 51 of the articles.
- **Conflict rows, fully blind (new):** 100 rows from each system drawn at random from the pooled run's 40 country-weeks,
  mixed, each shown with its article and nothing to say which system coded it. GDELT Cloud 81% right (65 of 80
  readable), the GDELT Project 5% (4 of 74), with 31% more partly right.
- **Corrected:** METHOD.md said the GDELT Project's rows from the audit's articles were scored. They were judged in release
  2026.11 and never published; they are now (`results/rows_same_articles.csv`). The 2026.11.1 entry below listed a GDELT
  Project reference-list figure (29%) that the release had withdrawn; it is removed.
- **Files:** `ROW_JUDGING.md`, `judgments/rows/`, `results/rows_same_articles.csv`, `results/rows_conflict.csv`.

## 2026.11.1, 25 November 2026

**The conflict comparison, like for like.** Release 2026.11's conflict figures are withdrawn and replaced. See the
corrected entry below for what was wrong.

- **Every lethal incident found (new).** 40 country-weeks in 23 countries (`suite/pool_questions_2026_11.csv`), one
  question each: *people killed in attacks, clashes or violence in {country}, {week}*. GDELT Cloud through its API filters
  for the same thing (`bench.py monitor`: conflict Events with deaths and `CR01` homicide Events located in the country,
  conflict and crime Stories about the country); web search A, B and C at their maximum results. Every record, with the
  reference incidents, judged blind by two jurors (`juror_a`, `juror_b`; κ = 0.80-0.81 on GDELT Cloud's and web search's
  records, 0.63 on the GDELT Project's), each scored apart.
- **Headline, armed conflict** (every incident type but criminal homicide): GDELT Cloud 9.7 distinct incidents a week,
  AI web search B 3.9, A 1.2, C 0.6 (second juror 11.2, 4.2, 1.2, 0.8): 2.5×, +5.7 a week (95% interval +3.3 to +9.0),
  ahead in 27 of 40 weeks, behind in 6. GDELT Cloud's first page alone: 4.9.
- **All lethal violence:** 25.9 against 5.1 a week. Criminal homicide is most of the pool and GDELT Cloud found 82% of it,
  web search B 6%.
- **The GDELT Project 2.0, like for like** (new in the pooled run): its public exports filtered as a user would (CAMEO
  18-20 rows located in the country, in the week), one record per source article, judged against the pool. Armed
  conflict 7.6 incidents a week (second juror 10.9): level with GDELT Cloud within the noise, from 30,037 records against
  GDELT Cloud's 16,535. All lethal violence 15.5 (19.0) against GDELT Cloud's 25.9 (24.4). Its first-release reference
  figure, from a search near each incident, is withdrawn.
- **Blind audit** of 140 sampled incidents by a third model: real, lethal, in the week and not a repeat for 85% of the
  armed-conflict incidents only GDELT Cloud found, 79% of those only web search found and 63% of those only the GDELT
  Project found; 56%, 75% and 64% for criminal homicide.
- **Reference-list recall, like for like:** lethal incidents only (480; `scope` in `results/occurrences.csv`), GDELT
  Cloud's blind country-week lists under the same single review (`cloud_pages`): GDELT Cloud 32%, web
  search B 27%, A 21%, C 11%. One call each: GDELT Cloud 23%, web search B 27%.
- **Unchanged:** news recall (GDELT Cloud 93% on the first review, web search B 72%) and accuracy (86% of 149 audited
  Events right against their source).
- **Files:** `judgments/pool/` (questions, key, both jurors' verdicts, incident types, audit, wider-filter check),
  `results/pooled_*.csv`, `pool_report.py`. `JUDGE_POOL.md` adds the incident types.
- **Withdrawn from the scored tables:** `cloud_filters` and `cloud_monitor` for conflict, and web search's second-look
  estimates (`results/web_depth.csv`), which were measured on the first release's scope.

## 2026.11, corrected 25 November 2026

- **The conflict comparison is withdrawn until a like-for-like re-run.** GDELT Cloud's conflict figures (`cloud_filters`, `cloud_monitor`) came from searches built around each incident: a 150 km radius around its coordinates, a date window around its date, and candidates ranked by its place names. `cloud_monitor` adds a second look and a recheck that only GDELT Cloud received. The GDELT Project arm also searched within 100 km of each incident. The web searches were asked only the country and the week.
- **Asked the same question and reviewed the same way**, GDELT Cloud's country-week lists (conflict Stories and Events with deaths, every page) found 33% of the lethal conflict incidents and AI web search B 27% (+5 points, 95% interval −4 to +14, resampled by country). One call each: 23% against 27%.
- **The conflict cases the question describes.** The question asks for people killed; 57 UCDP events with a best estimate of zero deaths and about 65 Wikipedia items that report no death (talks, deployments, strikes on infrastructure) were scored in 2026.11 and will be scored apart.
- **The news result holds** when every service is reviewed the same way: GDELT Cloud 93% (326 of 351), AI web search B 72%.
- **Accuracy:** 86% of the 149 audited GDELT Cloud Events with a readable source were right against it.
- **Verdict files** are published for the 436 cases of rounds 1–3; the 519 v2 cases follow with the re-run.

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
