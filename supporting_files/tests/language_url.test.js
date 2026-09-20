// Run with Playwright available on NODE_PATH and the static site served at TEST_URL.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const checkLanguage = async language => {
      assert.equal(await page.locator('html').getAttribute('lang'), language);
      assert.equal(await page.locator('#language-select').inputValue(), language);
    };
    for (const [query, language] of [['', 'en'], ['?lang=es', 'es'], ['?lang=ko', 'ko'], ['?lang=fr', 'en'], ['?lang=constructor', 'en'], ['?lang=', 'en']]) {
      await page.goto(base + '/' + query);
      await checkLanguage(language);
      await page.reload();
      await checkLanguage(language);
    }
    await page.goto(base + '/?from=GCT&to=NHV&extra=1&extra=2#results');
    const historyLength = await page.evaluate(() => history.length);
    for (const language of ['es', 'ko', 'en']) {
      await page.selectOption('#language-select', language);
      await checkLanguage(language);
      const url = new URL(page.url());
      assert.equal(url.searchParams.get('lang'), language === 'en' ? null : language);
      assert.equal(url.searchParams.get('from'), 'GCT');
      assert.equal(url.searchParams.get('to'), 'NHV');
      assert.deepEqual(url.searchParams.getAll('extra'), ['1', '2']);
      assert.equal(url.hash, '#results');
      assert.equal(await page.evaluate(() => history.length), historyLength);
    }
    await page.evaluate(() => history.pushState({ test: true }, '', '?lang=ko'));
    await page.reload();
    await checkLanguage('ko');
    await page.goBack();
    await checkLanguage('en');
    await page.goForward();
    await checkLanguage('ko');
    assert.deepEqual(await page.evaluate(() => history.state), { test: true });
    await page.selectOption('#appearance-select', 'dark');
    await page.selectOption('#language-select', 'es');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    assert.equal(await page.locator('.tagline').textContent(), 'Compara Amtrak y trenes regionales en una sola búsqueda.');
    await page.selectOption('#language-select', 'ko');
    assert.equal(await page.locator('.tagline').textContent(), '암트랙과 지역 철도를 한 번의 검색으로 비교하세요.');
    // Load real local schedules and exercise the existing shared search engine.
    await page.evaluate(async () => {
      await ensureScheduleLoaded({ updateStatus: false });
      els.origin.value = 'New Haven'; els.destination.value = 'Stamford';
      els.date.value = '2026-09-21'; els.time.value = '9:00 AM';
      await renderSearch({ requireSchedule: true });
    });
    assert(await page.locator('.result').count() > 0, 'Real search returns trips');
    await page.locator('.shortlist-toggle').first().click();
    await page.evaluate(() => { window.originalSearch = activeSearchState; window.originalShortlist = [...shortlistedRouteIds]; window.originalOriginId = findStation(els.origin.value).id; });
    for (const language of ['en', 'es', 'ko']) {
      await page.selectOption('#language-select', language);
      assert(await page.evaluate(() => activeSearchState === window.originalSearch), 'Language preserves exact search and route objects');
      assert(await page.evaluate(() => JSON.stringify([...shortlistedRouteIds]) === JSON.stringify(window.originalShortlist)));
      assert(await page.evaluate(() => findStation(els.origin.value).id === window.originalOriginId), 'Existing localized station names preserve the selected station');
      assert.equal(await page.evaluate(() => els.date.value), '2026-09-21');
    }
    for (const theme of ['light', 'dark', 'system']) {
      await page.selectOption('#appearance-select', theme);
      assert.equal(await page.locator('html').getAttribute('data-theme-preference'), theme);
    }
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow');
    }
    for (const selector of ['meta[property="og:title"]', 'meta[name="twitter:title"]']) assert.equal(await page.locator(selector).getAttribute('content'), 'moose.train');
    for (const selector of ['meta[property="og:description"]', 'meta[name="twitter:description"]']) assert.equal(await page.locator(selector).getAttribute('content'), 'Compare Amtrak and regional rail in one search.');
    for (const selector of ['meta[property="og:image"]', 'meta[name="twitter:image"]']) assert.equal(await page.locator(selector).getAttribute('content'), 'https://unpixelated-ideas.github.io/moose.train/preiewimage.png');
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://unpixelated-ideas.github.io/moose.train/');
    const response = await page.request.get(base + '/preiewimage.png');
    assert.equal(response.status(), 200);
    assert.match(response.headers()['content-type'], /image\/png/);
    assert.deepEqual(errors, []);
    console.log('Language URLs, history, real search preservation, appearance, responsive layout, metadata and preview asset passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
