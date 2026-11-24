# Data licence

The code in this repository is MIT-licensed (see `LICENSE`). The data is licensed separately.

| What | Licence |
|---|---|
| Our results (`results/`), judgments (`judgments/`), question set (`suite/questions.csv`, `suite/cells.csv`) and documentation | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit "GDELT Cloud EventBench". |
| UCDP Candidate Events rows in `suite/` | Uppsala Conflict Data Program, CC BY 4.0. Cite UCDP. |
| Wikipedia Current Events items in `suite/` and `references/` | CC BY-SA 4.0. Each item links to its day's page. |
| USGS earthquake catalog rows | Public domain. |
| Indepaz, SATP, WHO, GDACS, election calendar and central-bank rate items | Facts with a link to the source only. No text is copied beyond a one-line description. |
| GDELT Project 2.0 rows referenced in `judgments/` | GDELT Project open data terms. |

Raw responses from the tested web search services are not included and are never committed (`run/` and `runs/` are ignored). To compare any web search service yourself, plug it in through an adapter (see `AGENTS.md`); its responses stay in your local `run/` folder.
