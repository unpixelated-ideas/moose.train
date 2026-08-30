const assert = require("assert");

function daylightSavingSearchTimeAdjustment(searchDate, minutes) {
  if (!searchDate || Number.isNaN(searchDate.getTime()) || typeof minutes !== "number") return null;
  const year = searchDate.getFullYear();
  const springForwardDate = nthWeekdayOfMonth(year, 2, 0, 2);
  const fallBackDate = nthWeekdayOfMonth(year, 10, 0, 1);

  if (sameLocalDate(searchDate, springForwardDate) && minutes >= 2 * 60 && minutes < 3 * 60) {
    return { minutes: 3 * 60, transition: "spring-forward" };
  }

  if (sameLocalDate(searchDate, fallBackDate) && minutes >= 1 * 60 && minutes < 2 * 60) {
    return { minutes: 2 * 60, transition: "fall-back" };
  }

  return null;
}

function nthWeekdayOfMonth(year, monthIndex, weekday, occurrence) {
  const firstOfMonth = new Date(year, monthIndex, 1);
  const offset = (weekday - firstOfMonth.getDay() + 7) % 7;
  return new Date(year, monthIndex, 1 + offset + (occurrence - 1) * 7);
}

function sameLocalDate(left, right) {
  return left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate();
}

function date(year, month, day) {
  return new Date(year, month - 1, day, 12, 0);
}

assert.deepStrictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 3, 8), 2 * 60),
  { minutes: 3 * 60, transition: "spring-forward" },
  "spring-forward 2:00 AM moves to 3:00 AM",
);

assert.deepStrictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 3, 8), 2 * 60 + 59),
  { minutes: 3 * 60, transition: "spring-forward" },
  "spring-forward 2:59 AM moves to 3:00 AM",
);

assert.strictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 3, 8), 3 * 60),
  null,
  "spring-forward 3:00 AM is already valid",
);

assert.deepStrictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 11, 1), 1 * 60),
  { minutes: 2 * 60, transition: "fall-back" },
  "fall-back 1:00 AM moves to 2:00 AM",
);

assert.deepStrictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 11, 1), 1 * 60 + 59),
  { minutes: 2 * 60, transition: "fall-back" },
  "fall-back 1:59 AM moves to 2:00 AM",
);

assert.strictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 11, 1), 2 * 60),
  null,
  "fall-back 2:00 AM is already unambiguous",
);

assert.strictEqual(
  daylightSavingSearchTimeAdjustment(date(2026, 3, 9), 2 * 60 + 30),
  null,
  "non-transition dates are unchanged",
);

console.log("daylight-saving search time tests passed");
