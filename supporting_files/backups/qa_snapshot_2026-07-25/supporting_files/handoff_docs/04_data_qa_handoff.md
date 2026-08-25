# Data QA Thread Handoff

## Current State

The current CSV has:

- `10,191` stop events
- `828` trips in the prototype
- Active services: Hartford Line, Shore Line East, New Haven Line, New Canaan Branch, Danbury Branch, Waterbury Branch, partial Amtrak/MNR/SLE connection rows, CTtransit bus substitution

Danbury Branch is currently represented from `metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16.pdf`.

## Owned Responsibilities

This thread owns:

- Regression checks after extraction changes.
- Spot checks against source PDFs.
- Invalid-time scans.
- Duplicate/phantom station checks.
- Route sanity examples.
- Source traceability checks.

## Core QA Checks

Run after every extraction:

- Count rows by service.
- Scan for invalid times.
- Verify `unknown` appears only for partial connection rows.
- Confirm source PDFs/pages are populated.
- Confirm branch-only stations do not leak into main New Haven Line rows.
- Confirm branch services have sensible station order.
- Confirm duplicate source PDFs were not created by renaming.

## Key Fixtures

Preserve known fixtures:

- Metro-North 1507 weekday inbound: New Haven `04:28` to Grand Central `06:30`, Stamford departure-only `05:37`, Harlem `D` note at `06:17`.
- Shore Line East New Haven to Old Saybrook should show direct trips, not forced transfers.
- Grand Central to Old Saybrook should use the first valid Shore Line East onward connection at New Haven.
- Hartford Line New Haven to Hartford should prefer direct Hartford Line service over New Haven-State Street transfer tricks.
- New Canaan Branch should route Grand Central to New Canaan as direct when a branch trip exists.
- Danbury Branch should route Danbury to Grand Central when a direct branch trip exists.
- Waterbury Branch should route Waterbury to Grand Central with sensible transfer behavior.

## First Checks To Run

```sh
/Users/fgbm27/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import csv, re
from collections import Counter
rows = list(csv.DictReader(open("moose_train_schedule.csv")))
print("rows", len(rows))
print(Counter(r["service_name"] for r in rows))
bad = [
    r for r in rows
    for f in ("arrival_time", "departure_time")
    if r[f] and r[f] != "unknown" and not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", r[f])
]
print("bad times", len(bad))
branch_only = {
    "New Canaan", "Talmadge Hill", "Springdale", "Glenbrook",
    "Danbury", "Bethel", "Redding", "Branchville", "Cannondale", "Wilton", "Merritt 7",
    "Waterbury", "Naugatuck", "Beacon Falls", "Seymour", "Ansonia", "Derby-Shelton",
}
leaks = [r for r in rows if r["service_name"] == "New Haven Line" and r["station_name"] in branch_only]
print("main-line branch leaks", len(leaks))
PY
```

## References

- `supporting_files/extraction/extraction_summary.csv`
- `supporting_files/reference/extraction_logic.md`
- `supporting_files/reference/routing_logic.md`
