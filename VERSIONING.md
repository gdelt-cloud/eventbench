# Versioning

- **The suite is a frozen snapshot.** Each release (`2026.11`, then the next) fixes its occurrence list, questions and judging rules. Results are always reported against a named snapshot.
- **References are rebuilt per window.** A new release draws new reference occurrences for a new time window from the same sources, with a published seed. Old windows stay as they were.
- **Old results are never re-scored silently.** If a judging rule or a reference list changes, the change gets a new version and a CHANGELOG entry, and earlier numbers stay reproducible from their own snapshot.
- **Services change.** Live services improve or regress between runs, so every result carries the run date.
- **A pooled share belongs to its run.** It is relative to the services in that run's pool. Across runs, compare ratios and reference-list recall ([METHOD.md](METHOD.md#comparing-runs)).
