# Generic GTFS Importer

Moose.train ingests static railroad schedules through `supporting_files/extraction/gtfs_importer.py`.

The importer is feed-configured rather than railroad-parser-specific. Adding another GTFS-compatible railroad should usually mean adding one `GtfsFeedConfig`, optional route filters, optional station-scope rules, and optional station normalization aliases.

## Configured Feeds

Current feeds:

| Feed ID | Source ID | Operator | URL | Route Selection |
|---|---|---|---|---|
| `lirr` | `lirr` | LIRR | `https://rrgtfsfeeds.s3.amazonaws.com/gtfslirr.zip` | All rail branches; exclude the nonpublic Hillside Facility. |
| `mnr` | `mnr` | Metro-North | `https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip` | Include route IDs `1`–`6`: Hudson, Harlem, New Haven, and its three branches. Port Jervis and Pascack Valley remain out of scope. Exclude non-public Highbridge Yard and Springdale maintenance stops. |
| `hartford` | `hartford` | CTrail | `https://ctrides.com/hlgtfs.zip` | Import complete feed. |
| `sle` | `amtrak_official` | CTrail | `https://content.amtrak.com/content/gtfs/GTFS.zip` | Include Shore Line East agency `1230` from the Amtrak-hosted feed. |
| `amtrak` | `amtrak_official` | Amtrak | `https://content.amtrak.com/content/gtfs/GTFS.zip` | Include Amtrak agency `51`, rail route type `2`, and trips serving at least two supported stations. |

The CTrail developer listing currently identifies the Amtrak-hosted `GTFS.zip` URL as the current Shore Line East GTFS feed.

`feed_id` identifies the Moose.train service product. `source_id` identifies the physical GTFS source ZIP. Shore Line East and Amtrak intentionally share `source_id=amtrak_official`, so the ZIP is downloaded once and different product rules are applied to the same source data.

## Normalized Output

Each feed writes normalized CSV tables under:

`supporting_files/extraction/normalized_gtfs/{feed_id}/`

Tables:

- `feeds.csv`
- `agencies.csv`
- `routes.csv`
- `trips.csv`
- `stops.csv`
- `stop_times.csv`
- `calendars.csv`
- `calendar_dates.csv`
- `shapes.csv`
- `transfers.csv`
- `canonical_stations.csv`

Identifiers are namespaced as `{feed_id}:{source_id}`. Original source IDs are preserved in `source_*` columns for traceability.

The `stops.csv` table includes `in_search_scope`. Feeds without a configured station scope mark all imported stops as searchable. Amtrak marks only the current launch geography as searchable.

## Amtrak Scope

The current Amtrak product is limited to trips that serve at least two supported stations:

- Connecticut Amtrak stations: Stamford, Bridgeport, New Haven Union, New Haven State Street, Wallingford, Meriden, Berlin, Hartford, Windsor, Windsor Locks, Old Saybrook, New London, Mystic
- New York Penn
- Shared Hudson Line stations: Yonkers, Croton-Harmon, Poughkeepsie
- Springfield
- Westerly

Only those stops are emitted to the combined schedule (`moose_train_schedule.csv.gz` in the repository, restored to CSV for publication). Eligible through-trains may retain out-of-scope stops in normalized GTFS output with `in_search_scope=false`, plus original origin/destination notes in `raw_notes`.

Amtrak route selection uses agency ID `51` and GTFS rail route type `2`. Thruway bus routes and other non-rail route types are excluded by configuration.

## Calendar And Time Rules

Service dates are resolved from `calendar.txt` plus `calendar_dates.txt`.

- `calendar.txt` defines regular service ranges and weekday patterns.
- `calendar_dates.txt` adds or removes specific dates.
- Compact `service_days` values are emitted only when the resolved dates exactly match a regular pattern.
- Irregular service uses explicit `service_dates`.
- GTFS times past midnight, such as `24:05:00`, are valid and preserved as `24:05` in schedule rows.

## Station Rules

The importer preserves every GTFS source stop. It also assigns a canonical Moose.train station ID using explicit aliases or the existing deterministic station ID helper.

Do not fuzzy-match stations during import. If two operators use different source stops for New Haven Union Station, keep both source stops and map them explicitly to the same canonical station ID.

## Refresh Rules

Imports are feed scoped.

- Download to a temporary file.
- Validate the ZIP.
- Extract to a temporary directory.
- Build normalized output in a temporary directory.
- Replace only the target feed output after success.

A failed refresh should leave the previous normalized data for that feed intact and should not touch other feeds.

## Adding Another Railroad

1. Add a `GtfsFeedConfig` in `default_feed_configs()`.
2. Choose a stable internal `feed_id`.
3. Set `operator_name`, `url`, `source_id`, `zip_filename`, and an enabled flag.
4. Add route inclusion or exclusion rules only if the feed contains routes outside the intended import scope.
5. Add explicit station aliases or source-stop-ID mappings only where needed for canonical station mapping.
6. Add station-scope rules when the feed contains a larger geography than Moose.train should expose.
7. Run the GTFS importer tests and a full extraction.
8. Confirm `gtfs_import_metadata.csv` has expected counts and no unexpected errors.

Only create feed-specific parsing code for a documented GTFS incompatibility.

## LIRR station identity

LIRR uses stable `LIRR_` station IDs to avoid collisions with other feeds. Penn Station maps to `NYP`, and Grand Central Madison maps to `GCT`, shared with Metro-North Grand Central Terminal. Operator-specific boarding areas remain visible in journey details. Public coverage includes Long Island and the LIRR stations in New York City; the one-transfer search limit still applies. The official source is [MTA Developer Resources](https://www.mta.info/developers).

## Hudson and Harlem expansion

Hudson/Harlem stations use explicit stable IDs in `MNR_EXPANSION_STATION_IDS`; shared Amtrak stations use `YNY`, `CRT`, and `POU` for both operators. Fordham keeps `FOR`. New stations retain MTA source names; IDs do not depend on future renaming. Passenger stop permissions remain in `raw_notes` and prepared search stops. Limited-service stations appear only with published service; no trains are synthesized for them.
