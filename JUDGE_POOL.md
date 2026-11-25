# Judging the pooled truth

Each packet holds every record that several unnamed sources returned to ONE monitoring question, plus the
reference incidents for that question, shuffled, with the sources hidden:

> People killed in attacks, clashes or violence in {COUNTRY}, from {START} to {END}.

For every record decide two things.

**on_topic**: "yes" only if the record reports a specific violent incident (an attack, armed clash,
airstrike or drone strike, shelling, bombing, shooting, killing, massacre or a criminal homicide) in which
at least one person was killed, that took place in {COUNTRY}, on a date from {START} to {END}. A report
published up to {TAIL} days after {END} about such an incident counts. Judge by the incident the record
describes, not by when it was published.

Answer "no" for: an incident in another country (including strikes by {COUNTRY}'s forces elsewhere); an
incident outside the dates; an incident with no death; general news, statements, politics, analysis or
statistics; an overview or roundup that does not single out one incident; a page that is not news. When
you are unsure, answer "no".

**incident**: for on-topic records only, a short label in the form "place · date · what happened", for
example "Lymanivka, Kharkiv · 21 Oct · Russian strike kills 1". Give the SAME label to every record that
describes the same incident: the same act, at the same place, at the same time. Different incidents get
different labels, however similar. If a record reports several specific incidents, label the one it
reports in most detail. Some records are short reference descriptions ("Government of X vs Y; deaths 1",
a place and a date): label them like any other record, so they share a label with the records that report
the same incident.

**Before you finish**, read your list of labels once more and merge any two that name the same incident
(the same act, place and time, written differently), so each incident has exactly one label.

Output one JSON object keyed by record id, with every record in the packet included:

```json
{"R0001": {"on_topic": "yes", "incident": "Lymanivka, Kharkiv · 21 Oct · Russian strike kills 1"},
 "R0002": {"on_topic": "no", "incident": null}}
```
