const assert = require("assert");

const TRANSIT_TIME_ZONE = "America/New_York";

const translations = {
  en: {
    timezoneNoticeTimes: "Your time: {localTime} · U.S. Eastern time: {easternTime}",
    timezoneNoticeDateTime: "{date}, {time}",
  },
  ko: {
    timezoneNoticeTimes: "현재 내 시간: {localTime} · 미국 동부 시간: {easternTime}",
    timezoneNoticeDateTime: "{date} {time}",
  },
  es: {
    timezoneNoticeTimes: "Tu hora: {localTime} · Hora del este de EE. UU.: {easternTime}",
    timezoneNoticeDateTime: "{date}, {time}",
  },
};

let currentLanguage = "en";
let timeFormat = "12";

function shouldShowTimezoneNotice(timeZone, dismissed = false) {
  return Boolean(timeZone && timeZone !== TRANSIT_TIME_ZONE && !dismissed);
}

function t(key, values = {}) {
  let text = (translations[currentLanguage] && translations[currentLanguage][key]) || translations.en[key] || key;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replace(`{${name}}`, value);
  });
  return text;
}

function timezoneNoticeTimes(now, visitorTimeZone) {
  return t("timezoneNoticeTimes", {
    localTime: formatTimeInTimeZone(now, visitorTimeZone),
    easternTime: formatTimeInTimeZone(now, TRANSIT_TIME_ZONE),
  });
}

function formatTimeInTimeZone(date, timeZone) {
  const parts = dateTimePartsForZone(date, timeZone);
  if (!parts) return "";
  return t("timezoneNoticeDateTime", {
    date: formatDisplayDate(dateIsoFromParts(parts)),
    time: formatInputTime(parts.hour * 60 + parts.minute),
  });
}

function dateTimePartsForZone(date, timeZone) {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
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
  } catch (_error) {
    return null;
  }
}

function formatInputTime(total) {
  if (timeFormat !== "12") return formatTwentyFourHour(total);
  const normalized = normalizeMinuteOfDay(total);
  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;
  const hour12 = hours % 12 || 12;
  const period = localizedPeriod(hours >= 12 ? "PM" : "AM");
  if (currentLanguage === "ko") return `${period} ${hour12}:${String(minutes).padStart(2, "0")}`;
  return `${hour12}:${String(minutes).padStart(2, "0")} ${period}`;
}

function formatTwentyFourHour(total) {
  const normalized = normalizeMinuteOfDay(total);
  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function normalizeMinuteOfDay(total) {
  return ((total % 1440) + 1440) % 1440;
}

function localizedPeriod(period) {
  if (currentLanguage === "ko") return period === "AM" ? "오전" : "오후";
  if (currentLanguage === "es") return period === "AM" ? "a. m." : "p. m.";
  return period;
}

function formatDisplayDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat(currentLanguage, {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

function dateIsoFromParts(parts) {
  return [
    parts.year,
    String(parts.month).padStart(2, "0"),
    String(parts.day).padStart(2, "0"),
  ].join("-");
}

const sampleNow = new Date("2026-08-30T19:30:00Z");

assert.strictEqual(
  shouldShowTimezoneNotice("America/New_York"),
  false,
  "Eastern visitors do not see the timezone notice",
);

assert.strictEqual(
  shouldShowTimezoneNotice("America/Los_Angeles"),
  true,
  "non-Eastern visitors see the timezone notice",
);

assert.strictEqual(
  shouldShowTimezoneNotice(""),
  false,
  "missing browser timezone hides the notice",
);

assert.strictEqual(
  shouldShowTimezoneNotice("America/Los_Angeles", true),
  false,
  "dismissed notice stays hidden",
);

currentLanguage = "en";
timeFormat = "12";
assert.strictEqual(
  timezoneNoticeTimes(sampleNow, "America/Los_Angeles"),
  "Your time: August 30, 2026, 12:30 PM · U.S. Eastern time: August 30, 2026, 3:30 PM",
  "English AM/PM notice uses the selected language and 12-hour format",
);

currentLanguage = "ko";
assert.strictEqual(
  timezoneNoticeTimes(sampleNow, "America/Los_Angeles"),
  "현재 내 시간: 2026년 8월 30일 오후 12:30 · 미국 동부 시간: 2026년 8월 30일 오후 3:30",
  "Korean notice updates copy and AM/PM periods",
);

currentLanguage = "es";
assert.strictEqual(
  timezoneNoticeTimes(sampleNow, "America/Los_Angeles"),
  "Tu hora: 30 de agosto de 2026, 12:30 p. m. · Hora del este de EE. UU.: 30 de agosto de 2026, 3:30 p. m.",
  "Spanish notice updates copy and AM/PM periods",
);

timeFormat = "24";
assert.strictEqual(
  timezoneNoticeTimes(sampleNow, "America/Los_Angeles"),
  "Tu hora: 30 de agosto de 2026, 12:30 · Hora del este de EE. UU.: 30 de agosto de 2026, 15:30",
  "24-hour preference changes both displayed times",
);

console.log("timezone notice tests passed");
