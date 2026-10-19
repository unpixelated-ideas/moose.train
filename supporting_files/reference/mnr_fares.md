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
- Local fare data last checked/updated: October 19, 2026
- Hudson/Harlem fare tables: January 4, 2026; existing New Haven table effective date remains July 1, 2026.

## Current Coverage

- Supported passenger category: `ADULT`
- Supported Metro-North station coverage in the app: Hudson Line through Poughkeepsie, Harlem Line through Wassaic, New Haven Line main line, and New Canaan, Danbury, and Waterbury branches
- Supported ticket products: standard one-way fare and CityTicket
- Peak/off-peak source: Metro-North `peak_offpeak` values imported from the official GTFS-derived schedule rows

Intermediate Metro-North trips outside Manhattan use the MTA-published intermediate one-way matrix. Per the MTA railroad fares page, Metro-North intermediate tickets are the same fare on all trains for travel outside Manhattan; moose.train preserves the train peak/off-peak classification in the structured fare result, but does not manufacture a separate intermediate peak fare.

## Known Gaps

- Amtrak fares are not calculated outside the separate eligible Hartford Line ticketing rules; CTrail uses its own fare tables.
- Discounted Metro-North fares are not calculated yet.
- Yankee Stadium special event fares are not calculated.
- Yankees–E. 153rd Street remains searchable but all calculated fares to/from that station are withheld because event fare rules are outside this release.

## Connections

Same-direction Metro-North transfers use one endpoint fare when represented in the official matrix. For a terminal journey with an off-peak shuttle connection, the terminal-serving train determines the peak/off-peak fare. Direction-changing journeys at Harlem-125th, Fordham, or Grand Central sum two leg tickets and display “Separate tickets”; they never receive one through CityTicket. Other reversals without a verified rule remain unpriced. Unknown direction or missing peak classification does not produce a guessed fare. Fordham uses New Haven zone 11 or Hudson/Harlem zone 2 according to the destination fare family. Cross-family intermediate pairs without a published matrix are not inferred. Amtrak combinations never display a partial Metro-North cost as a total.
