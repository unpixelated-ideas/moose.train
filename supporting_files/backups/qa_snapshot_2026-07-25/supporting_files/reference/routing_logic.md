# Routing Logic Notes

This document records routing sanity rules used by the `index.html` prototype. These rules should continue to apply as new agency timetables are added.

## Core Model

- The CSV uses one row per train stop event.
- A trip is grouped by agency, service name, train number, and direction.
- Stop order is determined by `station_sequence`.
- Direct trips are valid when the origin appears before the destination on the same trip.
- Transfer trips are currently limited to one transfer.
- Intermediate transfers are only allowed at explicit transfer hubs: New Haven Union Station, Bridgeport, Stamford, South Norwalk, and Grand Central Terminal.
- Other stations can still be origins or destinations, but they are not treated as reasonable intermediate transfer points unless added to the transfer hub list later.
- Published through trains, such as `SLE THRU`, should be represented as one trip so they route as direct service.
- Literal `unknown` arrival or departure times are treated as missing and cannot be used for routing math.

## Transfer Sanity Rules

### Do Not Ride Past The Destination And Double Back

Reject a transfer itinerary if the first leg passes through the final destination before the transfer point.

Example to reject:

- Origin: New Haven - Union Station
- Destination: Old Saybrook
- Bad route: New Haven - Union Station to New London, then New London back to Old Saybrook

Reason:

The rider has already passed the destination, so the transfer is not a sensible route.

### Do Not Transfer Off A Train That Continues To The Destination

Reject a transfer itinerary if the first train continues to the final destination after the proposed transfer stop.

Example to reject:

- Origin: New Haven - Union Station
- Destination: Old Saybrook
- Bad route: New Haven - Union Station to New Haven - State Street, wait, then another train to Old Saybrook
- Better route: stay on the first train to Old Saybrook

Reason:

The transfer adds waiting and complexity when the rider could remain on the same train.

### Use The Earliest Valid Onward Connection

When one first leg reaches a transfer station, keep only the earliest valid onward train from that transfer station to the destination for each onward agency/service.

Example to reject:

- Origin: Grand Central Terminal
- Destination: Old Saybrook
- First leg: MNR 6504 arrives at New Haven Union Station at 8:04 AM
- Good onward leg: SLE 3604 departs New Haven Union Station at 9:12 AM
- Bad onward leg: SLE 3610 departs New Haven Union Station at 10:45 AM

Reason:

Once the rider is already at the transfer station, skipping an earlier valid onward train and waiting for a later equivalent train creates a strictly worse itinerary.

Exception:

Keep multiple onward options when they use meaningfully different services, such as Amtrak versus Shore Line East. For example, weekday MNR 1556 can connect at New Haven to Amtrak 94 or Shore Line East 1640; both should remain available because they are different onward services.

### Do Not Transfer To A Train That Already Served The Origin

Reject a transfer itinerary if the second train stopped at the rider's origin before the proposed transfer station.

Example to reject:

- Origin: New Haven Union Station
- Destination: Hartford
- Bad route: Shore Line East from New Haven Union Station to New Haven - State Street, then Hartford Line from New Haven - State Street to Hartford
- Better route: board the Hartford Line train directly at New Haven Union Station

Reason:

The transfer only moves the rider sideways to catch a train they could already have boarded at the origin.

### Prefer Direct Trips Over Dominated Transfers

Reject a transfer itinerary when a direct trip departs at the same time or later and arrives at the same time or earlier.

Example to reject:

- Origin: New Haven Union Station
- Destination: Hartford
- Bad route: depart 5:12 AM, transfer at New Haven - State Street, arrive 6:10 AM
- Better route: direct Hartford Line trip departs 5:18 AM and arrives 6:10 AM

Reason:

The transfer requires more time and more complexity without arriving earlier.

## Future Considerations

- These rules should be applied across all services, not only Shore Line East.
- Future multi-transfer routing should apply the same principles to every leg.
- Add future transfer hubs deliberately alongside the timetable coverage that makes them useful, such as New London after full Amtrak service enables Mystic or other east-of-New-London destinations.
- If express/local or fare rules later make a seemingly indirect route useful, add an explicit exception rather than weakening these defaults.
- Station aliases should be normalized before routing so equivalent stations do not create false transfer opportunities.
