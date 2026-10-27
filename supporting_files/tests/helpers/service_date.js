// Integration tests use the calendars in their input, never a fixed date or
// the machine's clock. Freshness is checked separately by validate_refresh.py.
function serviceDateForGroups(groups, calendar, {label = 'schedule', weekdaysOnly = false} = {}) {
  if (!groups.length || groups.some(group => !group.length)) {
    throw new Error(`${label}: required service is missing`);
  }
  const datesFor = trip => [trip.serviceStartDate, trip.serviceEndDate,
    ...(trip.serviceDates || '').split(',')].filter(value => /^\d{4}-\d{2}-\d{2}$/.test(value));
  const bounds = groups.map(group => group.flatMap(datesFor).sort());
  if (bounds.some(dates => !dates.length)) throw new Error(`${label}: service has no dated calendar`);
  const first = bounds.map(dates => dates[0]).sort().at(-1);
  const last = bounds.map(dates => dates.at(-1)).sort()[0];
  for (let date = calendar.dateFromIso(first); calendar.localDateIso(date) <= last; date = calendar.addDays(date, 1)) {
    if (weekdaysOnly && (date.getDay() === 0 || date.getDay() === 6)) continue;
    if (groups.every(group => group.some(trip => calendar.serviceApplies(trip, date)))) {
      return calendar.localDateIso(date);
    }
  }
  throw new Error(`${label}: no common active service date in ${first}..${last}`);
}

module.exports = {serviceDateForGroups};
