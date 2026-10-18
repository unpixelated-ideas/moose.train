# October 7 refresh and weekend exceptions

All four imports succeeded, ending at 17:44 Eastern. The exported schedule contains 199481 stop events. Coverage: Metro-North through 2027-05-22; Hartford through 2027-07-12; Shore Line East and Amtrak through 2027-10-04.

## Unresolved East Norwalk conflict

The user's MTA notice states East Norwalk is closed through October 18. The new Metro-North feed still exports these stops:

| Service date | Train | GTFS time | Actual local time | Schedule CSV row |
|---|---|---|---|---:|
| 2026-10-10 | 6546 | 18:14 | October 10, 18:14 | 180857 |
| 2026-10-10 | 6573 | 24:30 | October 11, 00:30 | 187020 |
| 2026-10-11 | 6573 | 24:30 | October 12, 00:30 | 187021 |
| 2026-10-17 | 6534 | 15:14 | October 17, 15:14 | 178186 |

Source: mnr_gtfs_effective_2026-10-05_updated_2026-10-07.zip. CSV row numbers include the header and refer to this refresh. Each row's raw_notes provides its source GTFS trip and service IDs. No manual closure override has been applied. The feed has no East Norwalk service-day stops on October 18; October 19 has 58.

## Waterbury and New Haven weekend service

Waterbury has 24 replacement-bus trips serving Waterbury on each checked service date: October 10, 11, and 17. Sample October 10 times remain unchanged from the October 3 import:

- EB6906: Bridgeport 08:49 to Waterbury 09:41; CSV rows 196891 and 196939.
- LB6906: Bridgeport 08:49 to Waterbury 10:06; CSV rows 196892 and 197083.
- EB6913: Waterbury 06:38 to Bridgeport 07:30; CSV rows 197107 and 197155.

Replacement-bus presence does not independently verify the announced special bus timetable. The supplied notice has no individual departures to reconcile. Exact New Haven service-reduction cutoff coverage (17:15 October 10/11; 14:45 October 17) likewise remains unverified. Do not interpret this refresh as complete reconciliation of the notice.

## Checks

21 importer tests passed. FAQ refresh details and an explicit exception warning were updated in English, Korean, and Spanish. Source data was refreshed without inventing replacement times or silently removing disputed stops.
