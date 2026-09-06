# CTrail Fare Data

moose.train currently implements standard adult one-way fares for CTrail Shore Line East and CTrail Hartford Line trips that can be priced directly from the published station-to-station one-way matrices.

The encoded fare data is effective July 1, 2026 and comes from:

- Shore Line East fare page: https://shorelineeast.com/fares/
- Shore Line East fare chart: https://shorelineeast.com/wp-content/uploads/2026/08/CTrail-Fares-2026-updates.xlsx-Shore-Line-East-Fares.pdf
- Hartford Line fare page: https://hartfordline.com/fares-schedules/ticketing/
- Hartford Line fare chart: https://hartfordline.com/wp-content/uploads/2026/06/CTrail-Fares-2026-updates.xlsx-Hartford-Line-Fares.pdf

Only the adult standard one-way fare category is implemented. Senior, disabled, Medicare, child, student, military, onboard, weekly, monthly, ten-trip, school monthly, UniRail, group, and other special fare products are intentionally out of scope for the MVP. Fare amounts are stored as integer cents and formatted for display at render time.

Hartford Line tickets are accepted on eligible Amtrak Regional and Shuttle trains between New Haven and Springfield, except the Vermonter trains 54, 55, 56, and 57 at any time and Amtrak Northeast Regional trains 140, 141, 143, 146, 147, 148, and 157 during holiday blackout periods. In the current schedule data, eligible Amtrak trips are represented with `service_name` and `route_name` of `Amtrak Hartford Line`, so the CTrail Hartford fare rule recognizes that product rather than every Amtrak-operated train.

UniRail is a separate fare product for combining Hartford Line or Shore Line East rail service with New Haven Line, Shore Line East, or Hartford Line segments. The current MVP does not implement UniRail as a discounted connecting fare product. For mixed itineraries where every leg has a supported standard one-way fare, moose.train displays the sum of those supported leg fares as the result-card total and also displays each leg fare separately. If any leg is unsupported, supported leg fares still display on their individual legs, but the result-card total is omitted.
