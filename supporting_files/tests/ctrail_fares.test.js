const assert = require("assert");

const FARE_PASSENGER_CATEGORY = { ADULT: "ADULT", SENIOR: "SENIOR" };
const FARE_TYPE = { ORDINARY_ONE_WAY: "ORDINARY_ONE_WAY" };
const CTRAIL_FARE_PRODUCTS = {
  SHORE_LINE_EAST: "ctrail-shore-line-east",
  HARTFORD_LINE: "ctrail-hartford-line",
};
const CTRAIL_FARE_DATA = {
  metadata: {
    sourceName: "CTrail fare tables",
    effectiveDate: "2026-07-01",
    lastUpdated: "2026-09-01",
  },
  stationAliases: new Map([["STS", "NHV"]]),
  products: {
    [CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST]: {
      name: "CTrail Shore Line East",
      stationIds: ["NHV", "BRA", "GUI", "MAD", "CLIN", "WBK", "OSB", "NLC"],
      oneWayCents: new Map(),
    },
    [CTRAIL_FARE_PRODUCTS.HARTFORD_LINE]: {
      name: "CTrail Hartford Line",
      stationIds: ["NHV", "WFD", "MDN", "BER", "HFD", "WND", "WNL", "SPG"],
      oneWayCents: new Map(),
    },
  },
};

function addStationPairFares(productKey, destinationStationId, fares) {
  const product = CTRAIL_FARE_DATA.products[productKey];
  const destinationIndex = product.stationIds.indexOf(destinationStationId);
  assert(destinationIndex > 0, `unknown destination station ${destinationStationId}`);
  fares.forEach((amountCents, index) => {
    product.oneWayCents.set(stationPairKey(product.stationIds[index], destinationStationId), amountCents);
  });
}

[
  ["BRA", [400]],
  ["GUI", [500, 400]],
  ["MAD", [575, 400, 400]],
  ["CLIN", [650, 525, 525, 525]],
  ["WBK", [725, 525, 525, 525, 400]],
  ["OSB", [850, 525, 525, 525, 400, 400]],
  ["NLC", [1175, 850, 850, 850, 525, 525, 525]],
].forEach(([stationId, fares]) => addStationPairFares(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, stationId, fares));

[
  ["WFD", [425]],
  ["MDN", [550, 350]],
  ["BER", [675, 425, 350]],
  ["HFD", [925, 625, 525, 400]],
  ["WND", [1050, 750, 650, 525, 350]],
  ["WNL", [1150, 875, 725, 600, 400, 350]],
  ["SPG", [1475, 1175, 1050, 925, 675, 550, 475]],
].forEach(([stationId, fares]) => addStationPairFares(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, stationId, fares));

function normalize(value) {
  return String(value || "").toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

function stationPairKey(originStationId, destinationStationId) {
  return [String(originStationId), String(destinationStationId)].sort().join(":");
}

function normalizeCTrailFareStationId(stationId) {
  const clean = String(stationId || "").trim();
  return CTRAIL_FARE_DATA.stationAliases.get(clean) || clean;
}

function ctrailFareProductForLeg(leg) {
  const text = normalize(`${leg.trip?.service || ""} ${leg.trip?.route || ""}`);
  if (text.includes("shore line east")) return CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST;
  if (text.includes("hartford line") || text.includes("amtrak hartford line")) return CTRAIL_FARE_PRODUCTS.HARTFORD_LINE;
  return "";
}

function ctrailFareProductForLegs(legs) {
  const products = new Set(legs.map(ctrailFareProductForLeg).filter(Boolean));
  return products.size === 1 ? Array.from(products)[0] : "";
}

function calculateCTrailFare(request) {
  const passengerCategory = request?.passengerCategory || FARE_PASSENGER_CATEGORY.ADULT;
  if (passengerCategory !== FARE_PASSENGER_CATEGORY.ADULT) return null;
  const product = CTRAIL_FARE_DATA.products[request?.product];
  if (!product) return null;
  const originStationId = normalizeCTrailFareStationId(request?.originStationId);
  const destinationStationId = normalizeCTrailFareStationId(request?.destinationStationId);
  if (!originStationId || !destinationStationId || originStationId === destinationStationId) return null;
  if (!product.stationIds.includes(originStationId) || !product.stationIds.includes(destinationStationId)) return null;
  const amountCents = product.oneWayCents.get(stationPairKey(originStationId, destinationStationId));
  if (!Number.isInteger(amountCents)) return null;
  return {
    amountCents,
    currency: "USD",
    passengerCategory,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    product: request.product,
    sourceEffectiveDate: CTRAIL_FARE_DATA.metadata.effectiveDate,
  };
}

function calculateRouteFare(route, passengerCategory = FARE_PASSENGER_CATEGORY.ADULT) {
  if (!route || !route.legs.length) return null;
  const product = ctrailFareProductForLegs(route.legs);
  if (!product) return null;
  return calculateCTrailFare({
    product,
    originStationId: route.legs[0].fromId,
    destinationStationId: route.legs[route.legs.length - 1].toId,
    passengerCategory,
  });
}

function formatFareAmount(fare) {
  const amount = Number.isInteger(fare.amountCents) ? fare.amountCents / 100 : fare.amount;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: fare.currency || "USD" }).format(amount);
}

function renderFareSummary(fare) {
  if (!fare) return "";
  return [formatFareAmount(fare), "standard one-way fare"].join(" · ");
}

function renderRoute(route) {
  const fare = calculateRouteFare(route);
  return `<article>${fare ? renderFareSummary(fare) : ""}<div>${route.legs.length} leg</div></article>`;
}

function makeLeg(productName, fromId, toId, extraTrip = {}) {
  return {
    fromId,
    toId,
    trip: {
      agency: "CTrail",
      service: productName,
      route: productName,
      farePeakStatus: "PEAK",
      ...extraTrip,
    },
  };
}

function expectFare(product, fromId, toId, cents) {
  const fare = calculateCTrailFare({ product, originStationId: fromId, destinationStationId: toId });
  assert(fare, `${fromId}-${toId} should have a fare`);
  assert.strictEqual(fare.amountCents, cents);
  assert.strictEqual(calculateCTrailFare({ product, originStationId: toId, destinationStationId: fromId }).amountCents, cents);
}

const expectedSle = [
  ["BRA", [400]],
  ["GUI", [500, 400]],
  ["MAD", [575, 400, 400]],
  ["CLIN", [650, 525, 525, 525]],
  ["WBK", [725, 525, 525, 525, 400]],
  ["OSB", [850, 525, 525, 525, 400, 400]],
  ["NLC", [1175, 850, 850, 850, 525, 525, 525]],
];
const expectedHartford = [
  ["WFD", [425]],
  ["MDN", [550, 350]],
  ["BER", [675, 425, 350]],
  ["HFD", [925, 625, 525, 400]],
  ["WND", [1050, 750, 650, 525, 350]],
  ["WNL", [1150, 875, 725, 600, 400, 350]],
  ["SPG", [1475, 1175, 1050, 925, 675, 550, 475]],
];

expectedSle.forEach(([destination, fares]) => {
  const stations = CTRAIL_FARE_DATA.products[CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST].stationIds;
  fares.forEach((cents, index) => expectFare(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, stations[index], destination, cents));
});
expectedHartford.forEach(([destination, fares]) => {
  const stations = CTRAIL_FARE_DATA.products[CTRAIL_FARE_PRODUCTS.HARTFORD_LINE].stationIds;
  fares.forEach((cents, index) => expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, stations[index], destination, cents));
});

assert.strictEqual(CTRAIL_FARE_DATA.products[CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST].oneWayCents.size, 28);
assert.strictEqual(CTRAIL_FARE_DATA.products[CTRAIL_FARE_PRODUCTS.HARTFORD_LINE].oneWayCents.size, 28);

expectFare(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, "NHV", "BRA", 400);
expectFare(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, "NHV", "OSB", 850);
expectFare(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, "OSB", "NLC", 525);
expectFare(CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, "NHV", "NLC", 1175);

expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, "NHV", "WFD", 425);
expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, "NHV", "HFD", 925);
expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, "HFD", "SPG", 675);
expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, "WNL", "SPG", 475);
expectFare(CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, "NHV", "SPG", 1475);

assert.strictEqual(calculateCTrailFare({ product: CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, originStationId: "STS", destinationStationId: "HFD" }).amountCents, 925);
assert.strictEqual(calculateCTrailFare({ product: CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, originStationId: "STS", destinationStationId: "BRA" }).amountCents, 400);
assert.strictEqual(calculateCTrailFare({ product: CTRAIL_FARE_PRODUCTS.SHORE_LINE_EAST, originStationId: "NHV", destinationStationId: "HFD" }), null);
assert.strictEqual(calculateCTrailFare({ product: CTRAIL_FARE_PRODUCTS.HARTFORD_LINE, originStationId: "NHV", destinationStationId: "SPG", passengerCategory: FARE_PASSENGER_CATEGORY.SENIOR }), null);

const sleRoute = { legs: [makeLeg("Shore Line East", "NHV", "NLC")] };
assert.strictEqual(calculateRouteFare(sleRoute).amountCents, 1175);
assert.strictEqual(calculateRouteFare(sleRoute).sourceEffectiveDate, "2026-07-01");

const hartfordAmtrakRoute = {
  legs: [makeLeg("Amtrak Hartford Line", "NHV", "SPG", { agency: "Amtrak" })],
};
assert.strictEqual(calculateRouteFare(hartfordAmtrakRoute).amountCents, 1475);

const unsupportedAmtrakRoute = {
  legs: [makeLeg("Northeast Regional", "NHV", "SPG", { agency: "Amtrak" })],
};
assert.strictEqual(calculateRouteFare(unsupportedAmtrakRoute), null);

const connectingRoute = {
  legs: [
    makeLeg("Shore Line East", "NLC", "NHV"),
    makeLeg("Hartford Line", "NHV", "SPG"),
  ],
};
assert.strictEqual(calculateRouteFare(connectingRoute), null);
assert.strictEqual(renderRoute(connectingRoute), "<article><div>2 leg</div></article>");

["en", "es", "ko"].forEach(() => {
  assert.strictEqual(formatFareAmount({ amountCents: 425, currency: "USD" }), "$4.25");
});
assert.strictEqual(formatFareAmount({ amountCents: 850, currency: "USD" }), "$8.50");
assert.strictEqual(renderFareSummary(calculateRouteFare(sleRoute)), "$11.75 · standard one-way fare");
assert.strictEqual(makeLeg("Hartford Line", "NHV", "HFD").trip.farePeakStatus, "PEAK");
assert.strictEqual(calculateRouteFare({ legs: [makeLeg("Hartford Line", "NHV", "HFD")] }).amountCents, 925);

console.log("CTrail fare tests passed");
