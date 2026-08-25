const assert = require("assert");

const SEARCH_WINDOW_MINUTES = 23 * 60 + 59;

function routeWindowTimes(route, queryTime, mode) {
  if (mode === "arrive") {
    const arrival = adjustedForWindow(route.arrival, queryTime, mode);
    return { departure: arrival - route.duration, arrival };
  }
  const departure = adjustedForWindow(route.departure, queryTime, mode);
  return { departure, arrival: departure + route.duration };
}

function adjustedForWindow(value, queryTime, mode) {
  if (mode === "arrive") return value > queryTime ? value - 1440 : value;
  return value < queryTime ? value + 1440 : value;
}

function departureRangeStart(queryTime, mode) {
  return mode === "arrive" ? queryTime - SEARCH_WINDOW_MINUTES : queryTime;
}

function filterRoutesByDepartureRange(routes, queryTime, mode, hours) {
  if (hours >= 24) return routes;
  const start = departureRangeStart(queryTime, mode);
  const end = start + hours * 60;
  return routes.filter((route) => {
    const departure = routeWindowTimes(route, queryTime, mode).departure;
    return departure >= start && departure < end;
  });
}

function makeRoute(departure, arrival, legs = [{ departure }]) {
  return {
    departure,
    arrival,
    duration: arrival - departure,
    legs,
  };
}

function formatTripCount(count) {
  return count === 1 ? "1 trip found" : `${count} trips found`;
}

const eightAm = 8 * 60;
const leaveRoutes = [
  makeRoute(eightAm, eightAm + 20),
  makeRoute(eightAm + 59, eightAm + 90),
  makeRoute(eightAm + 60, eightAm + 120),
  makeRoute(eightAm - 1, eightAm + 30),
];

assert.deepStrictEqual(
  filterRoutesByDepartureRange(leaveRoutes, eightAm, "leave", 1).map((route) => route.departure),
  [eightAm, eightAm + 59],
  "hourly slider ranges use a half-open endpoint",
);

assert.strictEqual(
  filterRoutesByDepartureRange(leaveRoutes, eightAm, "leave", 24),
  leaveRoutes,
  "full search period preserves the complete existing result set",
);

const transferRoute = makeRoute(eightAm + 10, eightAm + 160, [
  { departure: eightAm + 10 },
  { departure: eightAm + 90 },
]);
assert.strictEqual(
  filterRoutesByDepartureRange([transferRoute], eightAm, "leave", 1).length,
  1,
  "transfer trips are filtered by the initial itinerary departure",
);

assert.strictEqual(formatTripCount(1), "1 trip found", "singular count uses trip");
assert.strictEqual(formatTripCount(0), "0 trips found", "zero count uses trips");
assert.strictEqual(formatTripCount(47), "47 trips found", "plural count uses trips");

console.log("departure range filter tests passed");
