const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [lang, primary, secondary] of [
        ['en', '🗽 New York City (major stations)', 'Penn Station or Grand Central'],
        ['es', '🗽 Nueva York (estaciones principales)', 'Penn Station o Grand Central'],
        ['ko', '🗽 뉴욕 (주요 기차역)', '뉴욕 펜역 또는 그랜드 센트럴역'],
      ]) {
        await page.goto(`${base}/?lang=${lang}`);
        await page.waitForFunction(() => typeof stations !== 'undefined' && stations.length > 0);
        for (const field of ['origin', 'destination']) {
          await page.locator('html').evaluate((el, theme) => el.dataset.theme = theme, field === 'origin' ? 'light' : 'dark');
          const input = page.locator(`#${field}`);
          await input.fill('');
          await input.focus();
          const option = page.locator(`#${field}-options [role="option"]`).first();
          await option.waitFor({ state: 'visible' });
          assert.equal(await option.getAttribute('aria-label'), primary);
          assert.equal(await option.locator('.station-option-description').textContent(), secondary);
          assert.equal(await option.evaluate(el => el.scrollWidth <= el.clientWidth), true);
          assert.equal(await option.evaluate(el => getComputedStyle(el).borderBottomStyle), 'solid');
          await input.press('ArrowDown');
          assert.equal(await option.getAttribute('aria-selected'), 'true');
          await input.press('Enter');
          assert.equal(await input.inputValue(), primary);
          assert.equal(await page.evaluate(field => findStation(document.getElementById(field).value).id, field), 'NYC_RAIL');
          await input.fill('Grand Central');
          assert.equal(await option.getAttribute('aria-label'), primary);
          await input.press('Escape');
        }
        assert.deepEqual(await page.evaluate(() => stationSearchIds(findStation('NYC_RAIL'))), ['NYP', 'GCT']);
      }
    }
    console.log('NYC picker: both fields, three languages, desktop/mobile wrapping, search, keyboard selection and terminal IDs passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
