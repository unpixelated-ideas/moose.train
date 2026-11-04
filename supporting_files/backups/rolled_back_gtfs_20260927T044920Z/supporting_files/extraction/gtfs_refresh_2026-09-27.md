# GTFS refresh — September 27, 2026

All four imports succeeded, as verified in `gtfs_import_metadata.csv`. Recorded import times are September 27, 2026, 00:24:14–00:25:22 EDT (America/New_York). The standard importer ran with the bundled Python runtime; no importer or application logic changed, and no PDFs were parsed. Initial sandbox DNS failures left the schedule intact; the authorized network retry succeeded.

## Coverage and counts

These are resolved service-calendar bounds, not a guarantee that every trip operates throughout the range.

| Service | Import time (EDT) | Calendar coverage | Stop-event rows before → after |
|---|---|---|---|
| Metro-North | 00:24:14 | 2026-09-09 – 2027-05-22 | 264,306 → 266,324 |
| CTrail Hartford Line | 00:25:18 | 2026-07-11 – 2027-07-12 | 266 → 266 |
| CTrail Shore Line East | 00:25:20 | 2026-09-20 – 2027-09-20 | 429 → 429 |
| Amtrak | 00:25:22 | 2026-09-20 – 2027-09-20 | 4,130 → 4,245 |

All latest coverage dates are unchanged. The shared Amtrak/Shore Line East feed declares feed_start_date=20260927, feed_end_date=20261003 and feed_version=20260926. These differ from the longer service calendars. The version is not independent evidence of a publication date. Provider publication dates remain unverified for every service; download times and file modification times are not publication dates.

## Significant differences

Comparison unions operating dates for each train/station/arrival/departure tuple, avoiding inflated differences from GTFS trip ID changes or duplicate rows. Future comparisons begin September 27, 2026.

- Metro-North: 11 train numbers have future stop-event or calendar changes. September 27 special-service assignments change: 7322, 7325, 7520, 7526 and 7527 gain service; 7338, 7341, 7343, 7536 and 7542 lose that date in this feed. Train 1849's Stamford time changes from 10:12 to 10:22 on affected dates beginning September 28. These are feed differences, not live cancellation notices.
- Amtrak: 24 train numbers have future stop-event or calendar changes, including 19 with changed time/stop patterns across the full import. For example, on affected dates beginning October 12, train 1088's New Haven departure moves from 16:47 to 17:00; train 1150's New Haven departure moves from 08:38 to 09:01. Train variants 1152 and 1169 disappear from this import. Other variants gain dates; this does not establish a net loss of passenger service.
- Hartford Line and Shore Line East: no future operating-date, station or time differences. Shore Line East's October expansion remains represented. The FAQ no longer implies every previously listed train first begins October 5: train 1640 also has earlier service.

## Verification

- All four metadata rows report success=true and empty errors; shared physical feed retained.
- Regenerated schedule contains 271,264 stop-event rows across all four services.
- 21 extraction tests passed, including calendar additions/removals, after-midnight times, shared sources, scope and exclusions.
- Actual output route filters and Amtrak minimum-two-supported-stations/geography verified; non-public Metro-North stop 651 remains excluded (47 source stop events).
- All schedule calendar summaries match resolutions from the official calendars and exceptions. Normalized stop times match the source exactly. After-midnight rows: Metro-North 6,401; Shore Line East 6; Amtrak 105.
- Canonical station mappings and names match the prior import; importer and duplicate-reconciliation logic unchanged.
- English, Korean and Spanish FAQ and refresh labels updated. FAQ's existing content loader successfully extracts all three languages; inline JavaScript syntax checked. Historical release content unchanged.
- Nothing deployed or published.

## Recovery

Pre-refresh metadata, schedule, normalized data, source CSVs, original GTFS sources and index.html are preserved at:

supporting_files/backups/gtfs_refresh_20260927T042355Z

The backup manifest records its creation time and original schedule SHA-256. Restore the corresponding files from this directory to recover the previous import.
