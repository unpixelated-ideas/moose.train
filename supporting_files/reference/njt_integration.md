# NJ Transit integration

## Implemented coverage

The normal schedule build includes NJ Transit commuter rail stops in New York and
New Jersey, including the Princeton Shuttle and Meadowlands trains when scheduled.
Main/Bergen local trains and Port Jervis trains remain separate services. Search
and the departure board use the same schedule. PATH, light rail, buses, passes,
discounted fares, and NJ Transit live updates are outside this release.

All operators retain the same maximum of one transfer. Secaucus, Newark Penn,
and Trenton are allowed hubs alongside existing hubs. Penn Station retains its
20-minute minimum, Grand Central 15 minutes, and the other hubs the existing
5-minute minimum. Two-transfer journeys through both Secaucus and Penn remain
unsupported; no service-specific exception was added.

Station IDs are explicit in `njt_stations.json`. Both Secaucus levels share `SEC`
while retaining distinct source stop IDs. New York Penn (`NYP`) and Newark Penn
(`NWK`) remain separate. Shared Amtrak IDs are `NWK`, `EWR`, `MET`, `PJC`, and `TRE`.
Other NJ Transit stations have namespaced IDs to avoid collisions.

## Schedule source and exceptions

The official public source is <https://www.njtransit.com/rail_data.zip>. It needs
no developer credentials, paid API, or backend. Import the configured commuter
rail routes and keep Philadelphia 30th Street outside the search area. NJ Transit
uses `block_id` for its published train number.
Original trip, route, stop, and service IDs remain traceable in normalized data
and the browser's prepared trips.

The saved November 18, 2026 snapshot includes 163 canonical NJ Transit stations in
the expanded scope. Its calendar is supplied through `calendar_dates.txt`.
The archive has no fare tables or transfer minimums.

Port Jervis `PJBUS` and Gladstone `GBUS` itineraries are excluded in full because
the source labels these replacement buses as rail trips.
Unknown nonnumeric train markers, unmapped/reassigned stop IDs, missing lines,
and expired coverage fail validation instead of being published.

The [Portal Bridge temporary schedules](https://www.njtransit.com/portalcutover)
and [September 17 notice](https://www.njtransit.com/press-releases/portal-north-bridge-enters-final-phase-construction-work-begins-put-final-track)
cover October 11–November 14 modifications. The feed contains date-dependent
changes; valid calendar dates alone do not prove operational accuracy. The FAQ
explains the rail-only scope and deferred live updates.

## Adult one-way fares

`build_njt_fares.py` requests an explicit weekday service date from NJ Transit's
public website GraphQL endpoint, using the reviewed station titles rather than
GTFS IDs. Requests are read-only, paced, and limited to two concurrent batches;
transient HTTP/network failures have bounded retries. This is an undocumented
website interface and may change.

The dated October 20, 2026 audit returned usable responses for 3,848 of 3,906
directed station pairs. The compiler publishes 3,802 prices and withholds 104
because a response is missing, the reverse price differs, or applicability does
not agree. It never fills missing data by reversing a fare, choosing a cheaper
quote, or adding leg prices. A disagreement is not proof of a source error;
it means the price needs further validation.

Core journeys in the verified fare snapshot must have corroborated prices in both
directions or the build fails, preserving the previous deployed site. Other
unverified prices display a localized “Fare unavailable”. Both directions are
stored explicitly. North Elizabeth–Rahway is a known withheld pair; the dated
source lists direct trains but returns $2.65 in one direction and $6.05 in reverse.

The browser uses one origin/destination through fare for eligible NJ Transit
connections, rather than summing two tickets. At Secaucus, only the reviewed
Northeast Corridor ↔ Port Jervis/Pascack Valley pattern is priced. Unreviewed
West of Hudson-to-West of Hudson transfer patterns remain unpriced. Other
same-corridor changes retain the origin/destination fare. Source restrictions
requiring travel via Secaucus are preserved. Mixed-operator prices are totaled
only when every component is known; Amtrak fare links remain available.

Fare details show the date checked, through-ticket information, and AirTrain
access inclusion for NJ Transit airport tickets. The checked date is not labeled
an effective date. Airport arrival times refer to the rail station, not a terminal.
The browser withholds snapshots older than 30 days. A missing fare script leaves
schedule search usable, with NJ Transit prices unavailable.

`supporting_files/assets/njt_fares.json` is the reviewable snapshot. Its matching
JavaScript asset is loaded before the application, with a content-hash version
in `index.html`. Browsers contact only the static site for NJ Transit data.
Historical source experiments remain in `njt_fare_audit.json` and
`njt_fare_samples.json`; they are not the current production snapshot.

## Build, validation, and free hosting

The normal public-repository GitHub Actions workflow downloads all six GTFS
products, validates current coverage of every NJ Transit and Metro-North line,
prepares fares, updates refresh labels, builds compact search assets, and runs
checks before deploying to GitHub Pages. Failure prevents deployment. The
existing public-runner guard remains; no paid hosting, credentials, or separate
service is introduced. Raw feeds and staging data are excluded from Pages.

For a local rebuild from saved official ZIPs:

```sh
python3 supporting_files/extraction/extract_timetables.py --no-download
python3 supporting_files/extraction/build_njt_fares.py --from-report supporting_files/staging/njt-fares-dated-2026-10-20.json
python3 supporting_files/scripts/validate_refresh.py
python3 supporting_files/scripts/update_refresh_labels.py
node supporting_files/scripts/build_search_schedule.js
node supporting_files/scripts/build_search_schedule.js --check
node supporting_files/tests/njt.test.js
```

Omit `--from-report` to collect a fresh dated fare snapshot. The saved audit is
local staging material and is not required by CI. Standard tests also cover
calendar-only feeds, overnight times, bus exclusions, cross-operator station
identities, fare applicability, partial-provider failure, stale prices, and the
uniform transfer ceiling. Browser checks cover three languages, desktop/mobile
layouts, tooltip placement, through fares, and a blocked fare script.

`prepare_njt.py` and `audit_njt_routes.js` remain available for isolated source
investigations. Staging never replaces published metadata or schedule assets.
The optional manual audit workflow produces a job summary without uploading
additional artifacts or deploying.
