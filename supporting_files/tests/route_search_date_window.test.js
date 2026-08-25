const assert = require("assert");

const SEARCH_WINDOW_MINUTES = 23 * 60 + 59;

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function localDateWithOffset(date, offset) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + offset);
}

function dayOffset(totalMinutes) {
  return Math.floor(totalMinutes / 1440);
}

function localDateIso(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function serviceDatesForSearch(date, mode) {
  return mode === "arrive" ? [date, addDays(date, -1)] : [date, addDays(date, 1)];
}

function serviceApplies(trip, date) {
  const dateIso = localDateIso(date);
  if (trip.serviceDates && trip.serviceDates.includes(dateIso)) return true;
  const day = date.getDay();
  if (trip.serviceDays === "weekday") return day >= 1 && day <= 5;
  if (trip.serviceDays === "sunday") return day === 0;
  return false;
}

function adjustedForWindow(value, queryTime, mode) {
  if (mode === "arrive") return value > queryTime ? value - 1440 : value;
  return value < queryTime ? value + 1440 : value;
}

function matchesSearch(departure, arrival, queryTime, mode) {
  const candidate = adjustedForWindow(mode === "arrive" ? arrival : departure, queryTime, mode);
  return mode === "arrive"
    ? candidate <= queryTime && candidate >= queryTime - SEARCH_WINDOW_MINUTES
    : candidate >= queryTime && candidate <= queryTime + SEARCH_WINDOW_MINUTES;
}

function routeDisplayOffset(route, queryTime, mode) {
  const departure = adjustedForWindow(route.departure, queryTime, mode);
  return departure - route.departure;
}

function routeServiceApplies(route, searchDate, queryTime, mode) {
  const displayOffset = routeDisplayOffset(route, queryTime, mode);
  return route.legs.every((leg) => {
    const legDate = localDateWithOffset(searchDate, dayOffset(leg.departure + displayOffset));
    return serviceApplies(leg.trip, legDate);
  });
}

function routeFromTrip(trip) {
  return {
    departure: trip.departure,
    arrival: trip.arrival,
    legs: [{ departure: trip.departure, trip }],
  };
}

function findRoutes(trips, queryTime, mode, date) {
  return trips
    .filter((trip) => serviceDatesForSearch(date, mode).some((serviceDate) => serviceApplies(trip, serviceDate)))
    .map(routeFromTrip)
    .filter((route) => matchesSearch(route.departure, route.arrival, queryTime, mode))
    .filter((route) => routeServiceApplies(route, date, queryTime, mode));
}

const sunday = new Date("2026-07-26T12:00:00");
const monday = new Date("2026-07-27T12:00:00");
const eightAm = 8 * 60;

assert.strictEqual(
  findRoutes([{ serviceDays: "weekday", departure: 6 * 60 + 28, arrival: 8 * 60 + 29 }], eightAm, "leave", sunday).length,
  1,
  "leave-after searches include next-day service inside the 24-hour window",
);

assert.strictEqual(
  findRoutes([{ serviceDates: "2026-07-27", departure: 6 * 60 + 28, arrival: 8 * 60 + 29 }], eightAm, "leave", monday).length,
  0,
  "next-day displayed routes must also operate on the next calendar day",
);

assert.strictEqual(
  findRoutes([{ serviceDays: "sunday", departure: 22 * 60, arrival: 23 * 60 }], eightAm, "arrive", monday).length,
  1,
  "arrive-by searches include previous-day service inside the 24-hour window",
);

console.log("route search date-window tests passed");
