# Worked cases

Each case shows the reference occurrence, then what each service returned that a blind reviewer matched to it. "None" means nothing it returned was judged to be about this occurrence. The three AI web search APIs are labelled A, B and C. Every verdict is in `results/occurrences.csv`.

## 1. A massacre in rural Colombia: Cloud and GDELT have it, web search does not

**Reference (Indepaz):** 7 Aug 2026, Abejorral, Antioquia. Three people killed.

| Service | What it returned |
|---|---|
| GDELT Cloud (Story) | *"Three men killed in rural Abejorral, Antioquia in massacre."* Headlines: *Masacre en Antioquia: tres hombres fueron asesinados en zona rural de Abejorral* |
| GDELT Project | One row: `COLOMBIA → Fight with small arms and light weapons → ? at Abejorral, Antioquia`, from lafm.com.co |
| AI web search A and B, top 10 for "people killed in attacks, clashes or violence in Colombia, Aug 3–9" | None |

Reviewer: *"Abejorral massacre of three men, clear."* The local Spanish-language report reached Cloud and GDELT through the GDELT article stream. A web search for the week's killings in Colombia surfaced other incidents.

## 2. A single death in Ukraine: only Cloud has a dated, placed record

**Reference (UCDP):** 21 Oct 2026, Lymanivka, Kharkiv. One killed in Russian shelling.

| Service | What it returned |
|---|---|
| GDELT Cloud (Event) | *"Russian forces shell Lymanivka, killing a woman and injuring four."* Dated 22 Oct, Kharkiv Oblast, actors Russian forces → civilians, linked to a Story built from Ukrainian-language reports |
| GDELT Project | None judged specific |
| AI web search A, B and C | None |

Reviewer: *"Lymanivka Oct 22 woman killed 4 hurt; one day later than reference, plausible same."*

## 3. A record Cloud had, but its place filters missed

**Reference (UCDP):** 17 Oct 2026, Kherson. One killed.

- **The first pass missed it.** Cloud's country, radius and category filters found no Cloud Event for this incident.
- **The recheck found it.** Searching for the place, and matching on either actor's country, returned a Cloud Story: *"Russian forces strike Kherson, Ukraine, with eight aerial bombs"* (17 Oct, from Russian- and Ukrainian-language reports). Its place is coded only to "Ukraine", which is why the radius filter missed it.
- **Others had it too.** GDELT Project: `RUSSIAN → Employ aerial weapons → GOVERNOR at Kherson`, from arabnews.com. AI web search C returned a matching report when asked the long question, though not with its keyword query, and the records extracted from web search A's results included it.

Across all 604 conflict incidents, the place filters found 265. A second look at the candidates the same calls returned, and a recheck of the incidents only web search had found, added 47, for 312 (`cloud_filters` and `cloud_monitor` in `results/occurrences.csv`).

## 4. Web search has it, Cloud does not

**Reference (UCDP):** 30 Oct 2026, Ka Nyin Chaung village, Tanintharyi, Myanmar. Four civilians killed in airstrikes.

| Service | What it returned |
|---|---|
| AI web search A | A specialist human-rights monitor's report of four civilians killed in airstrikes on flood-affected villages in Thayetchaung Township (2 Nov) |
| AI web search B | A report the reviewer matched to this incident |
| Web search A + LLM, B + LLM | A record: junta airstrikes on two villages, four civilians killed. Tanintharyi, Thayetchaung Township |
| GDELT Cloud | None, after every route |
| GDELT Project | None |

The source is a specialist monitor that is not in the GDELT article stream. GDELT Cloud's conflict misses are spread across many countries; the largest counts are in Pakistan (31 of 46), Colombia (21 of 38) and Burkina Faso (15 of 15).

## 5. A WHO outbreak notice: web search finds the notice, Cloud has no record

**Reference (WHO Disease Outbreak News):** 6 Nov 2026, yellow fever, WHO African Region.

| Service | What it returned |
|---|---|
| AI web search A | A copy of the WHO notice on a humanitarian news site |
| AI web search B | A report the reviewer matched to this notice |
| Web search A + LLM, B + LLM | A record of continuing yellow fever transmission in the WHO African Region |
| GDELT Cloud | None |

Cloud covers the other four notices. Ebola in DR Congo, Kenya and Nigeria has Stories and Events. Shamonda in France, MERS in Qatar and chikungunya in Switzerland are Stories only (for example *"Switzerland reports four locally acquired chikungunya cases in Ticino"*). Weak spots are a regional agency notice with little press pickup, and a health development that becomes a Story but not an Event.

## 6. An election: everyone has it; the difference is the record

**Reference:** 7 Nov 2026, New Zealand general election.

| Service | What it returned |
|---|---|
| GDELT Cloud | A Story, *"New Zealand election ends in near-deadlock, with coalition talks ahead"* (2 days of coverage, linked Events), plus Events for individual seat results |
| AI web search A | A wire report of the preliminary count |
| AI web search B | A report the reviewer matched to this election |
| Web search A + LLM, B + LLM | A record: the general election was held; preliminary counts put the two main parties nearly level |

For a scheduled national event, recall is not the differentiator. Cloud returns it as a typed, dated record with actors and links, inside the same feed as every other category.

## 7. "Every protest in India, 9–15 November": one search against one list

| | GDELT Cloud | AI web search A, top 10 |
|---|---|---|
| What came back | 89 Protest Events, each with a date, a place and the acting group. Examples: *Ladakh Police escort Sonam Wangchuk from protest site*; *Ratlam Police use water cannons and arrest Karni Sena marchers*; *Assam Police halt Adi Galo Welfare Society anti-dam march* | 10 results: 3 distinct protests, the other 7 tracker pages, topic pages, an out-of-date call to mobilise, or duplicates |
| Overlap | Holds all 3 of the web protests (the Bengaluru groups' rally, the Thiruvananthapuram hunger strike, Wangchuk in Ladakh) | Returned 0 of the 10 sampled Cloud protests |

All 10 sampled Cloud protests in this cell fit the category. Across 40 cells, Cloud's lists held 28% of what web search A verified and 24% of what web search B verified. The two web searches returned 8% of what Cloud listed.

## 8. An ordinary business development, asked without its name

**Reference (Wikipedia Current Events, Business and economy):** 9 Nov 2026. South Korea's Fair Trade Commission fines Woowa Brothers (Baemin) ₩331.1 billion and Coupang ₩300.8 billion.

| Service | What it returned |
|---|---|
| GDELT Cloud (Event) | *"South Korea's Competition Commission fines Baemin and Coupang."* Dated 9 Nov |
| AI web search A, B and C, asked for "business and economic developments in or affecting South Korea around November 9" | Other South Korean business news that day. None about the fines |

Asked this way, web search surfaces whatever ranks best that day. Cloud's category list for South Korea that day contains the specific development. Across the 10 business items, Cloud had 10, web search B 4, C 2 and A 1.
