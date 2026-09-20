const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const events = [];
const results = { innerHTML: '', focus: () => events.push('focus'), scrollIntoView: () => events.push('scroll') };
const context = vm.createContext({
  document: { getElementById: () => ({}), querySelector() {}, activeElement: { blur: () => events.push('blur') } },
  window: { matchMedia: () => ({ matches: true }) },
  requestAnimationFrame: fn => fn(), results,
});
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);
run(`
  els.results = results;
  els.origin.value = 'Beacon Falls'; els.destination.value = 'Berlin';
  els.time.value = '9:00 PM'; els.date.value = '2026-09-06'; els.mode.value = 'leave';
  findStation = () => ({id: 'test'});
  daylightSavingSearchTimeAdjustment = () => null;
  ensureScheduleLoaded = async () => { trips = [{}]; return true; };
  setSearchLoading = () => {};
  setStatus = () => {};
  findRoutesForStationSelection = () => [{}];
  renderActiveSearchResults = () => {};
  startActiveResultStatusRefresh = () => {};
  stopActiveResultStatusRefresh = () => {};
  refreshRealtimeForActiveSearch = () => {};
`);
(async () => {
  for (const loaded of [false, true]) {
    run(`trips = ${loaded ? '[{}]' : '[]'}`);
    events.length = 0;
    await run('renderSearch({requireSchedule: true})');
    assert.deepEqual(events, ['blur', 'focus', 'scroll'], 'First and repeat searches move focus to results');
  }
  events.length = 0;
  await run('renderSearch()');
  assert.deepEqual(events, [], 'Setting and background updates must not move focus');
  run(`findRoutesForStationSelection = () => []; emptyStateForSearch = () => ({key:'noResults',values:{}});`);
  await run('renderSearch({requireSchedule: true})');
  assert.deepEqual(events, ['blur', 'focus', 'scroll'], 'No-result searches also move focus');
  const connection = run(`renderTransferConnection({arrival: 1015}, {departure:1066,from:'Bridgeport'})`);
  assert(connection.includes('51m transfer at Bridgeport'));
  assert(!html.includes('leg-source-spacer'), 'Legs must not reserve space for removed source links');
  console.log('Search results focus and transfer presentation tests passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
