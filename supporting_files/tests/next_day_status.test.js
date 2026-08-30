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
  if (mode === "arrive") {
    return value > queryTime ? value - 1440 : value;
  }
  return value < queryTime ? value + 1440 : value;
}

function routeDayStatus(route, queryTime, mode, searchDate) {
  const times = routeWindowTimes(route, queryTime, mode);
  if (mode === "arrive") {
    if (dayOffset(times.departure) < 0 && dayOffset(times.arrival) >= 0) return "arrivesNextDay";
    if (dayOffset(times.departure) > 0) return "nextDay";
    if (dayOffset(times.arrival) > 0) return "arrivesNextDay";
    return "";
  }
  const searchWindowStart = mode === "arrive" ? queryTime - SEARCH_WINDOW_MINUTES : queryTime;
  const searchWindowStartDate = localDateWithOffset(searchDate, dayOffset(searchWindowStart));
  const departureDate = localDateWithOffset(searchDate, dayOffset(times.departure));
  const arrivalDate = localDateWithOffset(searchDate, dayOffset(times.arrival));
  if (localDateKey(departureDate) > localDateKey(searchWindowStartDate)) return "nextDay";
  if (localDateKey(arrivalDate) > localDateKey(searchWindowStartDate)) return "arrivesNextDay";
  return "";
}

function makeRoute(departure, arrival) {
  return {
    departure,
    arrival,
    duration: arrival < departure ? arrival + 1440 - departure : arrival - departure,
  };
}

function dayOffset(totalMinutes) {
  return Math.floor(totalMinutes / 1440);
}

function localDateWithOffset(date, offset) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + offset);
}

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

assert.strictEqual(
  routeDayStatus(makeRoute(8 * 60, 9 * 60), 7 * 60, "leave", new Date(2026, 6, 25)),
  "",
  "same-day departures and arrivals do not receive a next-day label",
);

assert.strictEqual(
  routeDayStatus(makeRoute(23 * 60 + 35, 3), 23 * 60, "leave", new Date(2026, 6, 25)),
  "arrivesNextDay",
  "trips leaving before midnight and arriving after midnight are labeled as arriving next day",
);

assert.strictEqual(
  routeDayStatus(makeRoute(6, 34), 23 * 60, "leave", new Date(2026, 6, 25)),
  "nextDay",
  "trips departing after midnight inside the leave-after window are labeled as next day",
);

assert.strictEqual(
  routeDayStatus(makeRoute(6, 34), 23 * 60, "leave", new Date(2026, 2, 7)),
  "nextDay",
  "post-midnight departures remain next-day departures across the spring DST boundary",
);

assert.strictEqual(
  routeDayStatus(makeRoute(23 * 60 + 35, 3), 23 * 60, "leave", new Date(2026, 9, 31)),
  "arrivesNextDay",
  "after-midnight arrivals remain next-day arrivals across the fall DST boundary",
);

assert.strictEqual(
  routeDayStatus(makeRoute(23 * 60 + 35, 3), 10, "arrive", new Date(2026, 6, 26)),
  "arrivesNextDay",
  "early-morning arrive-by searches label previous-evening trips that arrive after midnight",
);

assert.strictEqual(
  routeDayStatus(makeRoute(24, 43), 22 * 60, "arrive", new Date(2026, 7, 30)),
  "",
  "late-day arrive-by searches do not mark same-date early-morning service as next day",
);

console.log("next-day status tests passed");
