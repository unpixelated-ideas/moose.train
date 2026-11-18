// Regression: NYC → Albertson after LIRR coverage expires must not rescan
// the entire schedule for every possible first train and transfer station.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({document:{getElementById:()=>({}),querySelector(){}},window:{},Date,console});
vm.runInContext(script, context);
context.data = JSON.parse(fs.readFileSync(path.join(root, 'supporting_files/assets/schedule/search.json'), 'utf8'));
vm.runInContext('trips = decodeSearchSchedule(data).trips', context);
const coverageEnd = vm.runInContext("maxIsoDate(...trips.filter(trip => trip.stops.some(stop => stop.id === 'LIRR_1')).map(maxServiceDateForTrip))", context, {timeout:10000});
assert.match(coverageEnd, /^\d{4}-\d{2}-\d{2}$/);
const expired = new Date(Date.parse(coverageEnd) + 7 * 86400000).toISOString().slice(0, 10);
context.expired = expired;
const state = vm.runInContext(`emptyStateForSearch({id:'NYC_RAIL'}, {id:'LIRR_1'}, dateFromIso(expired), 660, 'leave')`, context, {timeout:10000});
assert.equal(state.key, 'dataBeyondRange');
assert.equal(state.searchDate, coverageEnd);
console.log('Expired Albertson schedule returns coverage message without freezing.');
