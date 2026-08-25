# Source PDFs

This folder stores the source timetable PDFs used to build `moose_train_schedule.csv`.

Current files:

- `ctrail_hartford_line_effective_2026-06-22_updated_2026-06-09.pdf`
  - Original uploaded filename: `6-22.pdf`
  - Notes: includes Hartford Line trains, CTtransit bus substitution columns, and provisional New Haven connection stubs with `unknown` for missing endpoint times.
- `ctrail_shore_line_east_effective_2026-03-29_updated_2026-03-17.pdf`
  - Original uploaded filename: `SLE-3_29-MNR-Schedule-Change.pdf`
  - Notes: includes Shore Line East trains, Metro-North New York connection tables, and SLE through-train handling.
- `metro_north_new_haven_line_effective_2026-03-29_revised_2026-04-11_updated_2026-04-08.pdf`
  - Original uploaded filename: `04-07-26_NHL+Branches-Sched_v3.pdf`
  - Notes: parsed with coordinate-based extraction because blank cells, `Ar.`/`Lv.` rows, and dense table columns are not safe to parse from plain text alone.
- `metro_north_new_canaan_branch_effective_2026-03-29_updated_2026-03-16.pdf`
  - Original uploaded filename: `03-29-26_NHL-NC-Sched_v2.pdf`
  - Notes: includes New Canaan Branch service between New Canaan, Talmadge Hill, Springdale, Glenbrook, Stamford, Harlem-125th St., and Grand Central. Parsed with visible-coordinate Metro-North logic.
- `metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16.pdf`
  - Original uploaded filename: `03-29-26_NHL-DB-Sched_v2.pdf`
  - Notes: includes Danbury Branch service between Danbury, Bethel, Redding, Branchville, Cannondale, Wilton, Merritt 7, South Norwalk, Stamford, and Grand Central. Parsed with visible-coordinate Metro-North logic.
- `metro_north_waterbury_branch_effective_2026-03-29_updated_2026-03-16.pdf`
  - Original uploaded filename: `03-29-26_NHL-WB-Sched_v2.pdf`
  - Notes: includes Waterbury Branch service between Waterbury, Naugatuck, Beacon Falls, Seymour, Ansonia, Derby-Shelton, Stratford, Bridgeport, Stamford, Harlem-125th St., and Grand Central. Parsed with visible-coordinate Metro-North logic.

PDFs may be renamed after extraction so their filenames describe the service and best-derived timetable dates. The CSV preserves the uploaded filename in `source_original_filename`; each stop event also includes `source_pdf` and `source_page` for traceability.

To refresh the CSV after adding or replacing PDFs, run:

```sh
/Users/fgbm27/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 supporting_files/extraction/extract_timetables.py
```

After each run, review:

- `supporting_files/extraction/extraction_summary.csv`
- `supporting_files/reference/extraction_logic.md`
- `supporting_files/reference/routing_logic.md`
