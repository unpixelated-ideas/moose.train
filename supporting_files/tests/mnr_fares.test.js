const assert = require("assert");

const FARE_PASSENGER_CATEGORY = { ADULT: "ADULT" };
const FARE_PEAK_STATUS = { PEAK: "PEAK", OFF_PEAK: "OFF_PEAK" };
const FARE_TYPE = { ORDINARY_ONE_WAY: "ORDINARY_ONE_WAY", CITYTICKET: "CITYTICKET" };
const CTRAIL_FARE_PRODUCTS = {
  HARTFORD_LINE: "ctrail-hartford-line",
};
const MNR_FARE_DATA = {
  cityTicket: {
    peak: 7.25,
    offPeak: 5.25,
    eligibleStationIds: new Set(["GCT", "H125", "FOR"]),
  },
  stationZones: new Map([
    ["GCT", "1"],
    ["H125", "1"],
    ["FOR", "11"],
    ["STM", "16"],
    ["NHV", "21"],
    ["STS", "21"],
    ["BRP", "19"],
    ["WBY", "51"],
  ]),
  terminalOneWay: new Map(Object.entries({
    "11": { peak: 7.25, offPeak: 5.25 },
    "16": { peak: 17.75, offPeak: 13.25 },
    "21": { peak: 27.25, offPeak: 20.25 },
    "51": { peak: 24.25, offPeak: 18.00 },
  })),
  intermediateOneWay: new Map([
    ["16:21", 9.50],
    ["19:51", 3.50],
  ]),
};
const CTRAIL_FARE_DATA = {
  stationAliases: new Map(),
  products: {
    [CTRAIL_FARE_PRODUCTS.HARTFORD_LINE]: {
      stationIds: ["NHV", "WFD", "MDN", "BER", "HFD"],
      oneWayCents: new Map([
        ["HFD:NHV", 925],
        ["HFD:WFD", 625],
      ]),
    },
  },
};

function normalize(value) {
  return String(value || "").toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, " ").trim();
}

function metroNorthPeakStatusFromNotes(notes) {
  const match = String(notes || "").match(/(?:^|;\s*)peak_offpeak=([01])(?:;|$)/);
  if (!match) return "";
  return match[1] === "1" ? FARE_PEAK_STATUS.PEAK : FARE_PEAK_STATUS.OFF_PEAK;
}

function calculateMetroNorthFare(request) {
  const passengerCategory = request?.passengerCategory || FARE_PASSENGER_CATEGORY.ADULT;
  if (passengerCategory !== FARE_PASSENGER_CATEGORY.ADULT) return null;
  const originStationId = String(request?.originStationId || "").trim();
  const destinationStationId = String(request?.destinationStationId || "").trim();
  if (!originStationId || !destinationStationId || originStationId === destinationStationId) return null;
  const peakStatus = request?.peakStatus;
  if (![FARE_PEAK_STATUS.PEAK, FARE_PEAK_STATUS.OFF_PEAK].includes(peakStatus)) return null;
  const originZone = MNR_FARE_DATA.stationZones.get(originStationId);
  const destinationZone = MNR_FARE_DATA.stationZones.get(destinationStationId);
  if (!originZone || !destinationZone) return null;

  const isPeak = peakStatus === FARE_PEAK_STATUS.PEAK;
  if (isMetroNorthCityTicketEligible(originStationId, destinationStationId)) {
    return {
      amount: isPeak ? MNR_FARE_DATA.cityTicket.peak : MNR_FARE_DATA.cityTicket.offPeak,
      fareType: FARE_TYPE.CITYTICKET,
      peakStatus,
      passengerCategory,
    };
  }

  const terminalZone = originZone === "1" ? destinationZone : destinationZone === "1" ? originZone : "";
  if (terminalZone) {
    const fares = MNR_FARE_DATA.terminalOneWay.get(terminalZone);
    if (!fares) return null;
    return {
      amount: isPeak ? fares.peak : fares.offPeak,
      fareType: FARE_TYPE.ORDINARY_ONE_WAY,
      peakStatus,
      passengerCategory,
    };
  }

  const amount = MNR_FARE_DATA.intermediateOneWay.get(fareZonePairKey(originZone, destinationZone));
  if (typeof amount !== "number") return null;
  return {
    amount,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    peakStatus,
    passengerCategory,
  };
}

function calculateRouteFare(route, passengerCategory = FARE_PASSENGER_CATEGORY.ADULT) {
  if (!route || !route.legs.length) return null;
  if (route.legs.every(isMetroNorthFareLeg)) return calculateMetroNorthRouteFare(route, passengerCategory);
  const ctrailProduct = ctrailFareProductForLegs(route.legs);
  if (ctrailProduct) {
    return calculateCTrailFare({
      product: ctrailProduct,
      originStationId: route.legs[0].fromId,
      destinationStationId: route.legs[route.legs.length - 1].toId,
      passengerCategory,
    });
  }
  return calculateCombinedLegFare(route.legs, passengerCategory);
}

function calculateMetroNorthRouteFare(route, passengerCategory = FARE_PASSENGER_CATEGORY.ADULT) {
  const peakStatus = metroNorthFarePeakStatusForLegs(route.legs);
  if (!peakStatus) return null;
  return calculateMetroNorthFare({
    originStationId: route.legs[0].fromId,
    destinationStationId: route.legs[route.legs.length - 1].toId,
    peakStatus,
    passengerCategory,
  });
}

function calculateCombinedLegFare(legs, passengerCategory = FARE_PASSENGER_CATEGORY.ADULT) {
  const legFares = legs.map((leg) => calculateLegFare(leg, passengerCategory));
  if (!legFares.length || legFares.some((fare) => !fare)) return null;
  const totalCents = legFares.reduce((sum, fare) => sum + fareAmountCents(fare), 0);
  if (!Number.isInteger(totalCents)) return null;
  return {
    amountCents: totalCents,
    currency: "USD",
    passengerCategory,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    componentFares: legFares,
  };
}

function calculateLegFare(leg, passengerCategory = FARE_PASSENGER_CATEGORY.ADULT) {
  if (isMetroNorthFareLeg(leg)) {
    const peakStatus = metroNorthFarePeakStatusForLegs([leg]);
    if (!peakStatus) return null;
    return calculateMetroNorthFare({
      originStationId: leg.fromId,
      destinationStationId: leg.toId,
      peakStatus,
      passengerCategory,
    });
  }
  const ctrailProduct = ctrailFareProductForLegs([leg]);
  if (!ctrailProduct) return null;
  return calculateCTrailFare({
    product: ctrailProduct,
    originStationId: leg.fromId,
    destinationStationId: leg.toId,
    passengerCategory,
  });
}

function calculateCTrailFare(request) {
  const passengerCategory = request?.passengerCategory || FARE_PASSENGER_CATEGORY.ADULT;
  if (passengerCategory !== FARE_PASSENGER_CATEGORY.ADULT) return null;
  const product = CTRAIL_FARE_DATA.products[request?.product];
  if (!product) return null;
  const originStationId = String(request?.originStationId || "").trim();
  const destinationStationId = String(request?.destinationStationId || "").trim();
  if (!product.stationIds.includes(originStationId) || !product.stationIds.includes(destinationStationId)) return null;
  const amountCents = product.oneWayCents.get(stationPairKey(originStationId, destinationStationId));
  if (!Number.isInteger(amountCents)) return null;
  return {
    amountCents,
    currency: "USD",
    passengerCategory,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    product: request.product,
  };
}

function ctrailFareProductForLegs(legs) {
  const legProducts = legs.map(ctrailFareProductForLeg);
  if (!legProducts.length || legProducts.some((product) => !product)) return "";
  const products = new Set(legProducts);
  return products.size === 1 ? Array.from(products)[0] : "";
}

function ctrailFareProductForLeg(leg) {
  const text = normalize(`${leg.trip?.service || ""} ${leg.trip?.route || ""}`);
  return text.includes("hartford line") ? CTRAIL_FARE_PRODUCTS.HARTFORD_LINE : "";
}

function isMetroNorthCityTicketEligible(originStationId, destinationStationId) {
  return MNR_FARE_DATA.cityTicket.eligibleStationIds.has(originStationId) &&
    MNR_FARE_DATA.cityTicket.eligibleStationIds.has(destinationStationId);
}

function fareZonePairKey(originZone, destinationZone) {
  return [String(originZone), String(destinationZone)].sort((a, b) => Number(a) - Number(b)).join(":");
}

function stationPairKey(originStationId, destinationStationId) {
  return [String(originStationId), String(destinationStationId)].sort().join(":");
}

function fareAmountCents(fare) {
  if (!fare) return NaN;
  if (Number.isInteger(fare.amountCents)) return fare.amountCents;
  if (typeof fare.amount === "number") return Math.round(fare.amount * 100);
  return NaN;
}

function isMetroNorthFareLeg(leg) {
  return normalize(leg?.trip?.agency) === "metro north";
}

function metroNorthFarePeakStatusForLegs(legs) {
  const statuses = new Set(legs.map((leg) => leg.trip.farePeakStatus).filter(Boolean));
  return statuses.size === 1 ? Array.from(statuses)[0] : "";
}

assert.strictEqual(metroNorthPeakStatusFromNotes("GTFS; peak_offpeak=1; gtfs_trip_id=x"), FARE_PEAK_STATUS.PEAK);
assert.strictEqual(metroNorthPeakStatusFromNotes("GTFS; peak_offpeak=0; gtfs_trip_id=x"), FARE_PEAK_STATUS.OFF_PEAK);

assert.deepStrictEqual(
  calculateMetroNorthFare({
    originStationId: "GCT",
    destinationStationId: "NHV",
    peakStatus: FARE_PEAK_STATUS.PEAK,
    passengerCategory: FARE_PASSENGER_CATEGORY.ADULT,
  }),
  {
    amount: 27.25,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    peakStatus: FARE_PEAK_STATUS.PEAK,
    passengerCategory: FARE_PASSENGER_CATEGORY.ADULT,
  },
);

assert.deepStrictEqual(
  calculateMetroNorthFare({
    originStationId: "NHV",
    destinationStationId: "GCT",
    peakStatus: FARE_PEAK_STATUS.OFF_PEAK,
  }),
  {
    amount: 20.25,
    fareType: FARE_TYPE.ORDINARY_ONE_WAY,
    peakStatus: FARE_PEAK_STATUS.OFF_PEAK,
    passengerCategory: FARE_PASSENGER_CATEGORY.ADULT,
  },
);

assert.strictEqual(
  calculateMetroNorthFare({
    originStationId: "FOR",
    destinationStationId: "GCT",
    peakStatus: FARE_PEAK_STATUS.OFF_PEAK,
  }).fareType,
  FARE_TYPE.CITYTICKET,
);

assert.strictEqual(
  calculateMetroNorthFare({
    originStationId: "NHV",
    destinationStationId: "STM",
    peakStatus: FARE_PEAK_STATUS.PEAK,
  }).amount,
  9.50,
  "intermediate New Haven fares use the published matrix and remain direction-independent",
);

assert.strictEqual(
  calculateMetroNorthFare({
    originStationId: "GCT",
    destinationStationId: "NHV",
    peakStatus: FARE_PEAK_STATUS.PEAK,
    passengerCategory: "SENIOR",
  }),
  null,
  "unsupported passenger categories do not fall through to adult fares",
);

assert.strictEqual(
  calculateRouteFare({
    legs: [
      { fromId: "GCT", toId: "BRP", trip: { agency: "Metro-North", farePeakStatus: FARE_PEAK_STATUS.PEAK } },
      { fromId: "BRP", toId: "WBY", trip: { agency: "Metro-North", farePeakStatus: FARE_PEAK_STATUS.OFF_PEAK } },
    ],
  }),
  null,
  "mixed peak/off-peak Metro-North routes are left unsupported rather than guessed",
);

assert.strictEqual(
  calculateRouteFare({
    legs: [
      { fromId: "GCT", toId: "NHV", trip: { agency: "Metro-North", farePeakStatus: FARE_PEAK_STATUS.OFF_PEAK } },
      { fromId: "NHV", toId: "HFD", trip: { agency: "CTrail", service: "Hartford Line", route: "Hartford Line" } },
    ],
  }).amountCents,
  2950,
  "mixed supported trips show a total built from leg fares",
);

assert.strictEqual(
  calculateRouteFare({
    legs: [
      { fromId: "GCT", toId: "NHV", trip: { agency: "Amtrak", service: "Northeast Regional", route: "Northeast Regional" } },
      { fromId: "NHV", toId: "HFD", trip: { agency: "CTrail", service: "Hartford Line", route: "Hartford Line" } },
    ],
  }),
  null,
  "mixed trips with an unsupported leg do not show a route total",
);

assert.strictEqual(
  calculateLegFare({
    fromId: "NHV",
    toId: "HFD",
    trip: { agency: "CTrail", service: "Hartford Line", route: "Hartford Line" },
  }).amountCents,
  925,
  "supported legs still expose their own fare when another leg is unsupported",
);

console.log("mnr fare tests passed");
