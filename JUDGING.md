# Judging instructions

You are an independent reviewer. Each `OCCURRENCE` below is a real-world occurrence taken from a reference list that none of the tested services produced: an academic conflict dataset, a monitoring group's list, or an official catalog. Under it is a shuffled list of candidate records from several unnamed sources. Records come in different styles (structured summaries, story headlines, coded rows with a source URL, search results, extracted notes). Judge only what a record says. Do not try to work out which source it came from.

For every occurrence, list the candidate records that describe it.

- **S (specific):** the record is about this same occurrence. That means the same attack, clash, killing, election, rate decision, outbreak notice or disaster. The place must be consistent at the reference's own precision. The date must be within 2 days (reports often lag by a day). Actors and victims must be consistent. Counts may differ.
- **A (aggregate):** the record is a roundup covering several occurrences, and it explicitly names this place on this date.
- **Leave out everything else.** That includes the same conflict on another day, another town in the same province, a preview or forecast of a scheduled event that does not report its outcome, and generic commentary.
- **Coded rows judged only by a URL:** use S or A only when the URL text itself clearly identifies the occurrence.
- **Be strict and consistent.** When unsure, leave the record out.

Write one JSON file per packet:

```json
{"<occurrence uid>": {"S": ["R00012"], "A": [], "note": "at most 25 words on the hardest call"}}
```

Include every occurrence uid, even when both lists are empty. Read every line; do not search by keyword, because records use other spellings and languages.
