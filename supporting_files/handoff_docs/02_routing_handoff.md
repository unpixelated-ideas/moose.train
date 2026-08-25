# Routing Thread Handoff

## Current State

Routing currently lives inside `index.html`.

The prototype:

- Loads `moose_train_schedule.csv`, with embedded CSV fallback for local file use.
- Groups trips from stop-event rows.
- Searches direct trips and one-transfer itineraries.
- Uses a 5-minute transfer buffer.
- Shows all results in a 23-hour, 59-minute search window.
- Treats `unknown` times as missing and non-routable.

## Owned Responsibilities

This thread owns:

- Route search behavior.
- Transfer sanity filters.
- Direct-vs-transfer ranking.
- Service-day applicability.
- Time-window behavior.
- Route result correctness across services.
- Allowed intermediate transfer hubs.

## Current Routing Rules

Preserve these rules:

- Reject riding past the destination and doubling back.
- Allow intermediate transfers only at New Haven Union Station, Bridgeport, Stamford, South Norwalk, and Grand Central Terminal.
- Reject transfers off a train that continues to the destination.
- Reject transfers to a train that already served the origin.
- Prefer direct trips over dominated transfers.
- Use the earliest valid onward connection for equivalent onward service.
- Keep meaningfully different onward services, such as Amtrak versus Shore Line East.
- Do not use rows with `unknown` arrival/departure times for routing math.

## Known Pitfalls

- Station aliases must match before route search.
- Branch-only stations should not appear in main-line trips.
- A direct route should generally rank above a transfer that arrives no earlier.
- Some published connections are partial stubs and must not become complete trips.

## First Checks To Run

Use the browser or a lightweight script to verify:

- New Haven - Union Station to Old Saybrook
- Grand Central Terminal to Old Saybrook
- New Haven - Union Station to Hartford
- Waterbury to Grand Central
- Grand Central to New Canaan

Expected behavior:

- Direct trips appear when available.
- Transfers do not skip an earlier equivalent connection.
- Partial `unknown` rows do not create route legs.

## References

- `supporting_files/reference/routing_logic.md`
- `index.html`
