# Web search second look (sample estimate, 2026-11-24)

How much would AI web search A, B and C gain from the same second look that GDELT Cloud got? This is estimated on a sample. It used no new searches and no paid calls. Row-level verdicts are in `web_second_look.csv`.

## What each second look is

**GDELT Cloud (already in the headline).** Cloud's first review (`cloud_filters`, 265/604 = 43.9% on conflict) judged candidates that had been pre-selected from the place-and-week calls by place name. The second look then re-ran the same monitoring calls (150 km radius plus country in any role, all categories). It chose up to 25 candidates by date (±2 days) and violence keywords instead of place name, and gave reviewers summaries and source headlines. That added 31 incidents: 9.6% of the 322 misses it re-examined. The recheck of incidents that only web search found added 16 more. The total is 312/604 = 51.7% (`cloud_monitor`), or +7.8 pp.

**Web search (first pass).** Reviewers saw every result the question returned. For each result they saw only the date, the title, the first 160–260 characters of the provider's excerpt and the URL, never the article. So the web arms had no candidate filter to widen. What they lacked was evidence.

**The fair web equivalent (this test).** Re-examine the same results that the same question returned for the incident's country-week, with no new searches:
- Fetch each result page over plain HTTP and read the article text. Where the fetch failed, the provider's stored excerpt (up to 700 characters) is the fallback.
- Pre-filter passages by place name and transliteration variants.
- Judge each passage by [JUDGING.md](../JUDGING.md).
  - **S** means the incident is the article's subject, or one of two subjects, each reported separately, as the original reviewers allowed for the two-prison Cotopaxi case.
  - **A** means the incident is one line in a multi-incident report or a list.
- Recall counts S only, as in METHOD.md.

## Sample

The sample covers 40 conflict incidents that web B (the best conflict arm) missed. It was drawn at random with seed 20261124 and stratified in proportion to B's 456 misses:

| Panel | B's misses | Sampled |
|---|---|---|
| UCDP | 330 | 29 |
| Indepaz | 15 | 1 |
| SATP | 35 | 3 |
| Wikipedia conflict | 76 | 7 |

The same 40 were checked for A and C, minus the incidents each of those arms had already found: 38 checked for A and 38 for C.

- The sample covered 918 distinct result URLs.
- 705 pages were readable, 192 fetches failed (mostly 403s), 15 pages had too little text and 6 were PDFs.
- By incident × result pair, the readable share was 73% for A, 79% for B and 74% for C.
- The place pre-filter flagged 45 of 380 pairs for A, 39 of 400 for B and 6 of 318 for C.

## Results

| Arm | Checked | S | A only | S rate (95% Wilson) | Lift to conflict recall | Estimated recall (first pass → after) |
|---|---|---|---|---|---|---|
| AI web search A | 38 | 2 | 1 | 5.3% (1.5–17.3%) | +4.3 pp (+1.2 to +14.1) | 18.2% → 22.5% (19.4–32.3%) |
| AI web search B | 40 | 1 | 3 | 2.5% (0.4–12.9%) | +1.9 pp (+0.3 to +9.7) | 24.5% → 26.4% (24.8–34.2%) |
| AI web search C | 38 | 0 | 1 | 0% (0–9.2%) | +0 pp (0 to +8.1) | 12.3% → 12.3% (12.3–20.3%) |

Each arm's lift is its S rate × its conflict misses (A 494, B 456, C 530) ÷ 604. If roundup lines (A) also counted, which the published rule does not allow, the estimates would be A 24.7%, B 32.1% and C 14.6%.

For comparison, GDELT Cloud scores 43.9% on the first pass and 51.7% with its second look. Even the top of each web interval stays below Cloud's first pass.

The hits:
- **Turkana, Kalata, Oct 27.**
  - B's result carries the reference's own headline, but it was published Oct 30; only the article body dates the attack to Oct 27.
  - A had the same incident at ranks 1 and 4.
- **Cotopaxi prison riot, Oct 22.** A's two-prison reports at ranks 3–5 and 7–10 give Cotopaxi its own count of four deaths.
- **Roundup lines (A).** Mir Ali, 35 killed (B rank 9, C rank 2); Chassad (B rank 9); Niamana (B rank 5); the Cartagena massacre in an attack-tracker list (A rank 1).

Why most incidents stay missed:
- In 15 of the 40, no result in any arm names the place.
- The 7 Wikipedia items are not lethal incidents, and 2 were asked about the wrong country.
- Several UCDP items come only from army posts or equipment-loss trackers.

## Depth: recall@k from stored hits (no new calls)

Each hit's rank is the first result reviewers marked S. Ranks were recovered for 101/110 of A's hits, 140/148 of B's and 66/74 of C's, and the curves are scaled to all hits.

| k | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| A | 9.7% | 12.6% | 15.1% | 16.9% | 18.2% | |
| B | 7.5% | 11.6% | 15.1% | 19.4% | 24.5% | |
| C | 8.7% | 10.2% | 11.0% | 11.5% | 11.7% | 12.3% |

**Extrapolation, not measurement.** The range runs from a log fit to a power-law fit of the yield at each rank:

| Arm | 2× results | 5× results |
|---|---|---|
| A | 20–21% | 21–25% |
| B | 30–32% | 37–42% |
| C | 13% | 13–14% |

B's yield per rank had not flattened by rank 10, so its range is the least certain. C cannot go much deeper: only 80 of its 234 conflict questions returned the full 20 results.

## Cost (234 conflict country-weeks, 604 incidents)

Per-call prices are from the spend logs: A $0.005, B $0.007, C $0.008.

| Option | A | B | C | All three |
|---|---|---|---|---|
| As run (1 call per country-week) | $1.17 | $1.64 | $1.87 | $4.68 |
| (a) Full-set second look | $0 search; 1,863 fetches, about 590 flagged passages | $0 search; 2,237 fetches, about 450 passages | $0 search; 1,742 fetches, about 110 passages | 5,627 fetches (about 25 min, 4 at a time); about 1,150 passages: about 19 reviewer-hours, or about $1 with a small LLM reader (about $10 without the pre-filter; estimated, not run) |
| (b) 2× results (a second call) | $2.34 | $3.28 | $3.74 | $9.36 |
| (c) Daily questions (7×) | $8.19 | $11.47 | $13.10 | $32.76 |
| (d) All three arms per question | | | | $4.68; the union of stored first-pass hits is 200/604 = 33.1% |

The recall effect of daily questions cannot be estimated from stored data.

## Caveats

- **Sample size.** With 40 incidents, each hit moves an arm by 2–5 pp, so the intervals are wide.
- **Sampling bias.** A and C were sampled only among incidents B also missed. Their misses that B found (69 for A, 103 for C) probably convert more often, so their lifts are likely understated.
- **Unreadable pages.** 21–27% of result pages could not be read over plain HTTP. One A hit came from a blocked page's stored excerpt. Pages were read on Nov 24, so live pages may have changed since the search.
- **Review.** One reviewer judged every passage, not blind to the arm, with no second reviewer. The S/A boundary decides four of the seven positive rows.
- **Pre-filter.** The place-name filter misses non-Latin-script pages and reports that name only a district.
