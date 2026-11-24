#!/usr/bin/env bash
# Template: a search adapter as a shell command. The runner pipes ONE JSON request into stdin and reads
# JSON results from stdout (schemas/search_request.schema.json -> schemas/search_results.schema.json).
#
#   python bench.py check-adapter --adapter "bash adapters/my_search.sh" --usd-per-call 0.005
#   python bench.py web --adapter "bash adapters/my_search.sh" --label my_search --usd-per-call 0.005 --max-usd 5
#
# Needs curl and python3 (used here only to reshape JSON; jq works just as well).
# TODO: set ENDPOINT, the key variable, and the two field mappings marked below.
set -euo pipefail
ENDPOINT="https://search.example.com/v1/search"
REQ="$(cat)"
BODY="$(printf '%s' "$REQ" | python3 -c '
import json, sys
r = json.load(sys.stdin)
# map the request onto your service parameters (use r["keyword_query"] if your service prefers keywords)
print(json.dumps({"q": r["query"], "from": r["start_date"], "to": r["end_date"], "limit": r.get("max_results", 10)}))')"
RESP="$(curl -sS --max-time 60 -H "Content-Type: application/json" -H "Authorization: Bearer ${SEARCH_API_KEY:?set SEARCH_API_KEY}" -d "$BODY" "$ENDPOINT")"
printf '%s' "$RESP" | python3 -c '
import json, sys
d = json.load(sys.stdin)
# map your service response fields onto url / title / published / excerpt
print(json.dumps({"results": [{"url": x.get("url"), "title": x.get("title"), "published": x.get("date"),
                               "excerpt": (x.get("snippet") or "")[:700]} for x in d.get("results", [])]}))'
