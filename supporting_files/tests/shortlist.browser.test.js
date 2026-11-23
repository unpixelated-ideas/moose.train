const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
const storageKey = 'moose.train.shortlist';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://api-endpoint.mta.info/**', route => route.abort());
    await page.goto(base);
    await page.evaluate(() => ensureScheduleLoaded());
    const shortlist = page.locator('[data-shortlist-filter]');
    const clear = page.locator('[data-shortlist-clear]');
    const cards = page.locator('.result');
    const toggles = page.locator('[data-shortlist-toggle]');
    const slider = page.locator('#departure-range-slider');
    const stored = () => page.evaluate(key => JSON.parse(localStorage.getItem(key)), storageKey);
    const cardIds = () => cards.evaluateAll(items => items.map(item => item.dataset.routeId));
    const search = async (origin, destination, date, time = '7:00 AM') => {
      await page.evaluate(({ origin, destination, date, time }) => {
        els.origin.value = origin;
        els.destination.value = destination;
        els.date.value = date;
        els.time.value = time;
      }, { origin, destination, date, time });
      await page.locator('#search-button').click();
    };

    assert.equal(await shortlist.count(), 0);
    await search('Port Jervis', 'New York Penn', '2026-11-20');
    const transfer = cards.filter({ has: page.locator('.transfer-connection') }).first();
    const transferId = await transfer.getAttribute('data-route-id');
    const transferDetails = await transfer.locator('.transfer-connection').textContent();
    const transferFare = await transfer.locator('.fare-summary').textContent();
    await transfer.locator('[data-shortlist-toggle]').click();
    assert.equal(await shortlist.textContent(), 'Show Shortlist (1)');

    await shortlist.click();
    await search('Grand Central', 'Stamford', '2026-11-19', '1:00 PM');
    assert.equal(await slider.count(), 1, 'A search exits Shortlist view');
    await toggles.first().click();
    const directId = (await cardIds())[0];
    assert.notEqual(directId, transferId);
    assert.equal(await shortlist.textContent(), 'Show Shortlist (2)');

    await search('Grand Central', 'Stamford', '2026-11-19', '12:59 PM');
    const repeated = page.locator('[data-shortlist-toggle][aria-pressed="true"]');
    assert.equal(await repeated.getAttribute('data-route-id'), directId);
    await slider.focus();
    await page.keyboard.press('Home');
    await page.waitForFunction(() => departureRangeHours === 1);
    await shortlist.click();
    assert.deepEqual(await cardIds(), [directId, transferId], 'Earlier date sorts first, independent of save order and range');
    assert.equal(await slider.count(), 0);
    assert.equal(await page.locator('.trip-count').count(), 0);
    await shortlist.click();
    assert.equal(await slider.inputValue(), '1');

    await search('Grand Central', 'Stamford', '2099-11-19');
    assert.equal(await cards.count(), 0);
    assert.equal(await shortlist.textContent(), 'Show Shortlist (2)');
    await page.locator('#reset-button').click();
    assert.equal(await page.locator('#origin').inputValue(), '');
    assert.equal(await shortlist.textContent(), 'Show Shortlist (2)');

    const original = await stored();
    assert.equal(original.version, 1);
    assert.equal(original.trips[0].route.legs.length, 2);
    assert(original.trips[0].route.legs.some(leg => leg.stops.length > 2));
    await page.reload();
    assert.equal(await shortlist.textContent(), 'Show Shortlist (2)');
    await shortlist.click();
    assert.deepEqual(await cardIds(), [directId, transferId]);
    assert.equal(await cards.last().locator('.transfer-connection').textContent(), transferDetails);
    assert.equal(await cards.last().locator('.fare-summary').textContent(), transferFare);
    assert.match(await page.locator('.shortlist-note').textContent(), /outdated/);

    const time12 = await cards.first().locator('.journey-time').textContent();
    await page.selectOption('#time-format-select', '24');
    assert.notEqual(await cards.first().locator('.journey-time').textContent(), time12);
    assert.deepEqual(await stored(), original, 'Formatting changes do not rewrite snapshots');
    for (const [language, count, label, confirm] of [
      ['en', 'Shortlisted trips (2)', 'Clear Shortlist', 'Remove all trips from your shortlist?'],
      ['ko', '후보 여정 (2개)', '후보 목록 비우기', '후보 목록에서 모든 여정을 삭제할까요?'],
      ['es', 'Viajes guardados (2)', 'Vaciar lista breve', '¿Quieres quitar todos los viajes de tu lista breve?'],
    ]) {
      await page.selectOption('#language-select', language);
      assert.equal(await page.locator('.shortlist-count').textContent(), count);
      assert.equal(await clear.textContent(), label);
      const dialogPromise = page.waitForEvent('dialog');
      const click = clear.click();
      const dialog = await dialogPromise;
      assert.equal(dialog.message(), confirm);
      await dialog.dismiss();
      await click;
      assert.deepEqual(await stored(), original);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }

    await toggles.last().click();
    assert.deepEqual(await cardIds(), [directId]);
    assert.equal((await stored()).trips.length, 1);
    await toggles.first().click();
    assert.equal(await shortlist.count(), 0);
    assert.equal(await clear.count(), 0);
    assert.equal(await stored(), null);

    await page.evaluate(({ key, data }) => {
      data.trips.push({ route: { legs: [null] } }, data.trips[0]);
      data.trips[0].scheduleVersion = 'older-schedule';
      localStorage.setItem(key, JSON.stringify(data));
    }, { key: storageKey, data: original });
    await page.reload();
    await shortlist.click();
    assert.deepEqual(await cardIds(), [directId, transferId], 'Restoration skips malformed entries and duplicates');
    await search('Grand Central', 'Stamford', '2026-11-19', '1:00 PM');
    await shortlist.click();
    page.once('dialog', dialog => dialog.accept());
    await clear.click();
    assert.equal(await stored(), null);
    assert.equal(await slider.count(), 1, 'Clearing returns to the active results');
    assert.equal(await page.locator('[data-shortlist-toggle][aria-pressed="true"]').count(), 0);
    await page.reload();
    assert.equal(await shortlist.count(), 0);

    for (const invalid of ['{', '{"version":99,"trips":[]}']) {
      await page.evaluate(({ key, value }) => localStorage.setItem(key, value), { key: storageKey, value: invalid });
      await page.reload();
      assert.equal(await shortlist.count(), 0);
    }
    assert.deepEqual(errors, []);
    console.log('Cross-search shortlist, range isolation, Reset, reload, fares, localization, removal, and clear confirmation passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
