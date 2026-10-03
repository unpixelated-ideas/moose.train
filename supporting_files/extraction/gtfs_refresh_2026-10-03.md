# Static GTFS refresh: October 3, 2026

All four configured products imported successfully. Latest recorded import time: 12:54 PM America/New_York. Source publication timestamps remain unverified.

| Product | Exported stop events | Latest service date |
|---|---:|---|
| Metro-North | 205989 | 2027-05-22 |
| Hartford Line | 266 | 2027-07-12 |
| Shore Line East | 386 | 2027-09-27 |
| Amtrak | 4160 | 2027-09-27 |

## MTA fall schedule check

The supplied [MTA notice](https://view.info.mta.org/?vawpToken=BLA5YYASHCBEPCEBXGJS35TXKM.120048) announces an October 4 fall schedule with New Haven Line inbound AM and outbound PM stopping-pattern changes. It does not list individual trains. Hudson, Harlem, and Hudson fall foliage service remain outside the configured scope.

Compared calendar-resolved Metro-North trains for Thursday October 1 and Monday October 5 in the refreshed export. Both are non-Friday weekdays. The new feed begins October 1, so a September date cannot be used as its baseline.

- Inbound train numbers 1211 and 1313 appear on October 5; 1213 is absent compared with October 1.
- Outbound 1548 adds Fairfield at 17:47 and Fairfield-Black Rock at 17:50. Export CSV rows 126561 and 126602.
- Outbound 1556 adds Fairfield at 18:33 and Fairfield-Black Rock at 18:38. Export CSV rows 130736 and 130777.
- 1546 drops South Norwalk, Rowayton, Darien, and Noroton Heights.
- 1554 drops South Norwalk, Rowayton, and Darien.
- 1848 changes its stops, including Stamford at 18:03 (CSV row 9677).
- Outbound train numbers 1446 and 1448 also appear on October 5.

Row numbers include the header and refer to this refresh's moose_train_schedule.csv. Source: mnr_gtfs_effective_2026-10-01_updated_2026-10-03.zip, from the configured official Metro-North feed. No PDF parsing or manual timetable overrides were used. This verifies concrete feed changes consistent with the notice, not an independent audit of every fall timetable change.

## Verification

- All four import metadata records report success.
- 21 importer unit tests passed.
- FAQ refresh time, coverage dates, and fall-schedule note updated in English, Korean, and Spanish.
