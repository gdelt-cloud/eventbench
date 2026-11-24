# Method

This benchmark asks one question per occurrence: **when something happened in the world, does each service give you a record of it?** It then asks a second question of every record a service returns: **is it right, and is it the only one?**

## The three numbers

| Number | Plain meaning | How it is computed |
|---|---|---|
| **Recall** | Of the things that happened, how many did the service give you? | Occurrences with at least one *specific* match ÷ occurrences in the reference list |
| **Precision** | Of the records the service gave you, how many were right? | Records whose source supports them ÷ records checked |
| **Duplicates** | How often does one occurrence come back as several records? | Records per matched occurrence, and the share of records with a same-occurrence sibling |

Every number in the results carries its count (for example 30/120) and a 95% Wilson interval.

## The reference lists (the denominator)

Recall needs a list of what happened that no tested service produced. Each panel below is reported separately, because each has its own unit and scope.

| Panel | Category | What one item is | Why it is fair |
|---|---|---|---|
| UCDP Candidate Events, Oct 2026 (47 countries) | Conflict | One lethal event of organized violence (as small as one death) | Academic, coded from wire and local press independently of every service; random sample, seeded per round |
| Wikipedia Current Events, Sep 20–Nov 20 | Conflict (armed conflicts and attacks) and non-conflict (crime, politics, disasters, business, diplomacy, health, science) | One news development | Editorial and independent of every service; a random sample stratified by Wikipedia's own category, plus every item with a clear country, with a bias toward English-language prominence that we disclose |
| Indepaz massacre list, Aug–Oct 2026 | Conflict (Colombia) | Three or more people killed together | Independent monitor with a published definition; every case listed |
| SATP timelines, Nov 2026 | Conflict (Pakistan, India) | A killing reported with date and district | Independent daily timeline; tests the current pipeline |
| National elections, Oct 20–Nov 20 | Political | One national election or round | Complete calendar |
| Central-bank rate changes, Oct 20–Nov 9 | Economic | One policy-rate change | Complete list from a rate tracker |
| WHO Disease Outbreak News, Oct 20–Nov 20 | Health | One outbreak notice | Official, complete |
| GDACS red/orange alerts, Oct 20–Nov 20 | Environment | One cyclone or earthquake alert | Official, complete |
| USGS earthquakes M5.5+, Oct 1–Nov 20 | Environment | One earthquake | Official catalog; includes remote ocean quakes nobody reports. Judged for GDELT Cloud only and not in the scored tables |

### About UCDP

The Uppsala Conflict Data Program, at Uppsala University, records organized violence: state-based conflict, non-state conflict and one-sided violence against civilians. Researchers code each event by hand from news, NGO reports, local sources and broadcast monitoring, with its date, place, sides and a best estimate of deaths; an event can be a single death.

- **Candidate Events** is UCDP's monthly, preliminary release, published about a month after the events it covers. We use the October 2026 Candidate file (v26.0.10).
- The final **Georeferenced Event Dataset (GED)** is revised and released once a year.
- So UCDP is not a real-time feed. It is a careful record made after the fact, which is why it works as a yardstick: no tested service produced it, and it reaches sources that no news crawl does. That last point also makes it hard for everyone; see the README.

## How each service is asked

The web services are named only as AI web search A, B and C. Scores are about how a kind of tool behaves when asked a monitoring question, not a ranking of vendors.

The question is the one a monitoring customer asks, and it never names the incident.

| Service | What it was asked | Depth |
|---|---|---|
| GDELT Cloud | Events and Stories in the country, ±2–5 days, **all categories**, matched by country or by either actor's origin; within 150 km where coordinates exist; the expected category for non-conflict items; optionally `search=` with the place | Every page (up to 800 records per route) |
| GDELT Project 2.0 | See "What we searched in the GDELT Project" below | All rows near the case, 25 nearest kept |
| AI web search A and B (well-known AI web search APIs) | Conflict: one natural-language question per country-week (*"people killed in attacks, clashes or violence in {country}, {week}"*). Non-conflict: one question per item naming the topic, country and approximate date, but not the incident | 10 results, in each service's news or date-window mode |
| AI web search C | The same questions as short keyword queries (*"{country} attack killed"*, *"{country} arrest court trial"*), the style its documentation recommends, in its news mode with the date range. Its run with the long question is kept as a disclosed variant: that run returned mostly off-topic pages | 20 results |
| Web search + LLM | Each results page above, handed to an LLM that returns de-duplicated records (see below) | Whatever the search returned |
| Any service you add | The same request through an adapter ([adapters/README.md](adapters/README.md)) | You set `--max-results` |

Depth differs on purpose: a database lists everything that matches, and a search engine returns a ranked page. A run can page the web services further by issuing more queries; the runner records every request and its cost.

**GDELT Cloud's two figures.** The first review counts what the place-and-week calls returned (`cloud_filters`). Reviewers then took a second look at the candidates the same calls returned, and rechecked each incident that only web search had found: it was looked up through the API's search and counts only when a monitoring call (the country in any role, all categories) also returns the record. The headline figure (`cloud_monitor`) includes both; both are published.

### What we searched in the GDELT Project

- **Files:** the public 15-minute Events export and the translation export (machine-translated non-English sources) for every interval from a day before the earliest case to a week after the latest.
- **Rows:** CAMEO root codes 18 (assault), 19 (fight) and 20 (unconventional mass violence) only.
- **Matching:** rows within 100 km of the case's coordinates and from one day before to three days after its date. A case with no coordinates matches rows in the same country whose source URL shares words with the case description. The 25 nearest rows are kept.
- **Judging:** each row is shown with its coded actors, action and place, plus its source article's headline when the page could be read. A row counts when either reading matches.
- **Not searched:** the GKG, the Mentions table, other CAMEO roots (such as coerce or threaten), and the GDELT DOC full-text search. The GDELT Project arm is not tested on non-conflict items, because the CAMEO codes do not map cleanly to elections, rate decisions or outbreak notices.

### What "web search + LLM" is

It is the pipeline a developer builds to turn a web search API into something like an event feed:
1. Run the search question.
2. Hand the page of results to an LLM.
3. The LLM returns a de-duplicated list of records: date, place, parties, deaths and the source URLs behind each one.

There is one LLM call per results page. It makes results countable and removes repeats, at under 0.1¢ and about 7 seconds per page. It cannot find anything the search did not return, so its recall is at most the search's. We used a small, low-cost LLM; any model works (`bench.py extract`).

## How matching is judged

1. All candidate records for an occurrence are pooled, shuffled, and stripped of their source names ([JUDGING.md](JUDGING.md)).
2. A reviewer marks each record **S** (this occurrence) or **A** (a roundup that names it), or leaves it out.
3. A second reviewer re-judges a subset, and we report Cohen's κ. Our published round used Claude models as reviewers, a different model family from the one GDELT Cloud uses for coding. Disagreements are listed in the results.
4. The key that maps record ids back to services is applied only after judging (`bench.py score`).

## The listing test (taxonomy cells)

Recall against a reference list asks whether one known thing appears. A buyer of structured data also asks for **everything of a kind, in a place and time**. No independent list exists for "every corporate development in Indonesia this week", so we estimate one.

1. **The cells.** For each category × country × week, Cloud returns its complete list. One web search returns its top 10.
2. **Web results.** Reviewers mark which web results are real, in-cell occurrences, group repeats, and look each one up in Cloud's complete list.
3. **Cloud sample.** Reviewers check a random sample of 10 Cloud records per cell: does it fit the category, and did the web search return it?
4. **The estimate.** Two overlaps result: the share of web's verified items that Cloud has, and the share of Cloud's verified items that web search returned. Treating the two as independent captures of the same population gives the Lincoln–Petersen estimate of the total, N ≈ (Cloud in-cell) × (web in-cell) ÷ (found by both). Each service's share is its count ÷ N.

Both services favour prominent occurrences, so the captures are positively correlated. N is therefore an underestimate, and both shares are upper bounds. The ratio between the two shares is the robust result. A category that went live mid-window (Governance, live Nov 16) is excluded.

## What a record carries

- **Presence.** For Cloud, presence is counted over every Event served on the sample days. For the other services it is counted over every result and every LLM-extracted record.
- **Correctness.** Correctness comes from reviewers reading the source article: action, actors, place, date and category. A separate review of every entity link on the random Events asks whether the linked entity, with its Wikipedia page, is the right real-world entity, and whether it sits on the right actor role.
- **Work.** For one structured question asked across 10 countries, we time and price each route.

## Precision

Two checks, reported separately.

**Accuracy against the source.**
- **GDELT Cloud:** a uniform random sample of all Events served on chosen days. A reviewer opens each Event's source article and checks the action, actors, place, date and category. *Fully right* means all five are right (the date within one day); *right action* means the action happened, with at most one other field wrong.
- **GDELT Project:** every row the Project coded from the same articles. Rows are shown blind beside Cloud's row, so both systems are scored on the same text.

**Relevance to the question.** 40 conflict country-weeks are drawn at random. Every result each web search returned, every lethal Event GDELT Cloud returned, and a random 18 of the roughly 261 records its filtered lists returned per question are judged blind: is it a specific lethal incident in the country and week asked? Repeats are grouped into distinct incidents. Records that are relevant but placed in another country (a cross-border strike, matched because the query asked for the country in any role) are counted apart.

## Cost per task

- **Fees and time:** every paid call is logged with its price and latency. A GDELT Cloud call is priced at a plan's query-unit rate (3.3¢) and at the highest overage rate (6.7¢).
- **Equal calls:** recall when every service gets the same number of calls per question: one web search page against GDELT Cloud's first page, its first two pages, and every page of its two filtered lists.
- **Per distinct incident:** fees per question divided by the distinct on-topic incidents it returned, from the relevance sample above.

## What this does not measure

- **Timeliness.** Everything was searched after the fact. Web indexes gain follow-up coverage with hindsight.
- **Answer quality of chat assistants.** This measures retrieval and records, not prose answers.
- **Commercial event datasets and intelligence feeds.** Their licences restrict competitive evaluation.
- **POLECAT.** Its public files end in 2024, so it has no overlap with these dates.

## Reproduce it

See [README.md](README.md#run-it-yourself) and [AGENTS.md](AGENTS.md). With the same seed, `bench.py refs` draws the same UCDP sample. Live services change, so expect small differences. To compare a service or dataset we did not test, plug it in through an adapter or `bench.py eventlist`; it is judged blind beside the rest.
