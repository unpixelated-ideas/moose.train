// Serve the site locally, then run with Playwright available on NODE_PATH.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const requests = [];
    const errors = [];
    page.on('request', request => requests.push(request.url()));
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.TEST_URL || 'http://127.0.0.1:8765');
    await page.waitForFunction(() => trips.length > 0);
    const prepared = await page.evaluate(() => ({ trips: trips.length, readyMs: Math.round(performance.now()) }));
    assert(requests.some(url => url.includes('search.json.gz')));
    assert(!requests.some(url => url.endsWith('moose_train_schedule.csv')), 'No full CSV download');
    const result = await page.evaluate(async () => {
      els.origin.value = 'New Haven';
      els.destination.value = 'Stamford';
      // Select a date present in this schedule instead of a historical fixture.
      const trip = trips.find(trip => trip.stops.some(stop => stop.id === 'NHV') && trip.stops.some(stop => stop.id === 'STM'));
      els.date.value = trip.serviceDates ? trip.serviceDates.split(/[;,\s]+/)[0] : trip.serviceStartDate;
      els.time.value = '9:00 AM';
      const start = performance.now();
      await renderSearch({ requireSchedule: true });
      return { searchMs: Math.round(performance.now() - start), date: els.date.value, results: document.querySelectorAll('.result').length };
    });
    assert(result.results > 0, 'Current schedule returns real journeys');
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...prepared, ...result }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
