# Metro-North Fare Data

moose.train stores Metro-North fares as local structured data in `index.html`, separate from the fare lookup functions. The current MVP returns standard adult one-way fares only.

## Sources

- MTA LIRR and Metro-North fares page: https://www.mta.info/fares-tolls/lirr-metro-north
- Metro-North Harlem and Hudson Line fares to/from Grand Central/Harlem-125th Street: https://www.mta.info/document/194931
- Metro-North New Haven Line fares to/from Grand Central/Harlem-125th Street: https://www.mta.info/document/194941
- Metro-North Harlem and Hudson intermediate fares: https://www.mta.info/document/194936
- Metro-North New Haven Line intermediate fares: https://www.mta.info/document/194946

## Data Currency

- Fare schedule effective date represented in local data: July 1, 2026
- Local fare data last updated: September 1, 2026

## Current Coverage

- Supported passenger category: `ADULT`
- Supported Metro-North station coverage in the app: New Haven Line main line, New Canaan Branch, Danbury Branch, and Waterbury Branch stations currently present in `stationIndex`
- Supported ticket products: standard one-way fare and CityTicket
- Peak/off-peak source: Metro-North `peak_offpeak` values imported from the official GTFS-derived schedule rows

Intermediate Metro-North trips outside Manhattan use the MTA-published intermediate one-way matrix. Per the MTA railroad fares page, Metro-North intermediate tickets are the same fare on all trains for travel outside Manhattan; moose.train preserves the train peak/off-peak classification in the structured fare result, but does not manufacture a separate intermediate peak fare.

## Known Gaps

- Amtrak and CTrail fares are not calculated.
- Discounted Metro-North fares are not calculated yet.
- Yankee Stadium special event fares are not calculated.
- Harlem Line and Hudson Line station IDs are not currently in the app schedule search dataset, although the official source documents are identified above for future expansion.
