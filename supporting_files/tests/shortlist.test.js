const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
let stored = null;
let writes = 0;
let storageBlocked = false;
const localStorage = {
  getItem() {
    if (storageBlocked) throw new Error('Storage blocked');
    return stored;
  },
  setItem(key, value) {
    if (storageBlocked) throw new Error('Storage blocked');
    writes++;
    stored = value;
  },
};
const context = vm.createContext({ localStorage, window: {}, document: { getElementById: () => ({}), querySelector: () => null } });
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);

run(`
  function fixtureTrip(agency, train, serviceDate, rows) {
    return {
      key: train, agency, train, service: "Test service", route: "Test route",
      serviceStartDate: serviceDate, serviceEndDate: serviceDate,
      stops: rows.map(([id, name, arrival, departure], index) =>
        ({ id, name, arrival, departure, index, sequence: index })),
    };
  }
  trips = [
    fixtureTrip("Amtrak", "66", "2026-09-28", [
      ["NYP", "New York Penn", null, 1410],
      ["STM", "Stamford", 1430, 1431],
      ["NHV", "New Haven", 1450, null],
    ]),
    fixtureTrip("CTrail", "1602", "2026-09-29", [
      ["NHV", "New Haven", null, 20],
      ["OSB", "Old Saybrook", 60, null],
    ]),
  ];
  function searchState(date, queryTime, mode) {
    const state = { date: dateFromIso(date), queryTime, mode };
    state.routes = findRoutes("NYP", "OSB", queryTime, mode, state.date);
    return state;
  }
  const leave = searchState("2026-09-28", 1380, "leave");
  const arrive = searchState("2026-09-29", 90, "arrive");
  const route = leave.routes[0];
  const id = activeRouteShortlistId(route, leave);
  const snapshot = snapshotShortlistedTrip(route, leave);
  shortlistedTrips.set(id, snapshot);
  persistShortlist();
`);
assert.equal(run('arrive.routes.length'), 1);
assert.equal(run('activeRouteShortlistId(arrive.routes[0], arrive)'), run('id'));
assert.equal(run('routeShortlistId(snapshot.route, snapshot.date)'), run('id'));
assert.notEqual(run('routeShortlistId(snapshot.route, "2026-09-29")'), run('id'));
assert.notEqual(run(`routeShortlistId({
  legs: [{ ...snapshot.route.legs[0], trip: { ...snapshot.route.legs[0].trip, train: "67" } }, snapshot.route.legs[1]]
}, snapshot.date)`), run('id'));

const saved = JSON.parse(stored).trips[0];
assert.equal(saved.date, '2026-09-28');
assert.equal(saved.route.duration, 90);
assert.equal(saved.route.legs[1].departure - saved.route.legs[0].arrival, 10);
assert.deepEqual(saved.route.legs.map(leg => [leg.trip.agency, leg.serviceDate]), [
  ['Amtrak', '2026-09-28'], ['CTrail', '2026-09-29'],
]);
assert.equal(saved.route.legs[0].stops[1].name, 'Stamford');
assert(!('realtime' in saved.route));
assert.equal(run('readShortlist().has(id)'), true);
const rendered = run('renderRoute(snapshot.route, 0, "leave", leave.date, id, true, null, snapshot)');
assert.match(rendered, /September 28, 2026 – September 29, 2026/);
assert.match(rendered, /10m transfer at New Haven/);
assert.match(rendered, /Check fare on Amtrak/);
assert.equal(writes, 1);

storageBlocked = true;
assert.equal(run('readShortlist().size'), 0);
run('persistShortlist()');
assert.equal(run('shortlistedTrips.has(id)'), true);
assert.equal(writes, 1);
console.log('Overnight identity, different dates and trains, mixed operators, intermediate stops, fare links, and blocked storage passed.');
