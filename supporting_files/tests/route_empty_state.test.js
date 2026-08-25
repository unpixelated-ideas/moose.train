const assert = require("assert");

const TRANSFER_BUFFER = 5;
const transferStationIds = new Set(["B", "C", "D", "HUB"]);

function makeLeg(fromId, toId, departure, arrival) {
  return {
    fromId,
    toId,
    departure,
    arrival,
    trip: { key: `${fromId}-${toId}-${departure}`, service: "Test", route: "Test" },
  };
}

function buildLegIndex(legs) {
  const byOrigin = new Map();
  legs.forEach((leg) => {
    if (!byOrigin.has(leg.fromId)) byOrigin.set(leg.fromId, []);
    byOrigin.get(leg.fromId).push(leg);
  });
  return byOrigin;
}

function findSupportedRoutes(originId, destinationId, legs, queryTime) {
  const legsByOrigin = buildLegIndex(legs);
  const originLegs = legsByOrigin.get(originId) || [];
  const direct = originLegs.filter((leg) => leg.toId === destinationId && leg.departure >= queryTime);
  const transfers = [];
  originLegs.forEach((firstLeg) => {
    if (!transferStationIds.has(firstLeg.toId)) return;
    (legsByOrigin.get(firstLeg.toId) || []).forEach((secondLeg) => {
      if (secondLeg.toId !== destinationId) return;
      if (secondLeg.departure < firstLeg.arrival + TRANSFER_BUFFER) return;
      transfers.push([firstLeg, secondLeg]);
    });
  });
  return [...direct, ...transfers];
}

function shortestRelaxedConnectionLegCount(originId, destinationId, legs, maxLegs = 6) {
  const legsByOrigin = buildLegIndex(legs);
  const queue = [{ stationId: originId, legCount: 0 }];
  const bestByStation = new Map([[originId, 0]]);
  while (queue.length) {
    const current = queue.shift();
    if (current.legCount >= maxLegs) continue;
    const outboundLegs = legsByOrigin.get(current.stationId) || [];
    for (const leg of outboundLegs) {
      if (current.legCount > 0 && !transferStationIds.has(current.stationId)) continue;
      const nextLegCount = current.legCount + 1;
      if (leg.toId === destinationId) return nextLegCount;
      if (!transferStationIds.has(leg.toId)) continue;
      const existing = bestByStation.get(leg.toId);
      if (existing !== undefined && existing <= nextLegCount) continue;
      bestByStation.set(leg.toId, nextLegCount);
      queue.push({ stationId: leg.toId, legCount: nextLegCount });
    }
  }
  return Infinity;
}

function emptyStateForSearch({ originId, destinationId, legs, allScheduleLegs = legs, queryTime, validInput = true, dataLoaded = true }) {
  if (!validInput) return "invalid-input";
  if (!dataLoaded) return "data-loading-error";
  const supportedRoutes = findSupportedRoutes(originId, destinationId, legs, queryTime);
  if (supportedRoutes.length) return "routes";
  const dateLegCount = shortestRelaxedConnectionLegCount(originId, destinationId, legs);
  if (!Number.isFinite(dateLegCount) || dateLegCount <= 2) return "noResults";
  const structuralLegCount = shortestRelaxedConnectionLegCount(originId, destinationId, allScheduleLegs);
  return Number.isFinite(structuralLegCount) && structuralLegCount > 2 ? "multiTransferUnsupported" : "noResults";
}

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "Z", 10, 20)],
  }),
  "routes",
  "direct trips continue to display normally",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "Z", 30, 40)],
  }),
  "routes",
  "one-transfer trips continue to display normally",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "Z", 50, 60)],
  }),
  "multiTransferUnsupported",
  "connected trips requiring two transfers show the transfer-limit message",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "D", 50, 60), makeLeg("D", "Z", 70, 80)],
  }),
  "multiTransferUnsupported",
  "connected trips requiring more than two transfers show the transfer-limit message",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("HUB", "Z", 30, 40)],
  }),
  "noResults",
  "genuinely disconnected trips keep the generic no-results message",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    validInput: false,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "Z", 50, 60)],
  }),
  "invalid-input",
  "invalid input keeps its existing behavior",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    dataLoaded: false,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "Z", 50, 60)],
  }),
  "data-loading-error",
  "data-loading errors keep their existing behavior",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "ORIGIN",
    destinationId: "DESTINATION",
    queryTime: 0,
    legs: [makeLeg("ORIGIN", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "DESTINATION", 50, 60)],
  }),
  "multiTransferUnsupported",
  "detection is based on graph connectivity rather than hard-coded station pairs",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "Z", 50, 60)],
    allScheduleLegs: [makeLeg("A", "B", 10, 20), makeLeg("B", "Z", 30, 40)],
  }),
  "noResults",
  "date-specific search failures do not show the transfer-limit message when the loaded graph has a supported route shape",
);

assert.strictEqual(
  emptyStateForSearch({
    originId: "A",
    destinationId: "Z",
    queryTime: 0,
    legs: [makeLeg("A", "B", 10, 20), makeLeg("HUB", "Z", 30, 40)],
    allScheduleLegs: [makeLeg("A", "B", 10, 20), makeLeg("B", "C", 30, 40), makeLeg("C", "Z", 50, 60)],
  }),
  "noResults",
  "date restrictions keep the generic no-results message when no date-valid relaxed path exists",
);

console.log("route empty-state tests passed");
