const assert = require("assert");

const MNR_REALTIME_ROUTE_IDS = new Set(["3", "4", "5", "6"]);
const MINOR_DELAY_MAX_SECONDS = 15 * 60;
const MNR_REALTIME_SERVICE_NAMES = ["new haven line", "new canaan branch", "danbury branch", "waterbury branch"];
const APP_TO_MNR_GTFS_STOP_ID = new Map([
  ["BRP", "140"],
  ["DAN", "165"],
  ["DBY", "167"],
  ["FFD", "138"],
  ["GCT", "1"],
  ["GLB", "153"],
  ["NCN", "157"],
  ["NHV", "149"],
  ["SONO", "131"],
  ["SPD", "154"],
  ["STM", "124"],
  ["TMH", "155"],
  ["WBY", "172"],
]);

function normalize(value) {
  return String(value || "").toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, " ").trim();
}

function displayTrainNumber(value) {
  return String(value || "").split("~")[0];
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function localDateIso(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function realtimeSearchServiceDates(searchDate) {
  return [addDays(searchDate, -1), searchDate, addDays(searchDate, 1)];
}

function isMetroNorthRealtimeTrip(trip) {
  const text = normalize(`${trip.service} ${trip.route}`);
  return normalize(trip.agency) === "metro north" &&
    MNR_REALTIME_SERVICE_NAMES.some((name) => (
      name === "new haven line"
        ? text.includes(name) && !text.includes("branch")
        : text.includes(name)
    )) &&
    trip.stops.some((stop) => APP_TO_MNR_GTFS_STOP_ID.has(stop.id));
}

function isMetroNorthRealtimeLeg(leg) {
  return isMetroNorthRealtimeTrip(leg.trip) &&
    APP_TO_MNR_GTFS_STOP_ID.has(leg.fromId) &&
    APP_TO_MNR_GTFS_STOP_ID.has(leg.toId);
}

function realtimeTripMatchesStaticStops(update, trip) {
  const staticStopIds = trip.stops.map((stop) => APP_TO_MNR_GTFS_STOP_ID.get(stop.id)).filter(Boolean);
  if (!staticStopIds.length) return false;
  const realtimeStopIds = update.stopUpdates.map((stop) => stop.stopId);
  const sharedStops = staticStopIds.filter((stopId) => realtimeStopIds.includes(stopId));
  if (sharedStops.length < Math.min(2, staticStopIds.length)) return false;
  return sharedStops.every((stopId, index) => {
    if (index === 0) return true;
    return realtimeStopIds.indexOf(sharedStops[index - 1]) < realtimeStopIds.indexOf(stopId);
  });
}

function matchMetroNorthRealtimeTrip(trip, snapshot, searchDate) {
  if (!isMetroNorthRealtimeTrip(trip)) return null;
  const trainNumber = displayTrainNumber(trip.train);
  const candidates = snapshot.tripUpdates.filter((update) => (
    update.trainNumber === trainNumber &&
    (!update.routeId || metroNorthRealtimeTripAllowsRouteId(trip, update.routeId)) &&
    (!update.serviceDate || realtimeSearchServiceDates(searchDate).some((date) => localDateIso(date) === update.serviceDate))
  ));
  const confident = candidates.filter((update) => realtimeTripMatchesStaticStops(update, trip));
  return confident.length === 1 ? confident[0] : null;
}

function metroNorthRealtimeTripAllowsRouteId(trip, routeId) {
  if (!MNR_REALTIME_ROUTE_IDS.has(routeId)) return false;
  const text = normalize(`${trip.service} ${trip.route}`);
  if (routeId === "3") return text.includes("new haven line") && !text.includes("branch");
  if (routeId === "4") return text.includes("new canaan branch");
  if (routeId === "5") return text.includes("danbury branch");
  if (routeId === "6") return text.includes("waterbury branch");
  return false;
}

function normalizeMetroNorthRealtimeEntity(entity) {
  const descriptor = entity.tripUpdate.trip || {};
  const realtimeTripId = String(descriptor.tripId || "").trim();
  return {
    trainNumber: String(entity.id || realtimeTripId || "").trim(),
    realtimeTripId,
    routeId: String(descriptor.routeId || "").trim(),
  };
}

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

function serviceMinuteEpochSeconds(searchDate, serviceMinutes) {
  return Math.floor(new Date(
    searchDate.getFullYear(),
    searchDate.getMonth(),
    searchDate.getDate(),
    0,
    serviceMinutes,
    0,
    0,
  ).getTime() / 1000);
}

function routeStatusWindowTimes(route, queryTime, mode) {
  const displayOffset = routeWindowTimes(route, queryTime, mode).departure - route.departure;
  const departure = (route.realtime?.departure ?? route.departure) + displayOffset;
  let arrival = (route.realtime?.arrival ?? route.arrival) + displayOffset;
  if (arrival < departure) arrival += 1440;
  return { departure, arrival };
}

function routeRealtimeStatus(route, queryTime, mode, searchDate, realtimeSnapshot, nowSeconds) {
  if (route.legs.some((leg) => leg.realtime?.isCanceled)) return "ⓧ";
  if (route.legs.some((leg) => leg.realtime?.departure?.isSkipped || leg.realtime?.arrival?.isSkipped)) return "⛔️";
  if (serviceMinuteEpochSeconds(searchDate, routeStatusWindowTimes(route, queryTime, mode).arrival) <= currentStatusEpochSeconds(searchDate, realtimeSnapshot, nowSeconds)) return "✓";

  const mixedCoverage = route.legs.some(isMetroNorthRealtimeLeg) && route.legs.some((leg) => !isMetroNorthRealtimeLeg(leg));
  if (route.realtime) {
    const delaySeconds = route.legs.reduce((maxDelay, leg) => Math.max(
      maxDelay,
      positiveDelaySeconds(leg.realtime?.departure?.delaySeconds),
      positiveDelaySeconds(leg.realtime?.arrival?.delaySeconds),
    ), 0);
    const allDelaySeconds = route.legs.flatMap((leg) => [
      leg.realtime?.departure?.delaySeconds,
      leg.realtime?.arrival?.delaySeconds,
    ]).filter(Number.isFinite);
    if (allDelaySeconds.length && Math.min(...allDelaySeconds) < 0) return "🔥";
    if (delaySeconds > MINOR_DELAY_MAX_SECONDS) return "🔴";
    if (delaySeconds > 0) return "🟡";
    return "🟢";
  }

  if (!route.legs.some(isMetroNorthRealtimeLeg)) return "⊙";
  if (mixedCoverage && serviceMinuteEpochSeconds(searchDate, routeStatusWindowTimes(route, queryTime, mode).departure) <= currentStatusEpochSeconds(searchDate, realtimeSnapshot, nowSeconds)) return "⊙";
  if (serviceMinuteEpochSeconds(searchDate, routeStatusWindowTimes(route, queryTime, mode).departure) > realtimeSnapshot.maxPredictionEpochSeconds) return "◷";
  if (mixedCoverage) return "⊙";
  return "";
}

function positiveDelaySeconds(value) {
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function currentStatusEpochSeconds(searchDate, realtimeSnapshot, nowSeconds) {
  const feedNow = Number(realtimeSnapshot?.feedTimestamp || 0);
  return Math.max(nowSeconds, feedNow, searchDateProjectedFeedEpochSeconds(searchDate, realtimeSnapshot));
}

function searchDateProjectedFeedEpochSeconds(searchDate, realtimeSnapshot) {
  const feedNow = Number(realtimeSnapshot?.feedTimestamp || 0);
  if (!feedNow || !realtimeSnapshotHasServiceDate(realtimeSnapshot, searchDate)) return 0;
  const feedDate = new Date(feedNow * 1000);
  return Math.floor(new Date(
    searchDate.getFullYear(),
    searchDate.getMonth(),
    searchDate.getDate(),
    feedDate.getHours(),
    feedDate.getMinutes(),
    feedDate.getSeconds(),
    feedDate.getMilliseconds(),
  ).getTime() / 1000);
}

function realtimeSnapshotHasServiceDate(realtimeSnapshot, searchDate) {
  const selectedDate = localDateIso(searchDate);
  return (realtimeSnapshot?.tripUpdates || []).some((update) => update.serviceDate === selectedDate);
}

const searchDate = new Date(2026, 7, 19, 12);
const newCanaanTrip = {
  agency: "Metro-North",
  service: "New Canaan Branch",
  route: "New Haven Line - New Canaan Branch",
  train: "1710",
  stops: [{ id: "STM" }, { id: "GLB" }, { id: "SPD" }, { id: "TMH" }, { id: "NCN" }],
};
const newHavenTrip = {
  agency: "Metro-North",
  service: "New Haven Line",
  route: "New Haven Line",
  train: "1574",
  stops: [{ id: "GCT" }, { id: "H125" }, { id: "STM" }, { id: "BRP" }, { id: "NHV" }],
};
const danburyTrip = {
  agency: "Metro-North",
  service: "Danbury Branch",
  route: "New Haven Line - Danbury Branch",
  train: "1874",
  stops: [{ id: "SONO" }, { id: "DBY" }, { id: "DAN" }],
};
const waterburyTrip = {
  agency: "Metro-North",
  service: "Waterbury Branch",
  route: "New Haven Line - Waterbury Branch",
  train: "B1456",
  stops: [{ id: "BRP" }, { id: "DBY" }, { id: "WBY" }],
};
const ctrailTrip = {
  agency: "CTrail",
  service: "Shore Line East",
  route: "Shore Line East",
  train: "1652",
  stops: [{ id: "NHV" }, { id: "CLIN" }],
};
const newCanaanRoute = {
  departure: 17 * 60,
  arrival: 17 * 60 + 17,
  duration: 17,
  legs: [{
    fromId: "STM",
    toId: "NCN",
    trip: newCanaanTrip,
  }],
};
const mixedCoverageRoute = {
  departure: 20 * 60 + 1,
  arrival: 21 * 60 + 20,
  duration: 79,
  legs: [
    {
      fromId: "FFD",
      toId: "NHV",
      departure: 20 * 60 + 1,
      arrival: 20 * 60 + 41,
      trip: newHavenTrip,
    },
    {
      fromId: "NHV",
      toId: "CLIN",
      departure: 20 * 60 + 52,
      arrival: 21 * 60 + 20,
      trip: ctrailTrip,
    },
  ],
};
const nowBeforeTrip = serviceMinuteEpochSeconds(searchDate, 16 * 60);

assert.strictEqual(
  isMetroNorthRealtimeLeg({ fromId: "STM", toId: "NCN", trip: newCanaanTrip }),
  true,
  "New Canaan Branch station-to-station legs are eligible for Metro-North realtime",
);

assert.strictEqual(
  isMetroNorthRealtimeLeg({ fromId: "SONO", toId: "DAN", trip: danburyTrip }),
  true,
  "Danbury Branch station-to-station legs are eligible for Metro-North realtime",
);

assert.strictEqual(
  isMetroNorthRealtimeLeg({ fromId: "BRP", toId: "WBY", trip: waterburyTrip }),
  true,
  "Waterbury Branch station-to-station legs are eligible for Metro-North realtime",
);

assert.strictEqual(
  isMetroNorthRealtimeLeg({ fromId: "STM", toId: "NHV", trip: newHavenTrip }),
  true,
  "New Haven Line station-to-station legs are eligible for Metro-North realtime",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(newCanaanTrip, {
    tripUpdates: [{
      trainNumber: "1710",
      routeId: "4",
      serviceDate: "2026-08-19",
      stopUpdates: [{ stopId: "124" }, { stopId: "153" }, { stopId: "154" }, { stopId: "155" }, { stopId: "157" }],
    }],
  }, searchDate).trainNumber,
  "1710",
  "GTFS-RT trip_id is matched to static trip_short_name/train number with route and stop confirmation",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(newHavenTrip, {
    tripUpdates: [{
      trainNumber: "1574",
      routeId: "3",
      serviceDate: "2026-08-19",
      stopUpdates: [{ stopId: "1" }, { stopId: "124" }, { stopId: "140" }, { stopId: "149" }],
    }],
  }, searchDate).trainNumber,
  "1574",
  "New Haven Line route updates enrich New Haven Line trips",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(danburyTrip, {
    tripUpdates: [{
      trainNumber: "1874",
      routeId: "5",
      serviceDate: "2026-08-19",
      stopUpdates: [{ stopId: "131" }, { stopId: "167" }, { stopId: "165" }],
    }],
  }, searchDate).trainNumber,
  "1874",
  "Danbury Branch route updates enrich Danbury Branch trips",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(waterburyTrip, {
    tripUpdates: [{
      trainNumber: "B1456",
      routeId: "6",
      serviceDate: "2026-08-19",
      stopUpdates: [{ stopId: "140" }, { stopId: "167" }, { stopId: "172" }],
    }],
  }, searchDate).trainNumber,
  "B1456",
  "Waterbury Branch route updates enrich Waterbury Branch trips",
);

assert.deepStrictEqual(
  normalizeMetroNorthRealtimeEntity({
    id: "1770",
    tripUpdate: { trip: { tripId: "3177467", routeId: "4" } },
  }),
  { trainNumber: "1770", realtimeTripId: "3177467", routeId: "4" },
  "current Metro-North realtime uses FeedEntity.id for the public train number",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(newCanaanTrip, {
    tripUpdates: [
      { trainNumber: "1710", routeId: "4", serviceDate: "2026-08-19", stopUpdates: [{ stopId: "124" }, { stopId: "157" }] },
      { trainNumber: "1710", routeId: "4", serviceDate: "2026-08-19", stopUpdates: [{ stopId: "124" }, { stopId: "157" }] },
    ],
  }, searchDate),
  null,
  "ambiguous realtime candidates fall back to static GTFS",
);

assert.strictEqual(
  matchMetroNorthRealtimeTrip(newCanaanTrip, {
    tripUpdates: [{
      trainNumber: "1710",
      routeId: "3",
      serviceDate: "2026-08-19",
      stopUpdates: [{ stopId: "124" }, { stopId: "157" }],
    }],
  }, searchDate),
  null,
  "New Haven Line mainline route updates do not enrich New Canaan Branch trips",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60, arrival: 17 * 60 + 17 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: 0 }, arrival: { delaySeconds: 0 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "🟢",
  "realtime routes with no positive delay show the no-delay indicator",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60 + 4, arrival: 17 * 60 + 21 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: 240 }, arrival: { delaySeconds: 240 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "🟡",
  "realtime routes delayed by 15 minutes or less show the minor-delay indicator",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60 - 2, arrival: 17 * 60 + 15 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: -120 }, arrival: { delaySeconds: -120 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "🔥",
  "realtime routes running early show the early indicator",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60 + 16, arrival: 17 * 60 + 33 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: 16 * 60 }, arrival: { delaySeconds: 16 * 60 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "🔴",
  "realtime routes delayed by more than 15 minutes show the major-delay indicator",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60, arrival: 17 * 60 + 17 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { isCanceled: true } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "ⓧ",
  "cancellations take precedence over delay status",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60, arrival: 17 * 60 + 17 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { isSkipped: true, delaySeconds: 0 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "⛔️",
  "skipped stops take precedence over delay status",
);

assert.strictEqual(
  routeRealtimeStatus(newCanaanRoute, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, serviceMinuteEpochSeconds(searchDate, 18 * 60)),
  "✓",
  "already-arrived trains show the arrived indicator",
);

assert.strictEqual(
  routeRealtimeStatus(newCanaanRoute, 16 * 60, "depart", searchDate, {
    feedTimestamp: serviceMinuteEpochSeconds(searchDate, 18 * 60),
    maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 19 * 60),
    tripUpdates: [{ serviceDate: "2026-08-19" }],
  }, serviceMinuteEpochSeconds(new Date(2026, 7, 18, 12), 20 * 60)),
  "✓",
  "realtime feed timestamp can mark arrived when the local clock is behind the selected service date",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    departure: 17 * 60 + 18,
    arrival: 18 * 60 + 40,
    duration: 82,
    realtime: { departure: 17 * 60 + 18, arrival: 18 * 60 + 40 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: 0 }, arrival: { delaySeconds: 0 } } }],
  }, 8 * 60, "depart", new Date(2026, 7, 20, 12), {
    feedTimestamp: serviceMinuteEpochSeconds(new Date(2026, 7, 19, 12), 20 * 60 + 27),
    maxPredictionEpochSeconds: serviceMinuteEpochSeconds(new Date(2026, 7, 20, 12), 23 * 60),
    tripUpdates: [{ serviceDate: "2026-08-20" }],
  }, serviceMinuteEpochSeconds(new Date(2026, 7, 19, 12), 20 * 60 + 27)),
  "✓",
  "selected service date uses feed clock time when the local calendar date is one day behind",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    realtime: { departure: 17 * 60, arrival: 17 * 60 + 17 },
    legs: [{ ...newCanaanRoute.legs[0], realtime: { departure: { delaySeconds: 0 }, arrival: { delaySeconds: 0 } } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, serviceMinuteEpochSeconds(searchDate, 18 * 60)),
  "✓",
  "already-arrived live trains show arrived instead of no-delay",
);

assert.strictEqual(
  routeRealtimeStatus(newCanaanRoute, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 16 * 60 + 30) }, nowBeforeTrip),
  "◷",
  "supported Metro-North trains beyond the feed horizon show the too-far-in-advance indicator",
);

assert.strictEqual(
  routeRealtimeStatus(mixedCoverageRoute, 8 * 60, "depart", searchDate, {
    feedTimestamp: serviceMinuteEpochSeconds(searchDate, 21 * 60 + 13),
    maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 19 * 60),
    tripUpdates: [{ serviceDate: "2026-08-19" }],
  }, serviceMinuteEpochSeconds(searchDate, 21 * 60 + 13)),
  "⊙",
  "started mixed-coverage routes show partial realtime coverage instead of too-far-in-advance",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    legs: [{ ...newCanaanRoute.legs[0], fromId: "NYP", toId: "NHV", trip: { ...newCanaanTrip, agency: "Amtrak", service: "Northeast Regional", route: "Northeast Regional" } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, nowBeforeTrip),
  "⊙",
  "routes outside Metro-North realtime coverage show the unavailable-line indicator",
);

assert.strictEqual(
  routeRealtimeStatus({
    ...newCanaanRoute,
    legs: [{ ...newCanaanRoute.legs[0], fromId: "NYP", toId: "NHV", trip: { ...newCanaanTrip, agency: "Amtrak", service: "Northeast Regional", route: "Northeast Regional" } }],
  }, 16 * 60, "depart", searchDate, { maxPredictionEpochSeconds: serviceMinuteEpochSeconds(searchDate, 18 * 60) }, serviceMinuteEpochSeconds(searchDate, 18 * 60)),
  "✓",
  "already-arrived routes show arrived before realtime-unavailable coverage",
);

console.log("Metro-North realtime scope tests passed");
