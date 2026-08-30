const assert = require("assert");

const DEBUG_PASSWORDS = new Set(["youareamoose", "you are a moose"]);
const DEBUG_TIME_ZONES = [
  { label: "Samoa Standard Time (SST)", timeZone: "Pacific/Pago_Pago" },
  { label: "Hawaii-Aleutian Standard Time (HST/HAST)", timeZone: "Pacific/Honolulu" },
  { label: "Alaska Standard Time (AKST)", timeZone: "America/Anchorage" },
  { label: "U.S. Pacific Standard Time (PST)", timeZone: "America/Los_Angeles" },
  { label: "U.S. Mountain Standard Time (MST)", timeZone: "America/Denver" },
  { label: "U.S. Central Standard Time (CST)", timeZone: "America/Chicago" },
  { label: "U.S. Eastern Standard Time (EST)", timeZone: "America/New_York" },
  { label: "Atlantic Standard Time (AST)", timeZone: "America/Puerto_Rico" },
  { label: "Ireland Time (GMT/IST)", timeZone: "Europe/Dublin" },
  { label: "Korea Standard Time (KST)", timeZone: "Asia/Seoul" },
  { label: "Chamorro Standard Time (ChST)", timeZone: "Pacific/Guam" },
];

function isDebugPassword(password) {
  return DEBUG_PASSWORDS.has(String(password || "").trim().toLowerCase());
}

function shouldShowDebugExperience(currentLanguage) {
  return currentLanguage === "en";
}

function shouldShowTimezoneNotice(timeZone, dismissed = false, debugTimeZone = "") {
  return Boolean(timeZone && timeZone !== "America/New_York" && (debugTimeZone || !dismissed));
}

function storedDebugTimeZone(savedTimeZone) {
  return DEBUG_TIME_ZONES.some((item) => item.timeZone === savedTimeZone) ? savedTimeZone : "";
}

assert.strictEqual(isDebugPassword("youareamoose"), true, "compact password works");
assert.strictEqual(isDebugPassword("YouAreAMoose"), true, "compact password is case insensitive");
assert.strictEqual(isDebugPassword(" you are a moose "), true, "spaced password accepts trim and mixed spacing form");
assert.strictEqual(isDebugPassword("you areamoose"), false, "near-miss password is rejected");
assert.strictEqual(isDebugPassword(null), false, "cancelled prompt is rejected");

assert.strictEqual(shouldShowDebugExperience("en"), true, "debug entry is present in English");
assert.strictEqual(shouldShowDebugExperience("ko"), false, "debug entry is absent in Korean");
assert.strictEqual(shouldShowDebugExperience("es"), false, "debug entry is absent in Spanish");

assert.strictEqual(
  shouldShowTimezoneNotice("Asia/Seoul", true, "Asia/Seoul"),
  true,
  "debug timezone override shows the banner even after a previous dismissal",
);
assert.strictEqual(
  shouldShowTimezoneNotice("America/New_York", true, "America/New_York"),
  false,
  "debug Eastern override does not show the banner",
);

assert.strictEqual(storedDebugTimeZone("Pacific/Guam"), "Pacific/Guam", "known timezone override is accepted");
assert.strictEqual(storedDebugTimeZone("Etc/GMT+12"), "", "unknown timezone override is ignored");
assert.strictEqual(DEBUG_TIME_ZONES.length, 11, "all requested timezone options are present");

console.log("debug menu tests passed");
