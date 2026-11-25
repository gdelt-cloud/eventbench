# Method

The results this method produces are published, with charts, at [gdeltcloud.com/benchmarks/events](https://gdeltcloud.com/benchmarks/events).

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
| UCDP Candidate Events, Oct 2026 (47 countries) | Conflict | One event of organized violence, as small as one death (57 of the 428 sampled carry a best estimate of zero deaths and stay in every denominator) | Academic, coded from wire and local press independently of every service; random sample, seeded per round |
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
| GDELT Cloud | Conflict (release 2026.11.1): the country-week lists, never the incident: conflict Stories and Events with deaths for the country and week. Non-conflict: Events and Stories in the country around the item's date, the expected category. Release 2026.11's conflict calls searched within 150 km of each incident and ±2–5 days around it; they are withdrawn (below) | Every page (up to 800 records per route) |
| GDELT Project 2.0 | See "What we searched in the GDELT Project" below | All rows near the case, 25 nearest kept |
| AI web search A and B (well-known AI web search APIs) | Conflict: one natural-language question per country-week (*"people killed in attacks, clashes or violence in {country}, {week}"*). Non-conflict: one question per item naming the topic, country and approximate date, but not the incident | 10 results, in each service's news or date-window mode |
| AI web search C | The same questions as short keyword queries (*"{country} attack killed"*, *"{country} arrest court trial"*), the style its documentation recommends, in its news mode with the date range. Its run with the long question is kept as a disclosed variant: that run returned mostly off-topic pages | 20 results |
| Web search + LLM | Each results page above, handed to an LLM that returns de-duplicated records (see below) | Whatever the search returned |
| News API A\* (a news-database API with article clusters) | The same questions through its own filters: the country, the date window and the keyword form, two calls (article clusters, and article search). Asked inside its 30-day window only; see below | 50 clusters and 100 articles, one call each |
| Any service you add | The same request through an adapter ([adapters/README.md](adapters/README.md)) | You set `--max-results` |

Depth differs on purpose: a database lists everything that matches, and a search engine returns a ranked page. A run can page the web services further by issuing more queries; the runner records every request and its cost.

**GDELT Cloud's conflict figure is like for like (release 2026.11.1).** Release 2026.11 scored GDELT Cloud through calls built around each incident (`cloud_filters`), plus a second look and a recheck only GDELT Cloud received (`cloud_monitor`). Both columns stay in `results/occurrences.csv` for the record and are no longer scored. The scored conflict figure is `cloud_pages`: GDELT Cloud's blind country-week lists (conflict Stories and Events with deaths, every page), credited only where the same single review every service got matched a record (`results/cloud_blind_calls.csv`). `cloud_call1` and `cloud_calls2` are its first page and first two pages. Conflict counts only the lethal reference incidents (`scope = lethal`, 480): UCDP rows with a best estimate of zero deaths and Wikipedia items reporting no death are left out for every service. On news, GDELT Cloud's like-for-like figure is the first review (93%); the second look's 95% is disclosed beside it.

**A second look for web search.** Release 2026.11 also sampled a second look for web search (`results/web_second_look.md`, `results/web_depth.csv`), measured on its 604-case scope. With GDELT Cloud's second look withdrawn, it is kept for the record and not scored.

### News API A, asked inside its 30-day window

News API A is a news database: it stores articles, clusters them into events, and takes structured filters rather than a sentence. It was asked the published questions (`suite/questions_2026_11.csv`) through `bench.py web` with two adapters, one call each:
- **Article clusters:** events whose location is the question's country and whose event date falls in the question's window, matching any of the question's keywords (`attack`, `killed` for a conflict week; the topic words otherwise), ranked by relevance, up to 50.
- **Article search:** de-duplicated articles about the country (as a concept, because its location filter matches datelines only), published from the window start to a week after its end, with the same keywords, ranked by relevance, up to 100. Each article records when the service stored it, which gives the timing figures.

The plan we ran on searches only the last 30 days, so the arm answered the 311 questions whose window started on or after 25 October (438 occurrences: 213 conflict, 225 non-conflict; clusters on 296 questions, articles on all 311). Its records were judged blind like every other source, in packets that show each question's records once (second reviewer on 18 occurrences: κ = 0.92).

**Projection to the full suite.** The window holds a different mix of reference lists from the full suite (more Wikipedia items, only the last week of October from UCDP, no Indepaz), so the in-window figure is reweighted by list: recall within each list times that list's share of the full suite, with Indepaz taking the UCDP rate. Applied to the services measured on every question, this lands within 0.4–3.3 points of their real conflict figure, always below it, and 0.7–3.6 points of their non-conflict figure. The published projection adds the average of those errors and widens the 95% interval by their spread. Every figure that rests on it carries an asterisk.

**Not measured for this arm:** questions older than 30 days (searching them costs 4–5 times as much per call), precision, and timing for clusters, which carry no creation time.

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
- **GDELT Project, same articles:** every row the Project coded from the same articles (all CAMEO categories, the English and translation exports), shown shuffled and unlabelled beside GDELT Cloud's own row in one terse form and judged on one row test ([ROW_JUDGING.md](ROW_JUDGING.md)): right, partly right or not. The GDELT Cloud record is shown above the rows, so its own row can be told apart. These row verdicts were judged in release 2026.11 and first published in 2026.11.2 (`results/rows_same_articles.csv`).
- **Conflict rows, fully blind (2026.11.2):** 100 rows drawn at random from the GDELT Project rows of the pooled run's 40 country-weeks (CAMEO 18–20 located in the country, dated in the week) and 100 from GDELT Cloud's Events for the same questions, mixed and shuffled. Each item is one row and its source article, with nothing to say which system coded it, judged on the same row test (`judgments/rows/`, `results/rows_conflict.csv`). Articles that would not load after a second, slower attempt with the same fetch tool are not counted.

**Relevance to the question.** 40 conflict country-weeks are drawn at random. Every result each web search returned, every lethal Event GDELT Cloud returned, and a random 18 of the roughly 261 records its filtered lists returned per question are judged blind: is it a specific lethal incident in the country and week asked? Repeats are grouped into distinct incidents. Records that are relevant but placed in another country (a cross-border strike, matched because the query asked for the country in any role) are counted apart.

## Cost per task

- **Fees and time:** every paid call is logged with its price and latency. A GDELT Cloud call is priced at a plan's query-unit rate (3.3¢) and at the highest overage rate (6.7¢).
- **Equal calls:** recall when every service gets the same number of calls per question: one web search page against GDELT Cloud's first page, its first two pages, and every page of its two filtered lists.
- **Per distinct incident:** fees per question divided by the distinct on-topic incidents it returned, from the relevance sample above.

## Pooled truth (release 2026.11.1)

Recall against a reference list counts only the incidents on that list, and the lists are samples. A service
that returns many real incidents the lists never sampled gets no credit for them. The pooled truth fixes that,
the way shared search evaluations (TREC) have long pooled the results of every tested system:

1. **One question per country and week**, asked of every service in the same words or its filters for the
   same words: *"people killed in attacks, clashes or violence in {country}, {week}"*
   (`suite/pool_questions_2026_11.csv`: 40 country-weeks, the random sample of the relevance test).
   - GDELT Cloud: `bench.py monitor`. Conflict Events located in the country with deaths reported, crime
     Events (`CR01`, homicide or violent crime) located in the country, and the conflict and crime Stories
     about the country, every page.
   - Web search: `bench.py web` with each service's own adapter, at its maximum results per call, in the
     style its documentation recommends, with the same three-day grace for reports published after the week.
   - The GDELT Project 2.0: the public 15-minute Events and translation exports as a user filters them: rows
     with CAMEO roots 18-20 whose action is located in the country (ActionGeo; Israel with the West Bank and
     Gaza, as for every service), dated in the week. One record per source article: its coded rows and URL,
     with no headline, since the export carries none. Its records were judged against the pool the other
     services had built (on topic, and the same incident as a pooled label or a new one), the way any added
     source is; the cached exports end on 22 November, so the last week's late reports are missing for it.
2. **One packet per question** (`bench.py pool`): every record every service returned, plus the reference
   incidents for that country and week, shuffled, with the sources hidden.
3. **Jurors** (`bench.py pool-judge`, rules in `JUDGE_POOL.md`): each record on topic or not, and one label
   per incident. Two jurors from different model families judge every record; their agreement is published.
4. **Scores** (`bench.py pool-score` for any run; `pool_report.py` for every published table): the pool is
   every incident any record was labelled with. For each service, the incidents it delivered, its share of
   the pool, the share of its records that were on topic, and its records per question; GDELT Cloud also as
   its first page of each list (one call per route). Paired over the questions with a bootstrap interval.
5. **Incident types** (`judgments/pool/incident_types.csv`, rules in `JUDGE_POOL.md`): each pooled incident
   gets one type. *Armed conflict* is every type but criminal homicide, and it is the headline: the web
   search brief names armed groups, gangs and security forces, not ordinary murder.
6. **Blind audit** (`judgments/pool/audit.csv`): 110 sampled incidents, 45 found only by GDELT Cloud, 45
   only by web search and 20 by both, shown with the source hidden to a third model, which checks that each
   is a real lethal incident in the week and not a repeat of another incident in the pool.

**Release 2026.11.1's pooled run** (`judgments/pool/`): 40 country-weeks, 48,771 records (30,037 of them the GDELT
Project's). The jurors are a Claude model (`juror_a`) and a model from another lab (`juror_b`); they agree on 94.7% of
records (κ = 0.71): κ 0.80 on GDELT Cloud's records, 0.81 on web search's and 0.63 on the GDELT Project's, which carry
no text (`results/pooled_agreement.csv`). GDELT Cloud
was asked through `bench.py monitor` on 25 November 2026; web search A, B and C at 20, 25 and 20 results. The key
(`key.json`) names each record's source and its URL or id, and each GDELT Cloud record's position in the API's
answer; record text is not published. `python3 pool_report.py` rebuilds every `results/pooled_*.csv` table.

A pooled share measures what each service delivered against what the tested services found together. It is
not a share of everything that happened: the reference-list recall above stays beside it as the check no
service can influence.

## What this does not measure

- **Timeliness.** Everything was searched after the fact. Web indexes gain follow-up coverage with hindsight.
- **Answer quality of chat assistants.** This measures retrieval and records, not prose answers.
- **Commercial event datasets and intelligence feeds.** Their licences restrict competitive evaluation.
- **POLECAT.** Its public files end in 2024, so it has no overlap with these dates.

## Reproduce it

See [README.md](README.md#run-it-yourself) and [AGENTS.md](AGENTS.md). With the same seed, `bench.py refs` draws the same UCDP sample. Live services change, so expect small differences. To compare a service or dataset we did not test, plug it in through an adapter or `bench.py eventlist`; it is judged blind beside the rest.
