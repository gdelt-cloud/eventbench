# GDELT Cloud EventBench

When something happens in the world, does a data service give you a record of it? Is the record right? What does it tell you?

EventBench answers those questions for five kinds of source:
- GDELT Cloud
- the raw GDELT Project 2.0 event stream
- three well-known AI web search APIs, labelled A, B and C
- web search + LLM, where an LLM turns search results into records (explained below)
- and any search service or event list you plug in yourself ([AGENTS.md](AGENTS.md))

Every occurrence comes from a reference list that none of these services produced. Release 2026.11 covers:
- 955 occurrences: 604 conflict incidents in 59 countries and 351 non-conflict items
- 40 country × category × week listing cells
- 40 random conflict country-weeks in which every returned record was judged for relevance

Everything needed to rerun it is in this repository.

## Two ways to ask

| | Monitoring | Lookup |
|---|---|---|
| You know it happened? | No | Yes |
| You ask by | Place, time and topic: *"people killed in attacks in Mali this week"* | Name: *"the Boulkessi base attack on 7 October"* |
| Who works this way | A watch desk, a risk feed, an analyst scanning a region | A reporter or analyst following up a known event |
| In this release | **Every recall figure** | Planned for the next release |

Web search is built for lookup: describe the item and the top result is usually it. A database is built for monitoring, because it lists everything that matches a filter. Read every number below as a monitoring number.

## Where the cases come from

Every case comes from a list that none of the tested services produced.

- **UCDP Candidate Events** (conflict, 428 incidents). The Uppsala Conflict Data Program at Uppsala University codes each event of organized violence by hand. Researchers read news, NGO and local sources, and an event can be as small as one death. The Candidate release is monthly and preliminary, about a month behind; the final dataset (GED) is annual. So UCDP is not a real-time feed. It is a careful, human-built record made after the fact, independent of every service tested here, which is what makes it a fair yardstick and a hard one.
- **Indepaz** (19 Colombian massacres) and **SATP** (36 killings in Pakistan and India): independent monitors with published definitions.
- **Wikipedia Current Events:** editor-written daily summaries. 121 armed-conflict and attack items count as conflict; 326 items on crime, politics, disasters, business, diplomacy, health and science count as non-conflict.
- **Official lists** (25 items): national elections, central-bank rate changes, WHO Disease Outbreak News and GDACS alerts.

Details and sampling: [METHOD.md](METHOD.md) and [SUITE.md](SUITE.md).

## What each service was asked

- **GDELT Cloud:** the filters its customers use, through the public API: country (either actor's country), category, dates and a radius around the place. Reviewers then took a second look at the candidates those same calls returned, and rechecked each incident only web search had found: it counts only when a monitoring call (the country in any role, all categories) returns the record. Place filters alone are reported too.
- **GDELT Project 2.0:** the public 15-minute Events export and the translation export, CAMEO root codes 18–20 (assault, fight, mass violence). Rows within 100 km of the case and from one day before to three days after it, up to 25 nearest; with no coordinates, rows in the same country whose source URL shares words with the case. Reviewers judged each row from its coded fields plus its source article's headline. Not searched: the GKG, the Mentions table, other CAMEO roots, and the GDELT DOC full-text search. Not tested on non-conflict items.
- **AI web search A, B and C:** each in the style its own documentation recommends. A and B take a natural-language question (*"people killed in attacks, clashes or violence in Mali October 5-11 2026"*). C takes a short keyword query in its news mode (*"Mali attack killed"*), because the long question returned off-topic pages; its result for the long question is kept as a disclosed variant. Each uses its own date filter, and A and B return 10 results, C 20.
- **Web search + LLM:** the pipeline a developer builds to imitate an event feed from web search. It runs the search, hands the results page to an LLM, and the LLM returns a de-duplicated list of incident records with date, place, parties, deaths and source URLs. There is one LLM call per results page. It makes results readable and countable, but it cannot find anything the search did not return.

## Results, release 2026.11

### Recall: of what happened, how much did each service return?

No question named the incident. GDELT Cloud got the filters its customers use: country, category, dates and radius. Each web search got the question a person would type.

| Service | Conflict · 604 incidents, 59 countries | Non-conflict · 351 news and official items |
|---|---:|---:|
| **GDELT Cloud** (Events or Stories) | **52%** (48–56) | **95%** (92–97) |
| GDELT Cloud, place filters only | 44% (40–48) | 93% (90–95) |
| GDELT Cloud, Events only | 30% (26–33) | 58% (53–63) |
| GDELT Project 2.0 rows | 32% (29–36) | not tested |
| AI web search A, top 10 | 18% (15–21) | 59% (54–64) |
| AI web search B, top 10 | 25% (21–28) | 72% (67–77) |
| AI web search C, top 20, keyword query | 12% (10–15) | 42% (37–47) |
| AI web search C, the long question (first 120 conflict incidents) | 2% (0–6) | not tested |
| Web search A + LLM | 17% (14–20) | 55% (50–60) |
| Web search B + LLM | 23% (19–26) | 66% (61–71) |
| Web search C + LLM | 8% (6–11) | 39% (34–45) |
| GDELT Cloud, the GDELT Project or any web search | 60% (364) | 98% (345) |
| News API A\*, article search and clusters (2 calls) | 28%\* (21–36) | 67%\* (59–74) |
| News API A\*, article search, top 100 | 21%\* (15–28) | 48%\* (40–55) |
| News API A\*, article clusters, top 50 | 18%\* (11–24) | 46%\* (38–54) |

95% Wilson intervals are in brackets.

\* News API A is a news-database API that stores articles and clusters them into events. The plan we ran on searches only the last 30 days, so it answered the 311 questions inside that window (438 occurrences: 213 conflict, 225 non-conflict), and its full-suite figure is projected by reference list. Applied to the services measured on every question, the same projection lands within 0.4–3.3 points of their real conflict figure (always below it) and 0.7–3.6 points of their non-conflict figure; we correct by the average of those errors and widen the interval by their spread. Inside the window it found 38% of conflict incidents (both calls), against GDELT Cloud's 64% and web search B's 25% on the same incidents. Details: `results/news_api_a_window.csv` and [METHOD.md](METHOD.md#news-api-a-asked-inside-its-30-day-window).

- **Conflict:** GDELT Cloud found 79 incidents that neither the GDELT Project nor any web search returned. Web search alone found 39, mostly from specialist monitors outside the news stream. 240 of 604 were found by no service.
- **Non-conflict:** the 25 official, scheduled items work like lookups: web search A and B found all 25, C 24 and GDELT Cloud 23. On Wikipedia's 326 news developments, GDELT Cloud found 309, web search B 228, A 182 and C 123.

**By reference list:**

| List | Items | GDELT Cloud | GDELT Project | Web A | Web B | Web C |
|---|---:|---:|---:|---:|---:|---:|
| UCDP Candidate Events, October | 428 | 174 | 85 | 65 | 98 | 21 |
| Indepaz massacres, Aug–Oct | 19 | 9 | 5 | 2 | 4 | 0 |
| SATP timelines, November | 36 | 16 | 10 | 1 | 1 | 3 |
| Wikipedia, armed conflicts and attacks | 121 | 113 | 95 | 42 | 45 | 50 |
| Wikipedia, non-conflict | 326 | 309 | not tested | 182 | 228 | 123 |
| Official lists | 25 | 23 | not tested | 25 | 25 | 24 |

Per-panel and per-case results are in `results/`. Worked examples are in [cases.md](cases.md).

### Listing: "every X in country Y this week"

There are 40 cells: 8 categories × 5 countries, plus Protests in 5 more countries, for Nov 9–15. GDELT Cloud returned its complete list for each cell. Each web search returned one page.

| | GDELT Cloud | AI web search A | AI web search B |
|---|---:|---:|---:|
| Distinct in-cell occurrences per query | about 39 | 4.0 | 7.3 |
| Share of results that fit the cell | 86–91% | 58% | 82% |
| Holds this share of the other side's items | 28% of A's, 24% of B's | 8% of Cloud's | 8% of Cloud's |
| Estimated share of everything that happened (Lincoln–Petersen) | about 24–28% | about 3% | about 5% |

The lists overlap little, so each cell holds far more than any service returns. Both shares are upper bounds; see [METHOD.md](METHOD.md).

### Precision: of what each service returned, how much was right?

Two different checks. Accuracy reads the source article and checks every field. Relevance asks only whether a record is a real incident of the kind asked about.

**Accuracy against the source article.** *Fully right:* the article reports the action happening, and the parties, the place, the date (within one day) and the category are all right. *Right action:* the action happened, with at most one other field wrong.

| Service | What was checked | Fully right | Right action |
|---|---|---:|---:|
| GDELT Cloud Events | 200 drawn at random; 149 had a readable source article | **86%** (79–91) | 99% (96–100) |
| GDELT Cloud Events, same articles as the GDELT Project rows | The Events coded from the 98 articles below | 88% | |
| GDELT Project rows | All 259 rows coded from the same 98 articles, judged blind | 9% | 40% |

**Relevance to the question.** 40 conflict country-weeks drawn at random. Every record each service returned was judged blind: is it a specific lethal incident in the country and week asked?

| Service | Records per question | On topic |
|---|---:|---:|
| GDELT Cloud, lethal Events | about 2.6 | **95%** (97 of 102 placed in the country asked) |
| AI web search B | 10 | 61% |
| AI web search A | 10 | 32% |
| AI web search C | 10 | 12% |
| GDELT Cloud, conflict and security Stories (the broad list) | about 262 | 12% |

- **Lethal Events answer this question.** The query asked for the country in any role, so it also returned 90 cross-border matches, such as strikes by one country inside another. They are not counted above.
- **Stories are the broad list.** They cover operations, arrests, statements and threats as well as lethal incidents: the right records for a broader question, and 12% on this narrow one.
- **Web search + LLM** keeps only records of the kind asked, so 97% of its 123 extracted conflict records were on topic. That is relevance, not a field-by-field check, and it adds no recall: it cannot find what the search did not return.

### What a record carries

| Field | GDELT Cloud Event: present · correct | Web search + LLM record | Web result |
|---|---|---|---|
| Occurrence date | 100% · 91% within a day | 90% | publication date only |
| Category from a fixed taxonomy | 100% · 97% | — | — |
| Coordinates · locality | 100% · 94% | 77% some sub-national place | — |
| Acting party · receiving party | 99.7% · 81% (actors right 91%) | 77% · 28% | — |
| Entity with a Wikipedia or registry ID | 55% · link right 98% | — | — |
| Fatality count (conflict) | 100% | 27% | — |
| Linked Story and sources | 100% · 11.2 articles on average · 62% non-English | URLs | URL |
| One record per occurrence | 8% have a copy | 1–4% repeat | 52% of on-topic results repeat |

## Why the results look like this

**How GDELT Cloud beats the GDELT Project while reading the same article stream.** The GDELT Project's article stream is one of Cloud's inputs. What differs is what each system does with an article.

| Step | GDELT Project 2.0 | GDELT Cloud |
|---|---|---|
| Reading | Dictionary-based coding: one row per actor–action pattern in a sentence | A language model reads the article and decides whether an event happened |
| One occurrence | 4.1 rows per matched incident, never merged | Articles clustered into a Story, one Event per occurrence (1.2 records per incident) |
| Who and where | Actor strings and the first place named | Parties with roles, resolved to entities, coordinates and locality |
| When | Publication date | Occurrence date with its basis |
| Sources | The article stream | The stream, plus native feeds from 440+ regional outlets and translated non-English sources |

On the same 98 articles, 9% of the GDELT Project's rows were fully right, against 88% of Cloud's.

**Where web search wins.**
- It indexes more of the web, including specialist monitors that are not in any news stream.
- When you can describe the item, the top result is usually it.

**Where web search loses.**
- A results page is a ranking, not a list.
- One monitoring question returns about 1–4 distinct lethal incidents from a page of 10 results, and often the day's dominant story rather than the one you need.

**Why everyone's conflict recall is low.**
- UCDP counts single deaths and builds its list from sources no news crawl reaches, such as broadcast monitoring, army communiqués, NGO monitors and local radio.
- 40% of the conflict incidents (240 of 604) were found by no tested service.

## Expected criticisms, and our answers

| Criticism | Answer |
|---|---|
| "UCDP is the wrong denominator." | It is independent of every service, public, and counts single deaths, so it is hard for everyone. We add Indepaz, SATP and five non-conflict lists, and report each panel separately. |
| "Web search was not given a fair chance." | Each web service was asked in the query style its own documentation recommends, with its own news or date-window mode. Depth differs on purpose: a database lists, a search engine ranks. At an equal number of calls GDELT Cloud still returns more: 31% of conflict incidents from one call, against 25% for the best web search. All three web searches together reached 33% (37% with an LLM step). A sample second look at the full articles behind web search's own results, the equivalent of GDELT Cloud's, adds about 2 points to the best web search (24.5% to 26%, at most 34%), and recall by depth extrapolates to 30–32% at twice the results and 37–42% at five times (`results/web_second_look.md`, `results/web_depth.csv`). The next release measures a deeper-search configuration directly, and a lookup mode where web search is strongest. |
| "Web search + LLM is as good as GDELT Cloud." | Its 97% is relevance: the LLM keeps records of the kind asked. It does not check fields against the source, it adds no recall (A 17% against A's 18%, B 23% against 25%, C 8% against 12%), and its records carry fewer fields. It adds about 0.06¢ and 7 seconds a question. |
| "An AI judged it." | Reviewers were Claude models, a different model family from the one GDELT Cloud uses for coding. Records were shuffled and stripped of source names. A second reviewer re-judged 40 incidents (κ = 0.83). Every verdict is published in `judgments/`. |
| "You picked categories that suit you." | Conflict and non-conflict lists were sampled at random or taken in full, across every category we code, including those where Cloud loses. |
| "Searching after the fact flatters web search." | It does. Web indexes gain follow-up coverage with hindsight, so web figures are, if anything, high. Timeliness is not measured directly; `results/timeliness_estimate.md` estimates it from the publication dates of each service's matches. |
| "Why are the web services anonymous?" | Their terms restrict publishing named performance comparisons. The scores describe how this kind of tool behaves on monitoring questions. To compare a service you use, plug it in: any web search service works through a small adapter ([AGENTS.md](AGENTS.md)). |
| "Wikipedia Current Events favours English-language prominence." | Yes. We disclose it and stratify by Wikipedia's own categories. |
| "GDELT Cloud's figures depend on how you queried it." | They do. Place filters alone returned 44% of conflict incidents and 93% of non-conflict items. A second look at the candidates the same calls returned, and a recheck of the incidents only web search found, raised that to 52% and 95%. Both are published (`cloud_filters` and `cloud_monitor` in `results/occurrences.csv`). |

## Run it yourself

Requires Python 3.10+ (standard library only) and a GDELT Cloud API key. Any web search service plugs in through a small adapter, and so can any event list. Step-by-step instructions, written so a coding agent can follow them, are in [AGENTS.md](AGENTS.md).

```bash
python -m unittest discover tests
```

```bash
python bench.py refs
```

```bash
python bench.py cloud
```

```bash
python bench.py gdelt
```

```bash
python bench.py check-adapter --adapter adapters/my_search.py
```

```bash
python bench.py web --adapter adapters/my_search.py --label my_search --max-usd 5
```

```bash
python bench.py extract --label my_search --base-url <endpoint> --model <model> --usd-in <price> --usd-out <price> --max-usd 1
```

```bash
python bench.py eventlist --file my_events.csv --label my_list
```

```bash
python bench.py packets
```

Reviewers fill in `run/judgments/` following [JUDGING.md](JUDGING.md) and [JUDGING_CELLS.md](JUDGING_CELLS.md). Then:

```bash
python bench.py score
```

```bash
python report.py --results run/occurrences.csv
```

- **Add a search service.** Copy `adapters/template.py` (Python) or `adapters/template_curl.sh` (any command) and map the request and response fields. The contract is in [adapters/README.md](adapters/README.md) and `schemas/`. `adapters/mock.py` runs the whole pipeline offline for free.
- **Compare an event list.** Export another dataset or your own log with the columns in `templates/event_list.csv`; `bench.py eventlist` matches its rows to the cases by date and place, and they enter the blind review beside every other source.
- **Web search + LLM** works with any endpoint that speaks the chat-completions or responses protocol. Use a small, low-cost LLM; any model works.
- `refs` reproduces our exact UCDP samples, by seed. Every paid call is reserved in a local ledger first and stops at `--max-usd`.

### What it costs to run

| Item | Per question | Per 1,000 questions |
|---|---:|---:|
| AI web search A, B, C | 0.52¢, 0.70¢, 0.80¢ | $5.20, $7.00, $8.00 |
| LLM extraction (web search + LLM) | 0.06¢ | $0.60 |
| GDELT Cloud, filtered lists | 4.1 calls (conflict), 7.3 (non-conflict) | 4,100–7,300 calls |
| Review | AI reviewer time, or about 1 minute per occurrence by hand | Same |

### Cost, time and value per task

Fees and latency are measured at list prices (`results/cost.csv`, rounds 1–3: 158 conflict country-weeks and 93 non-conflict questions). Recall at an equal number of calls covers all 604 conflict incidents (`results/equal_calls.csv`). Yield per question comes from 40 random conflict country-weeks with every record judged blind (`results/on_topic.csv`). A GDELT Cloud call costs 3.3¢ inside a plan, up to 6.7¢ at the highest overage rate.

A call does different work on each side. One GDELT Cloud call returns up to 100 structured records, and GDELT Cloud pages through everything that matched the place, week and topic. One web search call returns a page of links, and the search stops there.

**Price and latency per call:**

| Service | Price per call | Latency (median) |
|---|---:|---:|
| AI web search A | 0.52¢ | 1.7 s |
| AI web search B | 0.70¢ | 2.0 s |
| AI web search C | 0.80¢ | 2.4 s |
| LLM step (web search + LLM) | 0.06¢ | 6.9 s more |
| GDELT Cloud | 3.3¢ (6.7¢ at overage) | 2.4 s |
| News API A\*, article search (up to 100 articles) | 1.5¢ (0.6–1.8¢ by plan; 5× for dates over 30 days old) | 1.4 s |
| News API A\*, article clusters (up to 50) | 7.5¢ (3–9¢ by plan; 4× for dates over 30 days old) | 1.5 s |

**Conflict recall at an equal number of calls** (604 incidents):

| Calls per question | GDELT Cloud | AI web search B | AI web search A | AI web search C |
|---|---:|---:|---:|---:|
| 1 | 31% (27–35), first page of conflict Stories | 25% (21–28) | 18% (15–21) | 12% (10–15) |
| 2 | 39% (35–43), plus the first page of lethal Events | | | |
| Every page of the two filtered lists, 4.5 calls on average | 41% (37–45) | | | |

**Per question, 40 random conflict country-weeks:**

| Service | Calls | Records | On topic | Distinct lethal incidents | Per question | Per distinct incident |
|---|---:|---:|---:|---:|---:|---:|
| AI web search B | 1 | 10 | 61% | 4.0 | 0.70¢ | 0.17¢ |
| AI web search A | 1 | 10 | 32% | 1.5 | 0.52¢ | 0.36¢ |
| GDELT Cloud, filtered lists | 4.2 | about 261 | Events 95% · Stories 12% | about 20–30 | 14¢ | 0.48¢ |
| AI web search C | 1 | 10 | 12% | 0.8 | 0.80¢ | 1.0¢ |

GDELT Cloud's incident count is scaled from a random 18 of its records per question; the point estimate is 29.

**Calls, time and fees per question, by route** (rounds 1–3):

| Task | Service | Calls (median) | Time (median) | Fees per question |
|---|---|---:|---:|---:|
| Watch a country-week for lethal violence | AI web search A, B, C | 1 | 1.7–2.4 s | 0.52–0.80¢ |
| | Web search A or B + LLM | 2 | 8.6–8.9 s | 0.58–0.76¢ |
| | GDELT Cloud, full list | 6.3 (3) | 4.8 s | 21¢ |
| | GDELT Cloud, lethal filter | 4.1 (2) | 2.4 s | 14¢ |
| Look up a topic in a country around a date | AI web search A, B | 1 | 1.7–2.0 s | 0.52–0.70¢ |
| | GDELT Cloud, full list | 12.8 (9) | 9.6 s | 42¢ |
| | GDELT Cloud, category filter | 7.3 (3) | 4.8 s | 24¢ |

**Listing every X in a country-week** (40 cells):

| Service | Calls per cell | Time per cell | Fees per cell | Correct items returned | Fees per correct item |
|---|---:|---:|---:|---:|---:|
| AI web search A | 1 | 1.7 s | 0.5¢ | 158 (4 per cell) | 0.13¢ |
| AI web search B | 1 | 2.0 s | 0.7¢ | 293 (7 per cell) | 0.10¢ |
| GDELT Cloud | 1.2 | 2.4 s | 3.9¢ | about 1,580 (39 per cell) | 0.10¢ |

How to read this:
- **A single search is the cheapest way to check one thing:** under 1¢ and about 2 seconds a call.
- **Per distinct lethal incident, every service costs a cent or less in fees.** Web search B is cheapest (0.17¢), then A (0.36¢), GDELT Cloud (0.48¢) and C (1.0¢). GDELT Cloud returns 5–7 times as many distinct incidents per question as the best web search.
- **At an equal number of calls GDELT Cloud returns more:** 31% of conflict incidents from one call, against 25% for the best web search.
- **Spending more on web search does not buy GDELT Cloud's coverage.** A, B and C together returned 33% of conflict incidents, against GDELT Cloud's 52%. A results page ranks; it does not list.
- **Per correct item in a list, the fee is about the same,** 0.1¢. GDELT Cloud's items arrive dated, placed, categorised and de-duplicated.
- **Fees are only part of the cost.** As an illustration, not a measurement: at 10 seconds a result and $60 an hour, reading costs about 1.7¢ a web result, several times its search fee. The LLM step turns a page into records for 0.06¢ and about 7 seconds, and finds nothing new.

## Files

| Path | What it holds |
|---|---|
| `bench.py` | The runner |
| `AGENTS.md` | Step-by-step instructions for adding a service and running the suite, for people and coding agents |
| `adapters/` | The adapter contract, a Python template, a shell template and an offline mock |
| `schemas/` | JSON Schemas: search request, search results, extracted records, event-list row |
| `templates/event_list.csv` | The columns for comparing any event list |
| `tests/` | Offline end-to-end test of the runner |
| `report.py` | The HTML report |
| `site/build.py` | The program page |
| `METHOD.md`, `SUITE.md` | What is measured and how; the test suite in plain terms |
| `JUDGING.md`, `JUDGING_CELLS.md` | Reviewer instructions |
| `cases.md` | Worked examples |
| `suite/` | The inputs: occurrences, questions, cells |
| `references/` | Curated reference lists |
| `results/` | One row per occurrence and service, plus summary tables |
| `judgments/` | Every verdict |
| `CHANGELOG.md`, `VERSIONING.md` | What changed and how releases are frozen |

## Credits and licences

- **Code:** MIT (`LICENSE`). **Results and judgments:** CC BY 4.0 (`DATA_LICENSE.md`).
- **UCDP Candidate Events:** Uppsala Conflict Data Program, CC BY 4.0.
- **Wikipedia Current Events:** CC BY-SA 4.0; each item links to its day's page.
- **USGS:** public domain.
- **GDACS, WHO, Indepaz and SATP:** facts and links only.
- **GDELT Project 2.0:** open data.
- **Judging:** AI reviewers (Claude models), a different model family from the one GDELT Cloud uses for coding.
