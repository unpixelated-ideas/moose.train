const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({ window: {}, document: { getElementById() {}, querySelector() {} }, console });
vm.runInContext(script, context);
const run = (code) => vm.runInContext(code, context);
// Split quoted fields, escaped quotes, CRLF, and non-ASCII station names at every boundary.
const csv = 'id,name,notes\r\n1,"New, Haven","a ""quote""\nand newline"\r\n2,서울,last';
context.csv = csv;
const expected = [{ id: '1', name: 'New, Haven', notes: 'a "quote"\nand newline' }, { id: '2', name: '서울', notes: 'last' }];
for (let size = 1; size <= csv.length; size++) {
  context.chunkSize = size;
  assert.deepEqual(JSON.parse(run(`JSON.stringify((() => {
    const rows = []; const parser = createCsvParser(row => rows.push(row));
    for (let i = 0; i < csv.length; i += chunkSize) parser.push(csv.slice(i, i + chunkSize));
    parser.finish(); return rows;
  })())`)), expected);
}
run('stations = initialStations()');
for (const query of ['ans', 'Ansonia', 'ANS']) {
  context.query = query;
  assert.equal(run('stations.filter(station => stationMatchesQuery(station, query)).some(station => station.name === "Ansonia")'), true);
}
assert.equal(run('stations.filter(station => stationMatchesQuery(station, "zzzzzz")).length'), 0);
assert.equal(run('stations.filter(station => stationMatchesQuery(station, "")).length === stations.length'), true);
assert.equal(run('stations.some(station => stationMatchesQuery(station, "penn"))'), true);
assert(!/id="(?:origin|destination)"[^>]*\blist=/.test(html));
// Trip grouping must survive interleaved trains without retaining raw CSV rows.
context.fixtureRows = [
  { train_number: '1', station_id: 'GCT', station_name: 'Grand Central Terminal', station_sequence: '1', arrival_time: '08:00', departure_time: '08:00' },
  { train_number: '2', station_id: 'GCT', station_name: 'Grand Central Terminal', station_sequence: '1', arrival_time: '09:00', departure_time: '09:00' },
  { train_number: '1', station_id: 'STM', station_name: 'Stamford', station_sequence: '2', arrival_time: '09:00', departure_time: '09:00' },
  { train_number: '2', station_id: 'STM', station_name: 'Stamford', station_sequence: '2', arrival_time: '10:00', departure_time: '10:00' },
].map(row => ({ agency: 'Test', service_name: 'Test', route_name: 'Test', direction: 'North', service_days: 'daily', service_dates: '', service_start_date: '2026-09-01', service_end_date: '2026-09-30', raw_notes: '', source_pdf: 'test.csv', ...row }));
const built = JSON.parse(run(`JSON.stringify((() => {
  const builder = createTripBuilder();
  fixtureRows.forEach(builder.addRow);
  return builder.finish();
})())`));
assert.equal(built.length, 2);
assert.deepEqual(built.map(trip => trip.stops.map(stop => stop.departure)), [[480, 540], [540, 600]]);
assert(built.every(trip => !Object.hasOwn(trip, 'rows')));
console.log('Mobile station filtering, streaming CSV boundaries, and trip grouping tests passed');
