# moose.train Project Snapshot

## Current State

`moose.train` is a local HTML prototype for comparing train route options across services from one normalized timetable CSV.

The project root must stay clean. It should contain only:

- `index.html`
- `moose_train_schedule.csv`
- `supporting_files/`

Current dataset status:

- `10,191` stop events
- `828` grouped trips in the prototype
- Source data is generated from PDFs in `supporting_files/source_pdfs/`

Current source PDFs represented in the CSV:

- CTrail Hartford Line
- CTrail Shore Line East
- Metro-North New Haven Line
- Metro-North New Canaan Branch
- Metro-North Danbury Branch
- Metro-North Waterbury Branch

Important caveat:

- Danbury Branch is currently represented from `metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16.pdf`.
- When source PDFs change, regenerate both `moose_train_schedule.csv` and the embedded CSV fallback in `index.html` so local-file search stays current.

## Owned Responsibilities

Use this snapshot thread as the project control tower:

- Track current files and known caveats.
- Decide which specialized thread should own new work.
- Keep source-of-truth docs current after major extraction, routing, or UI changes.
- Confirm the root folder rule after changes.

## Source-Of-Truth Files

- `supporting_files/source_pdfs/README.md`
- `supporting_files/extraction/extraction_summary.csv`
- `supporting_files/reference/extraction_logic.md`
- `supporting_files/reference/routing_logic.md`

## Known Pitfalls

- Metro-North PDFs have noisy hidden text layers and overlapping visible table fragments.
- Branch PDF filenames are more reliable than generic cover text because full-line PDFs can mention all branches in link sections.
- Do not let source PDF renaming overwrite another PDF.
- Do not regenerate `moose_train_schedule.csv` unless the extraction workstream intends it.

## First Checks To Run

```sh
find . -maxdepth 1 -mindepth 1 -print
cat supporting_files/extraction/extraction_summary.csv
cat supporting_files/source_pdfs/README.md
```
