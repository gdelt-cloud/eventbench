# Judging instructions: taxonomy cells

Each CELL is one kind of occurrence, in one country, in one week. It has three parts: the top 10 results of one web search, the complete list returned by a structured service, and a random sample of that list.

**A. Web results.** Judge each W#.
- `in_cell`: yes if it reports a real, specific occurrence of the cell's kind, in that country, inside the dates. Answer no for background, list or roundup pages, forecasts, other dates, other countries or other kinds.
- `group`: for in-cell results, give results about the same occurrence the same letter.
- `cloud_match`: the id from the full list that is the same occurrence, or null after checking the whole list.

**B. Sampled records.** Judge each S#.
- `fits`: yes if its title is plausibly an occurrence of the cell's kind, in that country.
- `in_web`: the W# reporting the same occurrence, or null.

Write JSON in this shape:

```json
{"<cell>": {"web": {"W1": {"in_cell": "yes", "group": "A", "cloud_match": "cameoplus_..."}},
            "sample": {"S1": {"fits": "yes", "in_web": null}}}}
```
