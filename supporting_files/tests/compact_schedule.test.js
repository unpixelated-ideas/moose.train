const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const json = fs.readFileSync(path.join(root, 'supporting_files/assets/schedule/search.json'));
const gzip = fs.readFileSync(path.join(root, 'supporting_files/assets/schedule/search.json.gz'));
const tinyCsv = 'agency,service_name,route_name,train_number,direction,station_id,station_name,station_sequence,arrival_time,departure_time\nTest,Test,Test,1,North,A,A,1,10:00,10:00\nTest,Test,Test,1,North,B,B,2,11:00,11:00\n';
function environment({ decompression = true, brokenGzip = false, brokenJson = false, offline = false } = {}) {
  const requests = [];
  const events = [];
  let idle;
  const context = vm.createContext({
    document: { getElementById: () => ({ addEventListener: (name, callback) => events.push([name, callback]) }), querySelector() {} },
    window: { requestIdleCallback: callback => { idle = callback; } },
    console, Response, TextDecoder, DecompressionStream: decompression ? DecompressionStream : undefined,
    fetch: async url => {
      requests.push(url);
      if (offline) throw new Error('Offline');
      if (url.includes('.gz')) return new Response(brokenGzip ? 'bad gzip' : gzip);
      if (url.includes('.json')) return new Response(brokenJson ? '{"version":0}' : json);
      return new Response(tinyCsv);
    },
  });
  vm.runInContext(script, context);
  vm.runInContext('applySchedule = (items, metadata) => { trips = items; }; setStatus = () => {}; readEmbeddedCsv = () => "";', context);
  return { context, requests, events, run: code => vm.runInContext(code, context), idle: () => idle() };
}
(async () => {
  const normal = environment();
  normal.run('startSchedulePreload()');
  assert.equal(normal.requests.length, 0, 'Wait for first paint / interaction');
  const background = normal.idle();
  const foreground = normal.run('ensureScheduleLoaded()');
  assert.equal(background, foreground, 'Search shares the in-flight preload');
  assert(await foreground);
  assert.equal(normal.requests.length, 1);
  assert.match(normal.requests[0], /search\.json\.gz\?v=[0-9a-f]{16}$/);
  assert(normal.run('trips.length') > 0);
  await normal.events[0][1]();
  assert.equal(normal.requests.length, 1, 'Loaded searches do not fetch again');
  for (const options of [{ decompression: false }, { brokenGzip: true }]) {
    const fallback = environment(options);
    assert(await fallback.run('ensureScheduleLoaded()'));
    assert(fallback.requests.at(-1).includes('search.json?v='));
    assert.equal(fallback.run('JSON.stringify(trips)'), normal.run('JSON.stringify(trips)'));
  }
  const csvFallback = environment({ brokenGzip: true, brokenJson: true });
  assert(await csvFallback.run('ensureScheduleLoaded()'));
  assert.equal(csvFallback.requests.at(-1), 'moose_train_schedule.csv');
  assert.equal(csvFallback.run('trips[0].stops[1].arrival'), 660);
  const offline = environment({ offline: true });
  assert.equal(await offline.run('ensureScheduleLoaded({ updateStatus: false })'), false);
  const attempts = offline.requests.length;
  assert.equal(await offline.run('ensureScheduleLoaded()'), false);
  assert(offline.requests.length > attempts, 'Failed preload can be retried');
  console.log('Compact schedule loading, shared preload, compatibility, and failure tests passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
