# Extraction Thread Handoff

## Current State

Extraction is handled by `supporting_files/extraction/extract_timetables.py`.

Current generated dataset:

- `moose_train_schedule.csv`
- `10,191` stop events
- Active PDFs: Hartford Line, Shore Line East, Metro-North New Haven Line, New Canaan Branch, Danbury Branch, Waterbury Branch
- Danbury Branch is present from `metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16.pdf`.

## Owned Responsibilities

This thread owns:

- PDF discovery and safe renaming.
- `moose_train_schedule.csv` regeneration.
- `supporting_files/extraction/extraction_summary.csv`.
- Station normalization and branch station IDs.
- Preserving `source_original_filename`, `source_pdf`, and `source_page`.
- Updating extraction docs when parser behavior changes.

## Current Extraction Rules

CSV rows are one train stop event per row.

Metro-North:

- Use visible-coordinate parsing with `pdfplumber`.
- Use train-number x positions as column anchors.
- Accept narrower visible train-number header rows for branch PDFs, where weekend tables may have only six columns.
- Preserve blank cells.
- Keep `Ar.` rows arrival-only and `Lv.` rows departure-only.
- Reject impossible time fragments.
- Classify branch PDFs by filename before generic PDF text.
- Refuse source PDF overwrite collisions.
- Filter branch-only stations out of the main New Haven Line extraction.

CTrail:

- Shore Line East service tables and New York connection tables are parsed separately.
- `SLE THRU` trips are stitched into one direct trip.
- Hartford Line partial connections use literal `unknown` for the missing time side.
- CTtransit is bus substitution, not Amtrak.

## Known Pitfalls

- Metro-North hidden text can claim the wrong branch.
- Branch PDFs can include links to other branches.
- Duplicate station/time rows can appear from overlapping PDF table layers.
- Same visible train number may need an internal `~1`, `~2` suffix to avoid trip collapse.
- Do not overwrite an existing normalized source PDF with a newly renamed PDF.

## First Checks To Run

```sh
/Users/fgbm27/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 supporting_files/extraction/extract_timetables.py
cat supporting_files/extraction/extraction_summary.csv
/Users/fgbm27/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import csv, re
rows = list(csv.DictReader(open("moose_train_schedule.csv")))
bad = [
    (r["train_number"], r["station_name"], f, r[f])
    for r in rows
    for f in ("arrival_time", "departure_time")
    if r[f] and r[f] != "unknown" and not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", r[f])
]
print(len(rows), "rows")
print(len(bad), "bad times")
PY
```

## References

- `supporting_files/reference/extraction_logic.md`
- `supporting_files/source_pdfs/README.md`
