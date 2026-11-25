# Judging coded rows against their source article

You are an independent reviewer. Each ITEM is one coded event row, from one of several event-coding systems, and the
source article it was coded from. You are not told which system produced a row, and you should not try to guess.

The row reads `acting party -> action -> receiving party at place on date`. A `?` means the system named no party
there.

For each item:

1. Open the article URL (use WebFetch). If it fails, try once more. If it still does not load, or loads with no
   article text (a paywall, a cookie wall, an index page), set `source` to `unavailable` and move on. Do not look for
   the article anywhere else.
2. Judge the row against the article, the same test for every row:
   - `supported`: the article reports that party doing that kind of action to that party, with the place and date
     roughly right (the place at the precision the row gives; the date within a few days of what the article reports).
     A `?` is not wrong by itself, but a row whose only content is an action the article does not report is not
     supported.
   - `partial`: the article reports that kind of action, but a named party, the place or the date is wrong.
   - `unsupported`: the article does not report that kind of action (including a row coded from a metaphor, an
     accident, a historical mention, a threat or a denial as if the act happened), or it is materially wrong.
3. `lethal`: `yes` if the article reports anyone killed in the act the row describes, else `no`.

Write a JSON file (the path is in your task), one entry per item:

```json
{"R001": {"source": "ok", "verdict": "supported", "lethal": "yes", "note": "<= 20 words"}}
```

Include every item in your batch. Reply with one line of counts.
