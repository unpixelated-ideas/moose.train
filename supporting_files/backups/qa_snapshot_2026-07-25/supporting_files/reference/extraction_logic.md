# Extraction Logic Notes

This document records extraction rules that protect timetable accuracy as future PDFs are added.

## Preserve Table Column Positions

When extracting timetable PDFs, train numbers and times must be mapped by their actual table column positions, not only by left-to-right order.

Reason:

Some timetable rows contain blank cells. If those blanks are collapsed, a time from one train can be assigned to the neighboring train.

Example:

- Shore Line East weekend service to New London has late-day columns for Train 3644 and Train 3652.
- A loose train-number regex included leading whitespace in the train column position.
- That made the 7:25 PM Train 3644 departure appear closest to Train 3652.
- Result: Train 3652 incorrectly received both the 7:25 PM and 10:25 PM trips.

Required behavior:

- Record train-number column positions from the actual start of the train number, not surrounding whitespace.
- Preserve blank timetable cells.
- Validate sparse end-of-day columns where missing cells are common.
- Spot-check the first and last trains in each timetable section after extraction.

## Current Safeguard

`supporting_files/extraction/extract_timetables.py` uses a stricter CTrail train-number regex so leading whitespace is not counted as part of the train column position.

## Parse Metro-North By Visible Coordinates

Metro-North New Haven Line PDFs use dense landscape tables with many blank cells, separate `Ar.`/`Lv.` rows, and some transformed duplicate text outside or over the visible page area. Plain text extraction is not safe for these tables.

Required behavior:

- Use visible PDF word coordinates, bounded to the page box.
- Treat train-number x-positions as column anchors.
- Allow narrower branch timetable header rows; weekend branch tables may have only six train columns.
- Assign each station-row time only to the nearest aligned train-number column.
- Preserve blank cells; do not slide a neighboring train's time into the blank.
- Reject impossible time fragments where the hour is outside `1-12` or the minute is outside `00-59`.
- Keep `Ar.` rows as arrival-only and `Lv.` rows as departure-only.
- Preserve note letters such as `D` in `raw_notes`.

QA fixture:

- Weekday inbound Metro-North 1507 must parse as one `TO NEW YORK` trip from New Haven `04:28` to Grand Central `06:30`.
- Stamford must be `departure_time=05:37` with no arrival time.
- Harlem-125th St. must preserve the `D` note at `06:17`.

Current safeguard:

- `extract_timetables.py` uses `pdfplumber` coordinate extraction for Metro-North and validates the 1507 fixture after regeneration.
- The revised 2026-04-11 New Haven Line PDF exposes the Monday-Friday inbound AM Peak & Mornings continuation table as an overlaid `PlacedPDF` text layer. The visual continuation columns after train 1231 cannot be separated from duplicate hidden columns by font, color, or coordinate alone. `extract_timetables.py` therefore applies an explicit source-page-2 fixture for confirmed main-line continuation trains, while excluding branch-only/branch-connection columns such as 1735, 1841, and slash branch connections.

## Preserve Metro-North Service Exceptions

Some Metro-North trains on the main New Haven Line carry column-specific service exceptions that are narrower than the page-level service period.

Required behavior:

- Preserve train-level service restrictions separately from the page-level weekday/weekend label.
- Exact `service_dates` should act as additional service dates, not as a replacement for the recurring `service_days` pattern.

Example:

- Main New Haven Line train 3419 operates Fridays and also on July 2, 2026. It should use `service_days=friday` and `service_dates=2026-07-02`.
- Main New Haven Line trains 1419, 1417, and 1427 operate Monday-Thursday, but do not operate on July 2, 2026. Use `service_days=monday_through_thursday` and preserve `Does not operate 2026-07-02` in `raw_notes`.
- Main New Haven Line trains 3539 and 3541 follow the same Friday plus July 2, 2026 exception pattern as 3419.
- Main New Haven Line trains 1437, 1537, and 1539 follow the same Monday-Thursday excluding July 2, 2026 pattern as 1417/1419/1427.

Current safeguard:

- `extract_timetables.py` applies known Metro-North service exceptions after extraction and before source CSV snapshots are written.
- The prototype treats exact `service_dates` as additive exceptions and honors `Does not operate YYYY-MM-DD` notes when evaluating whether a trip runs on a selected date.

## Preserve Published Connection Tables

Some CTrail timetables include connection tables above or below the main service table.

Required behavior:

- Extract published connection tables when they provide usable upstream or downstream train times.
- Keep the connecting agency/service distinct from the main timetable agency/service.
- For Shore Line East, `CONNECTIONS FROM NEW YORK (ARRIVING)` rows are Metro-North New Haven Line rows, not Shore Line East rows.
- Preserve blank connection columns. A blank aligned column means the corresponding Shore Line East train does not have a listed incoming Metro-North connection.

Example:

- Weekend/Holiday SLE 3690 has an incoming MNR 6502 connection from Grand Central Terminal to New Haven Union Station.
- Weekend/Holiday SLE 3692 has no listed incoming MNR connection in the source table.
- Weekday MNR 1556 may appear in duplicate columns because the same physical train connects to multiple onward services.
- Weekday MNR 1560 has a Monday-Thursday-only connection where marked by the source table.

Current safeguard:

- `extract_timetables.py` parses Shore Line East `CONNECTIONS FROM NEW YORK (ARRIVING)` blocks separately and emits them as Metro-North New Haven Line stop-event rows.
- Day-of-service notes such as `MON-THURS` are assigned only to the nearest train column.

## Stitch Through Trains Into One Trip

Some timetable columns are marked `SLE THRU`. These are Shore Line East through trains, not transfer itineraries.

Required behavior:

- If a train appears as `SLE THRU` in a connection table and also appears in the Shore Line East service table, stitch those rows into one CTrail Shore Line East trip.
- Preserve the upstream station times before New Haven.
- Preserve the Shore Line East station times after New Haven.
- Do not represent the through segment as Metro-North plus Shore Line East with a required transfer.
- Keep adjacent Amtrak columns separate; do not assign Amtrak times to the `SLE THRU` train.

Example:

- Weekday SLE THRU 1638 can be boarded at Stamford at 4:13 PM.
- The same one-seat train continues through New Haven and arrives New London at 6:28 PM.
- It should appear as a direct CTrail Shore Line East itinerary, not a transfer at New Haven.

Current safeguard:

- `extract_timetables.py` stitches matching Metro-North connection rows and Shore Line East rows when the same train number appears as a through Shore Line East service.

## Keep Shore Line East Service Tables Separate From Connection Tables

Shore Line East PDFs contain both the public Shore Line East timetable grid and published connection rows. These rows share a source PDF and may share direction labels such as `To New Haven`, but they are not always part of the same table product.

Required behavior for a Shore Line East service-table view:

- Include rows where `direction=To New Haven`, `service_days=weekday`, and `agency` is `CTrail` or `Amtrak`.
- Exclude `Metro-North` rows unless the requested output is explicitly a connections-from-New-York table.
- Keep Amtrak columns in the service-table view when they appear in the Shore Line East timetable, and label them as `Amtrak {train_number}`.
- Keep Shore Line East columns labeled as `SLE {train_number}`.
- Include `SLE THRU` rows when present as Shore Line East service rows.
- Preserve blank station/train cells; a missing stop must stay blank and must not be filled from a neighboring train.
- Sort train columns by the first timed stop in station sequence, not by the earliest clock time anywhere in the trip. This keeps late-night trips such as weekend/holiday SLE 3699 at the end of the table even though downstream stops occur after midnight.
- Treat `New Haven - Union Station` and `New Haven Union Station` as the same station ID (`NHV`) for search and routing, while preserving source labels when displaying a source-faithful timetable.

Required behavior for Shore Line East connection-to-New-York rows:

- Extract `CONNECTIONS TO NEW YORK (DEPARTING)` tables as connection rows with `direction=To Grand Central`.
- Include `SLE THRU` columns as `agency=CTrail`, `service_name=Shore Line East`, and `route_name=Shore Line East`.
- Include Metro-North columns as `agency=Metro-North`, `service_name=New Haven Line`, and `route_name=New Haven Line`.
- Do not preserve duplicate published columns as duplicate CSV trips when the same physical train has the same stop times. For example, the two published MNR 1561 columns should collapse to one logical train in CSV output.
- Preserve column-specific service notes. For example, `MON-THURS` should become `service_days=monday_through_thursday`, `FRI` should become `service_days=friday`, and `SUP EXP` should remain in `raw_notes`.
- Store times in 24-hour `HH:MM` format in CSV output.

Example:

- Weekday `To New Haven` source-table output from `ctrail_shore_line_east_effective_2026-03-29_updated_2026-03-17.csv` should include SLE trains 1633, 1637, 1645, 1659, 1667, 1681, 1687, 1691, 1695, 1699 and Amtrak 93/137.
- The same output should not include Metro-North connection trains 1502, 1504, 1510, 1524, 1534, 1556, 1560, or 1570.

Current safeguard:

- `supporting_files/extraction/pivot_sle_timetable.py` applies this filter when creating station-by-train Shore Line East timetable views from extracted source CSVs.
- `extract_timetables.py` parses both Shore Line East connection directions and rewrites existing per-source CSV snapshots from the final post-processed rows.

## Represent Partial Hartford Line Connections

Hartford Line PDFs list some connecting rail services only as New Haven arrival or departure times. They do not provide the full Metro-North, Amtrak, or Shore Line East station context for those connecting trips.

Hartford Line PDFs may also include `CTtransit` columns. These are bus substitution trips, not Amtrak trains.

Required behavior:

- Extract full Hartford Line tables as normal stop-event trips.
- Classify `CTtransit` columns as `agency=CTtransit`, `service_name=Bus substitution`, and `route_name=Hartford Line`.
- If one `CTtransit 950` header visually spans two timetable columns, split it into two internal trip instances using the two aligned time columns. The prototype should still display both as `Bus 950`.
- If Amtrak 490 appears as duplicate weekday northbound Hartford Line columns, preserve both patterns: `490~1` is the express pattern and `490~2` is the local pattern.
- Preserve column-specific weekend notes in Hartford Line mixed HL/AMTK tables. For example, Sunday-only Amtrak 157/409/465/497 columns should use `service_days=sunday`, and Saturday-only Amtrak 147/463/467 columns should use `service_days=saturday`.
- Extract Hartford Line connection blocks as provisional one-stop rows at New Haven Union Station.
- Use `unknown` exactly for the missing time side.
- For incoming connections to New Haven, set `arrival_time` to the known time and `departure_time` to `unknown`.
- For outgoing connections from New Haven, set `arrival_time` to `unknown` and `departure_time` to the known time.
- Preserve destination context such as `To Grand Central Terminal` or `To Penn Station` in `raw_notes`, not as a fully timed stop.
- Do not allow destination labels such as `To Grand Central Terminal`, `To Penn Station`, or `To New London` to become `station_name` values. They are direction/context labels for New Haven connection stubs, not separate stations.

Examples:

- AMTK 66 arriving New Haven at 7:24 AM becomes an Amtrak connection row with `arrival_time=07:24` and `departure_time=unknown`.
- MNR 6513 departing toward Grand Central Terminal at 7:39 AM becomes a Metro-North row with `arrival_time=unknown` and `departure_time=07:39`.

Current safeguard:

- `extract_timetables.py` emits Hartford connection stubs separately from complete Hartford Line service rows.
- `extract_timetables.py` trims generic CTrail service-table parsing before connection blocks and rejects generic CTrail station names that start with `To `.
- If the same train number appears in multiple aligned columns on the same CTrail table, `extract_timetables.py` gives each column an internal `~1`, `~2`, etc. suffix. The prototype strips that suffix when displaying the train number, but keeps it for trip grouping so separate columns do not collapse into one impossible stop pattern.
- `extract_timetables.py` annotates duplicate Amtrak 490 Hartford northbound columns with `raw_notes=express` for `490~1` and `raw_notes=local` for `490~2`.
- The prototype treats `unknown` times as missing for routing math so partial stubs do not create bogus complete itineraries.
