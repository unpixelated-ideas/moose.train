const { chromium } = require('playwright');

const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
const sampleCount = Number(process.env.TEST_SAMPLES || 12);

async function collect(browser, mobile) {
  const samples = [];
  for (let index = 0; index < sampleCount; index++) {
    const context = await browser.newContext({
      viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 },
      isMobile: mobile,
      hasTouch: mobile,
    });
    try {
      await context.route('https://**/*', route => route.abort());
      const page = await context.newPage();
      if (mobile) {
        const cdp = await context.newCDPSession(page);
        await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
        await cdp.send('Network.enable');
        await cdp.send('Network.emulateNetworkConditions', {
          offline: false, latency: 100, downloadThroughput: 625000, uploadThroughput: 125000,
        });
      }
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      const search = await page.evaluate(async () => {
        els.origin.value = 'New Haven';
        els.destination.value = 'Stamford';
        els.date.value = '2026-11-30';
        els.time.value = '9:00 AM';
        let started = performance.now();
        await renderSearch({ requireSchedule: true });
        const firstSearch = performance.now() - started;
        if (!document.querySelector('.result')) throw Error('Search produced no results');
        started = performance.now();
        await renderSearch({ requireSchedule: true });
        return { firstSearch, repeatSearch: performance.now() - started };
      });
      await page.goto(base + '/moose.train-departure-board.html?station=new-york-penn', {
        waitUntil: 'domcontentloaded',
      });
      await page.waitForFunction(() => boardUrlReady && !busy && allTrips.length > 0 && lastSuccess);
      const board = await page.evaluate(async () => {
        const boardOpen = performance.now();
        let started = performance.now();
        selectStation(stationOptions().find(station => station.id === 'STM'));
        const boardSelect = performance.now() - started;
        started = performance.now();
        await refresh();
        return { boardOpen, boardSelect, boardRefresh: performance.now() - started };
      });
      samples.push({ ...search, ...board });
    } finally {
      await context.close();
    }
  }
  const p95 = Object.fromEntries(Object.keys(samples[0]).map(key => {
    const values = samples.map(sample => sample[key]).sort((a, b) => a - b);
    return [key, Math.round(values[Math.ceil(0.95 * values.length) - 1])];
  }));
  return { samples, p95 };
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const result = { sampleCount };
    if (process.env.TEST_PROFILE !== 'mobile') result.desktop = await collect(browser, false);
    if (process.env.TEST_PROFILE !== 'desktop') result.mobile = await collect(browser, true);
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
