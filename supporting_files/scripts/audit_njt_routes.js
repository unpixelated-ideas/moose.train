// Exercise the production router against a staged import without changing public assets.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
process.env.TZ = 'America/New_York';
const schedulePath = process.argv[2];
const serviceDate = process.argv[3] || new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York'}).format(new Date());
if (!schedulePath || !/^\d{4}-\d{2}-\d{2}$/.test(serviceDate || '')) {
  throw new Error('Usage: node audit_njt_routes.js staged/schedule.csv.gz [YYYY-MM-DD]');
}
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({document: {getElementById: () => ({}), querySelector() {}}, window: {}, console, Date});
vm.runInContext(script, context);
context.csv = zlib.gunzipSync(fs.readFileSync(schedulePath)).toString('utf8');
context.serviceDate = serviceDate;
vm.runInContext(`
  const builder = createTripBuilder();
  const parser = createCsvParser(row => builder.addRow(row));
  parser.push(csv);
  parser.finish();
  trips = builder.finish();
  stationSequencesByDirection = buildStationSequencesByDirection(trips);
  // Preview only: station-specific minimums still require verification before launch.
  ['SEC', 'NWK', 'TRE'].forEach(id => transferStationIds.add(id));
  const auditDate = dateFromIso(serviceDate);
`, context);
const scenarios = [
  ['NYP', 'TRE', false], ['TRE', 'NYP', false],
  ['NJT_123', 'NJT_63', false], ['NJT_63', 'NJT_123', false],
  ['NJT_142', 'NJT_63', false], ['NJT_63', 'NJT_142', false],
  ['NJT_123', 'NYP', true], ['NYP', 'NJT_123', true],
  ['NJT_142', 'NYP', true], ['NYP', 'NJT_142', true],
];
const report = [];
for (const [origin, destination, transfer] of scenarios) {
  const routes = vm.runInContext(`findRoutes(${JSON.stringify(origin)}, ${JSON.stringify(destination)}, 0, 'depart', auditDate)`, context);
  assert(routes.length, `No staged route: ${origin} → ${destination} on ${serviceDate}`);
  assert(routes.every(route => route.legs.length <= 2), 'One-transfer maximum exceeded');
  assert(routes.some(route => route.legs.length === (transfer ? 2 : 1)), 'Expected direct/transfer option missing');
  if (transfer) assert(routes.every(route => route.legs.length === 2 && route.legs[0].toId === 'SEC'), 'Penn journey must change at Secaucus');
  report.push({origin, destination, options: routes.length, expectedTransfer: transfer});
}
console.log(JSON.stringify({serviceDate, published: false, provisionalTransferMinimums: true, scenarios: report}, null, 2));
