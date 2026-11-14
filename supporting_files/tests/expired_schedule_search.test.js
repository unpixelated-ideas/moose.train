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
const state = vm.runInContext(`emptyStateForSearch({id:'NYC_RAIL'}, {id:'LIRR_1'}, dateFromIso('2026-11-14'), 660, 'leave')`, context, {timeout:10000});
assert.equal(state.key, 'dataBeyondRange');
assert.equal(state.searchDate, '2026-11-08');
console.log('Expired Albertson schedule returns coverage message without freezing.');
