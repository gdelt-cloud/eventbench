# The test suite, in plain terms

The benchmark is four CSV files of inputs, one adapter per service, a judging step and a scoring step. Release 2026.11 scores 955 occurrences from `suite/occurrences_v2.csv`. Everything a service returns is saved in your local `run/` folder, so you can re-judge it. Any search service plugs in through an adapter ([adapters/README.md](adapters/README.md)), and any event list through `bench.py eventlist` ([AGENTS.md](AGENTS.md)).

## The inputs

### 1. `suite/occurrences_v2.csv`: the things that happened (1,034 rows)

One row per real-world occurrence, taken from a list no tested service produced. `suite/occurrences.csv` is the rounds 1–3 subset (436 rows plus the earthquakes); `occurrences_v2.csv` adds 520 rows and a `region` and `round` column.

- **Scored:** 955 rows, 604 conflict and 351 non-conflict.
- **Not in the scored tables:** 78 USGS earthquakes, judged for GDELT Cloud only (`judgments/usgs_out.json`), and one Wikipedia item.

| Column | Meaning | Example |
|---|---|---|
| `uid` | Stable id; the prefix names the source | `U646770` (UCDP), `IDP081` (Indepaz), `WK037` (Wikipedia) |
| `panel` | Which reference list | `UCDP Candidate v26.0.10` |
| `family` | `conflict` or `non-conflict` | `conflict` |
| `category` | Our category, for non-conflict items | `ECONOMIC` |
| `iso3`, `country` | Where it happened | `UKR`, `Ukraine` |
| `date` | When it happened, by the reference | `2026-10-21` |
| `lat`, `lon` | Coordinates, when the reference has them | `48.888, 36.308` |
| `place` | Place as the reference names it | `Lymanivka, Lozova raion, Kharkiv oblast` |
| `what` | One line on what happened | `Russia vs Ukraine; 1 killed` |
| `deaths` | Reference death count, if any | `1` |
| `source_url` | Where the reference row comes from | UCDP download URL |

How many, by panel:

| Panel | Scored rows | How chosen |
|---|---:|---|
| UCDP Candidate, Oct 2026, 47 countries | 428 | Random, seeded: 10 or 6 per country in rounds 1–3 (288), topped up to 15 per country where UCDP has that many (140) |
| Indepaz Colombian massacres, Aug–Oct 2026 | 19 | Every listed case |
| SATP Pakistan and India, Nov 2026 | 36 | Random 30 of Pakistan's 110 killings, plus all 6 for India |
| Wikipedia Current Events, armed conflicts and attacks, Sep 20–Nov 20 | 121 | Every item with a clear country |
| Wikipedia Current Events, non-conflict, Sep 20–Nov 20 | 326 | Random 68 stratified by Wikipedia's 7 non-conflict categories (rounds 1–3), plus every item with a clear country (258) |
| Official lists: elections, rate changes, WHO, GDACS | 25 | Every item in the window |
| USGS earthquakes M5.5+, Oct 1–Nov 20 | not scored | Every item; judged for GDELT Cloud only |

### 2. `suite/questions.csv`: what each service is asked (296 rows)

The file holds the rounds 1–3 questions word for word. The runner builds the same kinds of question for every row of an occurrence file (`bench.py web`), which is how the suite v2 rows were asked. A question never names the incident. Each question covers every occurrence that falls inside its scope.

| Column | Meaning | Example |
|---|---|---|
| `question_id` | Stable id | `UKR-2026-10-19` |
| `mode` | What the customer is doing (see below) | `monitor` |
| `country`, `start`, `end` | Scope | `Ukraine`, `2026-10-19`, `2026-10-25` |
| `cloud_filters` | What Cloud receives | `country=UKR`, all categories, plus a 100 km radius when coordinates exist |
| `web_question` | The natural-language question, word for word | `people killed in attacks, clashes or violence in Ukraine October 19-25 2026` |
| `covers` | Occurrence uids inside this scope | `U646770;U646958;…` |

Modes:
- **monitor:** "What happened here this week?" Nothing is named. This is used for conflict, with one question per country-week.
- **topic:** "What {topic} happened in {country} around {date}?" Nothing is named. This is used for non-conflict, with one question per occurrence.
- **list:** "Every {category} in {country} this week." This is the 40 taxonomy cells (`suite/cells.csv`).
- **lookup** and **archive** are planned for the next round. A lookup names the incident. An archive question asks about a past month without naming it.

The runner also derives a short keyword form of every question (`keyword_query`, for example `Ukraine attack killed`) for services whose own guidance prefers keywords. An adapter uses whichever form its service recommends. Request and result shapes are in `schemas/`.

### 3. `suite/cells.csv`: the listing test (45 rows)

Columns are `cell_id`, `category`, `country`, `start`, `end` and `label`. There are 8 categories × 5 countries, plus Protests in 5 more countries, all for Nov 9–15.

## Running it against each service

Each adapter turns a question into that service's own request, and `bench.py` saves the response to `run/web/<question_id>-<label>.json`.

| Service | What is sent | What is kept |
|---|---|---|
| GDELT Cloud | `/api/v2/events` and `/api/v2/stories`, every page. Three routes: radius, country (either actor's origin, all categories) and the expected category | Every record |
| GDELT Project 2.0 | The public 15-minute Events export and translation export, CAMEO roots 18–20 | Rows within 100 km (or, without coordinates, in the country with matching URL words), from 1 day before to 3 days after; 25 nearest, judged with the source headline |
| AI web search A | The natural-language question, top 10 | Title, URL, date, excerpt |
| AI web search B | The natural-language question in its news category with a publication-date window, top 10 | Same |
| AI web search C | The keyword form in its news mode with the date range, top 20 (the long question kept as a variant) | Same |
| Web search + LLM | Each results page, sent to an LLM that returns de-duplicated records | Date, place, parties, deaths, URLs |
| Your service | Either form of the question, through your adapter | Same as the web services |
| Your event list | Nothing is sent: rows are matched to cases by date and place | The matched rows |

## One case, start to finish

**The occurrence.**
- UCDP row `U646770`: on 21 Oct 2026, one person was killed in Lymanivka, Lozova raion, Kharkiv oblast.
- Sides: Russia vs Ukraine.
- UCDP's source: an Ukrinform article headed *"One person killed and 15 injured in Kharkiv region due to Russian strikes."*

**What each service was asked:**
- **Cloud:**
  - `events?near=48.888,36.308&radius_km=100&date_start=2026-10-20&date_end=2026-10-24` (every category)
  - the same with `country=UKR&category=<conflict types, Crime>`
  - the same two calls on `stories`

  That returned 476 records, 281 of them about violence. The 42 that best matched the place and sides went to the reviewer.
- **GDELT Project:** 114 rows within 100 km on Oct 20–24, from 70 articles. The 25 nearest articles went to the reviewer.
- **AI web search A and B:** each got *"people killed in attacks, clashes or violence in Ukraine October 19-25 2026"*. **C** got the keyword form *"Ukraine attack killed"*; its run with the long question is kept as a disclosed variant. Their results, and the LLM records made from them, are shared by every Ukrainian occurrence that week.

**What the reviewer saw.** The reference, followed by 67 occurrence-specific records and the week's shared records. All were shuffled and numbered R00001…, with no service names. For example:
- *R00096: [2026-10-22] Russian forces shell Lymanivka, killing a woman and injuring four …*
- *R00129: [2026-10-21] RUSSIA → Abduct, hijack, or take hostage → RUSSIA at Izyum …*

**The verdict.** S = R00096 and R00116. The note reads: *"Lymanivka Oct 22 woman killed 4 hurt; one day later than reference, plausible same."*

**The score.** The key maps R00096 to a Cloud Event and R00116 to a Cloud Story, so the row in `results/occurrences.csv` is:

`U646770, Cloud 1, Cloud Event 1, GDELT Project 0, web A 0, web B 0, web C 0, web C (long question) 0, web A + LLM 0, web B + LLM 0, web C + LLM 0`

Recall for a service is the share of rows with a 1. Every number carries its count and a 95% interval.

## The outputs

| File | What it holds |
|---|---|
| `run/web/*.json` | What each service returned, one file per service per question (kept locally, not published) |
| `packets/*.md` + `packet_key.json` | What reviewers saw, and the key that unblinds it |
| `judgments/*.json` | Every verdict, with a short note on hard calls |
| `results/occurrences.csv` | One row per occurrence × service |
| `results/recall_by_panel.csv` | Recall by reference panel, as counts |
| `results/equal_calls.csv`, `on_topic.csv`, `cost.csv` | Recall at an equal number of calls, relevance and yield per question, and calls, time and fees per question |
| `results/precision_audit.csv`, `structure.csv`, `taxonomy_cells.csv` | The accuracy audit, what a record carries, and the listing test |
