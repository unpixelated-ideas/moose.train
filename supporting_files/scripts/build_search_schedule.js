// Run after updating the CSV or trip preparation logic: node supporting_files/scripts/build_search_schedule.js
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const root = path.resolve(__dirname, '../..');
const htmlPath = path.join(root, 'index.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({ document: { getElementById: () => ({}), querySelector() {} }, window: {}, console });
vm.runInContext(script, context);
const csv = fs.readFileSync(path.join(root, 'moose_train_schedule.csv'), 'utf8');
context.csv = csv;
const started = performance.now();
const prepared = vm.runInContext(`(() => {
  const builder = createTripBuilder();
  const metadata = new Map();
  const parser = createCsvParser(row => {
    builder.addRow(row);
    const key = [row.station_id, row.source_pdf, row.service_name, row.timetable_effective_date].join('|');
    if (!metadata.has(key)) metadata.set(key, {
      station_id: row.station_id, station_name: row.station_name,
      source_pdf: row.source_pdf, source_original_filename: row.source_original_filename,
      service_name: row.service_name, timetable_effective_date: row.timetable_effective_date,
    });
  });
  parser.push(csv);
  parser.finish();
  return { trips: builder.finish(), metadata: Array.from(metadata.values()) };
})()`, context);
const strings = [];
const stringIds = new Map();
function encode(value) {
  if (typeof value !== 'string') return value;
  if (!stringIds.has(value)) { stringIds.set(value, strings.length); strings.push(value); }
  return [stringIds.get(value)];
}
const tripFields = Object.keys(prepared.trips[0]).filter(key => key !== 'stops');
const stopFields = Object.keys(prepared.trips[0].stops[0]);
const metadataFields = Object.keys(prepared.metadata[0]);
const row = (item, fields) => fields.map(key => encode(item[key]));
const payload = {
  version: 1, strings, tripFields, stopFields, metadataFields,
  trips: prepared.trips.map(trip => [...row(trip, tripFields), trip.stops.map(stop => row(stop, stopFields))]),
  metadata: prepared.metadata.map(item => row(item, metadataFields)),
};
const json = Buffer.from(JSON.stringify(payload));
const compressed = zlib.gzipSync(json, { level: 9 });
const version = crypto.createHash('sha256').update(json).digest('hex').slice(0, 16);
const updatedHtml = html.replace(/const SEARCH_SCHEDULE_VERSION = "[^"]*";/, `const SEARCH_SCHEDULE_VERSION = "${version}";`);
const outputs = [
  [htmlPath, Buffer.from(updatedHtml)],
  [path.join(root, 'supporting_files/assets/schedule/search.json'), json],
  [path.join(root, 'supporting_files/assets/schedule/search.json.gz'), compressed],
];
// Check the browser decoder against the exact CSV-derived trips, including all stop times and keys.
context.payload = payload;
const decoded = vm.runInContext('decodeSearchSchedule(payload)', context);
if (JSON.stringify(decoded) !== JSON.stringify(prepared)) throw new Error('Schedule round-trip mismatch');
for (const [file, contents] of outputs) {
  if (process.argv.includes('--check')) {
    const existing = fs.existsSync(file) ? fs.readFileSync(file) : null;
    // gzip byte streams can differ across zlib versions; their content must match.
    const matches = existing && (file.endsWith('.gz')
      ? zlib.gunzipSync(existing).equals(json)
      : existing.equals(contents));
    if (!matches) {
      throw new Error(`Stale schedule output: ${path.relative(root, file)}. Run the schedule builder.`);
    }
  } else {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, contents);
  }
}
console.log(JSON.stringify({ trips: prepared.trips.length, csvBytes: Buffer.byteLength(csv), jsonBytes: json.length, gzipBytes: compressed.length, preparationMs: Math.round(performance.now() - started), version }));
