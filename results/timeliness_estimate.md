# Timeliness estimate: what if each service had been asked within days, not weeks?

EventBench asked every service weeks after the incidents (mostly 20–23 November 2026, for incidents from August to November). This note estimates, from data the benchmark already holds, how the conflict recall figures would change if each service had been asked soon after each incident. No new searches or paid calls were made.

**Measured:** the publication date each search service returned for every page that reviewers judged a match; the timestamps on every GDELT Cloud record that reviewers judged a match; Wikipedia Current Events item counts; ten Wikipedia revision histories; UCDP's own source dates.
**Estimated:** recall at T+k = hits whose earliest matching page or record existed by the end of day D+k (UTC, D = the reference date), divided by all incidents. It assumes the same question, the same ranking and no indexing lag, so every web figure is an upper bound. The GDELT Cloud figure assumes a record is servable once it exists (see Caveats).

Per-hit dates: [`timeliness_per_hit.csv`](timeliness_per_hit.csv) (1,583 hits, conflict and non-conflict).

## Method

**Web search A, B and C.** For every incident a service found (`1` in its column of `occurrences.csv`), we took every result reviewers marked **S** for it, looked up that page's publication date in the stored search response, and kept the earliest. A dates pages to the day; B and C give a time. The provider dates agree with the date in the page URL for 178 of 182 hits whose URL carries one.

**GDELT Cloud.** For every hit, we took every matched record (`cloud_ids`, or the second-look and recheck verdicts for the 43 hits recorded without ids) and read its timestamps from the settled serving rows, in two bounded reads (exact ids, partitions 2026-09-15 to 2026-11-25):
- **Record first seen:** an Event's `coded_at`, or a Story's first-seen time (when the Story was formed). The earliest across matched records.
- **Source articles:** a Story's date (its articles' day), or for an Event its earliest linked Story date and first-seen date.
- `coded_at` is the latest coding, so it bounds first coding from above. For 660 of 703 matched Events it falls on the day of the Event's earliest linked Story, so re-coding moves very few.

## Conflict: 604 incidents

Share of each service's hits whose earliest match existed by the end of each day:

| Service | Hits (measured) | End of day D | D+1 | D+3 | D+7 | No date |
|---|---:|---:|---:|---:|---:|---:|
| GDELT Cloud, record first seen | 312 | 178 (57%) | 271 (87%) | 305 (98%) | 307 (98%) | 5 |
| GDELT Cloud, earliest source article | 312 | 216 (69%) | 282 (90%) | 306 (98%) | 307 (98%) | 5 |
| GDELT Cloud, Event coded (hits with an Event) | 192 | 115 (60%) | 174 (91%) | 190 (99%) | 192 (100%) | 0 |
| Web search A | 110 | 64 (58%) | 90 (82%) | 101 (92%) | 108 (98%) | 1 |
| Web search B | 148 | 81 (55%) | 126 (85%) | 142 (96%) | 148 (100%) | 0 |
| Web search C | 74 | 50 (68%) | 71 (96%) | 72 (97%) | 74 (100%) | 0 |

The 5 undated GDELT Cloud hits are Indepaz massacres from August and early September whose records fall before the window we read.

Median time from the start of the incident day (00:00 UTC) to the earliest match: GDELT Cloud record 20.6 h, B page 19.8 h, C page 16.4 h (A gives dates only).

**Implied recall if asked at T+k** (upper bounds; 95% Wilson intervals):

| Service | Measured, asked weeks later | T+0 (end of day D) | T+1 day | T+3 days | T+7 days |
|---|---:|---:|---:|---:|---:|
| **GDELT Cloud** | **51.7%** (312) | 29.5% (26–33) | **44.9%** (41–49) | 50.5% (47–55) | 50.8% (47–55) |
| Web search B | 24.5% (148) | 13.4% (11–16) | **20.9%** (18–24) | 23.5% (20–27) | 24.5% (21–28) |
| Web search A | 18.2% (110) | 10.6% (8–13) | **14.9%** (12–18) | 16.7% (14–20) | 17.9% (15–21) |
| Web search C | 12.3% (74) | 8.3% (6–11) | **11.8%** (9–15) | 11.9% (10–15) | 12.3% (10–15) |

Share of hits in place by D+1, by reference list: UCDP: GDELT Cloud 145/174, A 48/65, B 78/98, C 19/21. Wikipedia armed-conflict items: 109/113, 39/42, 44/45, 50/50. Indepaz and SATP: 17/25 (5 undated), 3/3, 4/5, 2/3.

### What it implies

- **Waiting weeks added little after day 3.** Every service had 92–98% of its eventual hits in place by D+3. Hindsight beyond T+3 days is worth at most 1.5 points of recall for any service.
- **At T+1 day every figure falls, and the ranking holds.** GDELT Cloud drops from 51.7% to at most 44.9% and B from 24.5% to at most 20.9%, so GDELT Cloud stays about 2.1 times B, as measured. A falls 3.3 points and C 0.5.
- **In points GDELT Cloud loses most at T+1 (6.8, against 3.6 for B), because it has the most hits.** As a share of hits it loses 13%, against 15% for B, 18% for A and 4% for C. Of its 36 hits first seen after D+1, 25 had no source article before D+2: late coverage, not slow coding. The other 11 had an article by D+1 but a record a day or more later; 6 of them fall in the 14–15 October ingest outage (about 29 hours), when Stories were formed on recovery. Without that outage the T+1 share would be about 89% (277 of 312).
- **By the end of the incident day (UTC), recall is 55–68% of the measured figure for every service**: 8–30%.
- **The web figures are upper bounds on these same pages.** A page must exist and be indexed to be returned, and indexing lag is not measured. Rankings would also differ in real time: fewer competing pages could lift an early report into the top 10, and a monitor asking daily rather than weekly gets more result slots per incident. Neither effect is estimated here.

## Non-conflict: 351 items (lookups, for reference)

These questions named the topic, country and approximate date, so they behave like lookups.

| Service | Measured | T+0 | T+1 | T+3 | T+7 |
|---|---:|---:|---:|---:|---:|
| GDELT Cloud | 94.6% (332) | 72.6% | 92.6% | 94.6% | 94.6% |
| Web search B | 72.1% (253) | 70.7% | 72.1% | 72.1% | 72.1% |
| Web search A | 59.0% (207) | 54.4% | 58.1% | 58.7% | 58.7% |
| Web search C | 41.9% (147) | 22.8% | 32.5% | 37.6% | 41.9% |

## How soon did the reference sources themselves know?

UCDP lists the sources it coded each event from, with dates. For the 428 sampled UCDP incidents, the earliest cited source was published within 1 day of the event for 310 (72%), within 3 days for 85% and within 7 days for 89%. For 45 (11%) it came more than 7 days later: monthly NGO reports, casualty trackers and timelines published weeks after the fact. Among the 209 UCDP incidents no service found, 30 (14%) have no cited source within 7 days; among the 219 found by at least one service, 15 (7%).

## Wikipedia Current Events as a monitoring source

- **Volume.** The 62 stored daily pages (20 September to 20 November) list 1,126 items: **18 a day** worldwide (median 18, range 10–29). "Armed conflicts and attacks" holds 293, **4.7 a day**.
- **Against UCDP.** UCDP's October Candidate file has 2,389 events in 48 countries, 77 a day (126 with 10 or more deaths, about 4 a day). The portal's conflict section is the size of the mass-casualty stream, and many of its items are statements and developments rather than incidents.
- **Speed.** The stored pages carry no revision history, so we read the histories of 10 day pages through the public Wikipedia API (one call each; nine drawn with seed 20261124, plus one test page). Each day page is created as a stub at 03:30 UTC the day before. Share of the page's final text in place:

| By the end of | Median | Range |
|---|---:|---:|
| Day D | 57% | 44–66% |
| D+1 | 94% | 82–100% |
| D+3 | 100% | 93–100% |
| D+7 | 100% | 100% |

Page size is a proxy for items: it also counts copy edits and reorganisation. Read it as "most of a day's items are written that day or the next". As a feed, the portal is a T+1 source covering a few prominent conflict items a day.

## Why 240 conflict incidents were found by no service

209 of the 240 are UCDP incidents. We drew 40 of the 209 (seed 20261124). Each was classified from its UCDP row (deaths, place precision, date precision, cited sources and their dates) and the reviewers' panel note. An incident can carry several reasons.

| Reason | Incidents (of 40) | How decided |
|---|---:|---|
| Zero or one death (UCDP best estimate) | 26 | UCDP field |
| Official, social-media or monitor sourcing | 32 | UCDP source names, read by hand: 13 social media or armed-group claims (X, Telegram), 13 monitors and timelines, 6 army, police or government statements. The other 8 cite news outlets |
| Remote or rural place (village, hill, road, countryside) | 23 | Read from UCDP's place description |
| Approximate location (province or vaguer) | 10 | UCDP place precision 4 or more |
| Local-language sources only | 10 | Read from UCDP's source list |
| Event date ambiguity | 2 | UCDP date precision is exact for all 40; in 2, the nearest report was 3 or more days off |
| *Also:* covered only in a roundup or a coarser record | 8 | Panel note |
| *Also:* gang or criminal killing reported by city press | 7 | Read by hand |
| *Also:* UCDP's earliest source published 7 or more days later | 9 | UCDP source dates |

One reason per incident, the most likely: official or social sourcing 11, zero or one death 11, local language only 6, approximate location 4, covered only in a roundup 3, remote area 3, city crime 1, date 1. Only 1 of the 40 (a double murder in Cape Town, reported in English) has none of the six listed reasons.

The same pattern holds across all 428 UCDP incidents, using UCDP fields alone (no service found it / at least one did): best estimate of one death or fewer 72% / 46%; a single cited source 76% / 49%; only social-media or monitor sources 38% / 13%; earliest source 7 or more days late 16% / 8%; province-level place or vaguer 13% / 10%. Date precision is not a factor (exact day for all).

Per-incident classification of the 40:

| UCDP id | Country | Deaths | Source kind | Most likely reason | All reasons |
|---|---|---:|---|---|---|
| U644102 | Afghanistan | 1 | social | official/social sourcing | ≤1 death, non-press source |
| U644788 | Afghanistan | 0 | social | zero or one death | ≤1 death, remote, non-press source, date |
| U649352 | Bangladesh | 1 | monitor | event date ambiguity | ≤1 death, non-press source, date |
| U648204 | Brazil | 1 | press | local-language only | ≤1 death, local language, city crime |
| U648265 | Brazil | 1 | press | local-language only | ≤1 death, local language, city crime |
| U644481 | Burkina Faso | 3 | social | official/social sourcing | local language, remote, non-press source |
| U648550 | Burkina Faso | 1 | social | official/social sourcing | ≤1 death, local language, remote, non-press source |
| U648668 | Burkina Faso | 0 | social | official/social sourcing | ≤1 death, local language, remote, non-press source |
| U650694 | Burundi | 2 | press | local-language only | local language, remote, near miss |
| U647047 | Cameroon | 2 | social | official/social sourcing | approx. place, remote, non-press source, near miss |
| U647050 | Cameroon | 1 | social | zero or one death | ≤1 death, non-press source |
| U647054 | Cameroon | 1 | social | zero or one death | ≤1 death, remote, non-press source |
| U646528 | Ecuador | 4 | press | covered only in a roundup | local language, near miss, city crime |
| U648683 | India | 1 | monitor | zero or one death | ≤1 death, non-press source, source 7+ d late |
| U650420 | Iran | 1 | official | approximate location | ≤1 death, approx. place, non-press source, near miss |
| U648492 | Mali | 0 | official | official/social sourcing | ≤1 death, remote, non-press source |
| U648972 | Mali | 0 | official | official/social sourcing | ≤1 death, approx. place, remote, non-press source |
| U649045 | Mali | 2 | monitor | remote area | remote, non-press source, source 7+ d late |
| U648605 | Mexico | 1 | press | local-language only | ≤1 death, local language, city crime |
| U649209 | Mexico | 3 | press | local-language only | local language, city crime |
| U650536 | Mexico | 0 | press | local-language only | ≤1 death, local language, near miss, city crime |
| U647703 | Myanmar | 2 | monitor | covered only in a roundup | approx. place, remote, non-press source, near miss |
| U648433 | Myanmar | 1 | monitor | zero or one death | ≤1 death, remote, non-press source, source 7+ d late |
| U646418 | Niger | 0 | social | official/social sourcing | ≤1 death, approx. place, remote, non-press source, source 7+ d late |
| U645234 | Nigeria | 5 | social | remote area | remote, non-press source |
| U645681 | Nigeria | 1 | monitor | zero or one death | ≤1 death, remote, non-press source |
| U645780 | Nigeria | 2 | social | official/social sourcing | remote, non-press source |
| U647231 | Nigeria | 1 | monitor | zero or one death | ≤1 death, remote, non-press source |
| U646663 | Pakistan | 3 | official | official/social sourcing | remote, non-press source, near miss |
| U647945 | Pakistan | 1 | official | zero or one death | ≤1 death, non-press source |
| U648877 | Russia | 1 | monitor | approximate location | ≤1 death, approx. place, non-press source, source 7+ d late |
| U648907 | Russia | 3 | monitor | approximate location | approx. place, non-press source, source 7+ d late |
| U648943 | Russia | 3 | monitor | official/social sourcing | remote, non-press source, source 7+ d late |
| U649101 | Somalia | 2 | social | remote area | approx. place, remote, non-press source |
| U649271 | Somalia | 0 | social | zero or one death | ≤1 death, remote, non-press source |
| U648837 | South Africa | 2 | press | city crime | city crime, source 7+ d late |
| U648058 | Syria | 1 | monitor | zero or one death | ≤1 death, approx. place, remote, non-press source |
| U648107 | Syria | 1 | monitor | zero or one death | ≤1 death, remote, non-press source |
| U646472 | Ukraine | 1 | official | covered only in a roundup | ≤1 death, non-press source, near miss |
| U648879 | Ukraine | 1 | monitor | approximate location | ≤1 death, approx. place, non-press source, source 7+ d late |

## Caveats

- **Upper bounds for web search.** A page that exists may not yet be indexed. A provider's date can be an update or crawl date: 4 of 182 checked against the URL date were off by more than a day.
- **Existing is not the same as served for GDELT Cloud.** A coded record reaches the API when the settle publishes its date. That lag is usually one settle cycle, but the settle has stalled before. It is not measured here.
- **Stories and geography.** A Story has no geography of its own; a country filter finds it through its linked Events. For the 120 conflict hits matched only by Stories, the Story's first-seen time may be a little earlier than when a country query could return it.
- **The question is held fixed.** The estimate keeps the weekly web question and GDELT Cloud's same place filters. It does not model a daily cadence.
- **Day boundaries are UTC.** Local dates and UCDP's dating can differ by a day. Matches dated before the reference date (up to a few per service) count as on time.
- **Judging is unchanged.** Hits are the published verdicts. A record or page that appeared only after the search date could not have been judged and is not counted anywhere.
