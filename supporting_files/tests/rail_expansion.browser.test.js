const assert = require('node:assert/strict');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.route('https://**/*', route => route.abort());
    const failures = [];
    page.on('pageerror', error => failures.push(error.message));
    const base = process.env.TEST_URL || "http://127.0.0.1:8765";
    await page.goto(base);
    await page.waitForFunction(() => trips.length > 38083);
    const expected = {
      'Westport (Metro-North)': 'WPT', 'Westport (Amtrak)': 'WSP',
      'Madison (Shore Line East)': 'MAD', 'Madison (NJ Transit)': 'NJT_77',
      'Murray Hill (LIRR)': 'LIRR_130', 'Murray Hill (NJ Transit)': 'NJT_99',
      'Middletown, NY': 'NJT_86', 'Middletown, NJ': 'NJT_85',
    };
    assert.deepEqual(await page.evaluate(names => Object.fromEntries(names.map(name => [
      name, findStation(name, { fuzzy: false })?.id,
    ])), Object.keys(expected)), expected);
    for (const [origin, destination, agency, service] of [
      ['ALB', 'NFL', 'Amtrak', 'Empire Service'],
      ['NRO', 'NYP', 'Amtrak', 'Northeast Regional'],
      ['NJT_103', 'NYP', 'Amtrak', 'Northeast Regional'],
      ['PJC', 'NJT_124', 'NJ Transit', 'Princeton Shuttle'],
      ['NJT_77', 'NYP', 'NJ Transit', 'Morris & Essex Line'],
      ['NJT_2', 'NJT_10', 'NJ Transit', 'Atlantic City Rail Line'],
      ['NHV', 'STM', 'Amtrak', 'Northeast Regional'],
    ]) {
      const found = await page.evaluate(([origin, destination, agency, service]) =>
        findRoutes(origin, destination, 240, 'depart', new Date(2026, 10, 30)).some(route =>
          route.legs.length === 1 && route.legs[0].trip.agency === agency && route.legs[0].trip.service === service),
      [origin, destination, agency, service]);
      assert(found, [origin, destination, agency, service].join(' / '));
    }
    for (const [slug, id, label] of [
      ['westport', 'WPT', 'Westport (Metro-North)'],
      ['westport-amtrak', 'WSP', 'Westport (Amtrak)'],
      ['madison', 'MAD', 'Madison (Shore Line East)'],
      ['madison-shore-line-east', 'MAD', 'Madison (Shore Line East)'],
      ['madison-nj-transit', 'NJT_77', 'Madison (NJ Transit)'],
      ['murray-hill-lirr', 'LIRR_130', 'Murray Hill (LIRR)'],
      ['murray-hill', 'LIRR_130', 'Murray Hill (LIRR)'],
      ['murray-hill-nj-transit', 'NJT_99', 'Murray Hill (NJ Transit)'],
      ['middletown-nj', 'NJT_85', 'Middletown, NJ'],
      ['princeton', 'NJT_124', 'Princeton'],
    ]) {
      await page.goto(base + '/moose.train-departure-board.html?station=' + slug);
      await page.waitForFunction(id => boardUrlReady && selectedStation.id === id && stationTrips.length > 0, id);
      assert.match((await page.locator('#station-title').textContent()).trim(), new RegExp(label.replace(/[()]/g, '\\$&')));
    }
    await page.goto(base + '/moose.train-departure-board.html?station=princeton&lang=ko');
    await page.waitForFunction(() => boardUrlReady && selectedStation.id === 'NJT_124');
    assert.match(await page.locator('#station-title').textContent(), /프린스턴/);

    await page.route('**/search.json.gz*', route => route.abort());
    await page.goto(base);
    await page.waitForFunction(() => trips.some(trip => trip.service === 'Princeton Shuttle'));
    await page.goto(base + '/moose.train-departure-board.html?station=princeton');
    await page.waitForFunction(() => boardUrlReady && selectedStation.id === 'NJT_124' && stationTrips.length > 0);

    const standalone = pathToFileURL(resolve('moose.train-departure-board.html'));
    standalone.searchParams.set('station', 'westport-amtrak');
    await page.goto(standalone.href);
    await page.waitForFunction(() => boardUrlReady && selectedStation.id === 'WSP' && stationTrips.length > 0);
    assert.deepEqual(failures, []);
    console.log('Expanded search and board checks passed, including hosted and standalone fallbacks.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
