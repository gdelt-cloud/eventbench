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

## Incident type (release 2026.11.1)

After the pool is judged, each distinct incident gets exactly one type, from its label and one report of it
(`judgments/pool/incident_types.csv`). *Armed conflict* is every type except `criminal_homicide`.

- `battle`: armed clash between organised armed forces or groups, including ambushes of troops, raids on
  military or police posts, and fighting between militias or gangs fighting as armed groups for territory.
- `remote_violence`: air or drone strike, shelling, artillery, missile or rocket attack, bombing, IED,
  landmine, unexploded ordnance, suicide bombing.
- `attack_on_civilians`: an armed group, militia, insurgents or state forces deliberately attacking,
  massacring, abducting and killing or assassinating civilians or named individuals for a political or
  armed-conflict purpose.
- `security_force_killing`: police or security forces kill people in an operation, raid, encounter, arrest or
  crowd control, outside battle with an armed group.
- `criminal_homicide`: ordinary crime: murder, femicide, domestic killing, robbery killing, gang or cartel
  killing framed as crime, contract killing, a killing by an unknown gunman with no stated armed-conflict link.
- `mob_or_riot`: mob violence, lynching, communal or ethnic clash between civilians, violent demonstration or riot.
- `other`: none of these.

Judge by what happened, from the label and the report.
