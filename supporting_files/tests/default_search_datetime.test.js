const assert = require("assert");

const TRANSIT_TIME_ZONE = "America/New_York";

function localDateIso(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultSearchDateTime(now = new Date()) {
  const nowParts = transitDateTimeParts(now);
  const currentDate = dateIsoFromParts(nowParts);
  const currentMinutes = nowParts.hour * 60 + nowParts.minute;
  if (currentMinutes >= 23 * 60 + 59) {
    const tomorrow = new Date(nowParts.year, nowParts.month - 1, nowParts.day + 1);
    return { date: localDateIso(tomorrow), minutes: 1 };
  }
  if (currentMinutes >= 23 * 60 + 45) {
    return { date: currentDate, minutes: currentMinutes };
  }
  if (currentMinutes >= 23 * 60) {
    return { date: currentDate, minutes: 23 * 60 + 45 };
  }
  return {
    date: currentDate,
    minutes: (nowParts.hour + 1) * 60,
  };
}

function transitDateTimeParts(date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: TRANSIT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute),
  };
}

function dateIsoFromParts(parts) {
  return [
    parts.year,
    String(parts.month).padStart(2, "0"),
    String(parts.day).padStart(2, "0"),
  ].join("-");
}

function at(hour, minute, day = 30) {
  return new Date(2026, 7, day, hour, minute);
}

assert.deepStrictEqual(
  defaultSearchDateTime(at(15, 23)),
  { date: "2026-08-30", minutes: 16 * 60 },
  "midday openings default to the next hour",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(0, 5)),
  { date: "2026-08-30", minutes: 60 },
  "after midnight openings default to the next hour on the same date",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(22, 59)),
  { date: "2026-08-30", minutes: 23 * 60 },
  "before 11 PM openings can still default to 11 PM",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(23, 0)),
  { date: "2026-08-30", minutes: 23 * 60 + 45 },
  "11 PM through 11:44 PM default to 11:45 PM",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(23, 45)),
  { date: "2026-08-30", minutes: 23 * 60 + 45 },
  "11:45 PM openings stay at 11:45 PM",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(23, 46)),
  { date: "2026-08-30", minutes: 23 * 60 + 46 },
  "after 11:45 PM openings stay at the current time",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(23, 58)),
  { date: "2026-08-30", minutes: 23 * 60 + 58 },
  "late 11:50s openings before 11:59 stay at the current time",
);

assert.deepStrictEqual(
  defaultSearchDateTime(at(23, 59)),
  { date: "2026-08-31", minutes: 1 },
  "11:59 PM openings roll to 12:01 AM on the following date",
);

console.log("default search date/time tests passed");
