const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {serviceDateForGroups} = require('./helpers/service_date');
process.env.TZ = 'America/New_York';
const html = fs.readFileSync(path.resolve(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({document:{getElementById:()=>({}),querySelector(){}},window:{},console,Date});
vm.runInContext(script, context);
const calendar = vm.runInContext('({dateFromIso, localDateIso, addDays, serviceApplies})', context);
const trip = (start, end, extra = {}) => ({serviceStartDate:start, serviceEndDate:end, serviceDays:'daily', ...extra});
const select = (groups, options) => serviceDateForGroups(groups, calendar, options);

// Simulate a rolling feed dropping the old test date, even decades from now.
for (const year of [2026, 2040, 2099]) {
  assert.equal(select([[trip(`${year}-10-25`, `${year}-11-30`)]]), `${year}-10-25`);
}
// Search across gaps rather than assuming every feed starts on the same day,
// or that a shared operating day must occur within three weeks.
assert.equal(select([
  [trip('2040-01-01','2040-12-31',{serviceDates:'2040-03-01'})],
  [trip('2040-02-01','2040-12-31',{serviceDates:'2040-03-01'})],
]), '2040-03-01');
assert.equal(select([[trip('2040-02-28','2040-03-01',{rawNotes:'does not operate 2040-02-28'})]]), '2040-02-29');
const weekday = select([[trip('2040-01-01','2040-01-10')]], {weekdaysOnly:true});
assert([1,2,3,4,5].includes(calendar.dateFromIso(weekday).getDay()));
assert.throws(()=>select([[]]), /required service is missing/);
assert.throws(()=>select([[trip('2040-01-01','2040-01-02')],[trip('2040-02-01','2040-02-02')]]), /no common active service date/);
assert.throws(()=>select([[trip('2040-01-01','2040-01-02',{serviceDates:'2040-01-01'})],[trip('2040-01-01','2040-01-02',{serviceDates:'2040-01-02'})]]), /no common active service date/);
console.log('Feed-relative service dates, calendar gaps, leap days, exclusions, and missing coverage passed.');
