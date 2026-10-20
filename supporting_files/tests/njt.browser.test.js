const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(request.url()));
    await page.route('https://api-endpoint.mta.info/**', route => route.abort());
    for (const width of [375,1280]) {
      await page.setViewportSize({width,height:1000});
      for (const lang of ['en','es','ko']) {
        await page.goto(`${base}/?lang=${lang}`);
        await page.waitForFunction(() => trips.length > 0);
        const state = await page.evaluate(async () => {
          els.origin.value='Port Jervis'; els.destination.value='New York Penn';
          els.date.value='2026-10-20'; els.time.value='7:00 AM';
          await renderSearch({requireSchedule:true});
          return {count:activeSearchState.routes.length,
            allOneTransfer:activeSearchState.routes.every(route=>route.legs.length===2 && route.legs[0].toId==='SEC'),
            expected:formatFareAmount(calculateNjtFare(activeSearchState.routes[0].legs)),
            throughNote:t('njtThroughFare')};
        });
        assert(state.count>0 && state.allOneTransfer);
        assert((await page.locator('.result .fare-summary').first().textContent()).includes(state.expected));
        assert.equal(await page.locator('.result .leg-fare').count(),0,'Do not show two separate prices for one NJ Transit ticket');
        const info=page.locator('.result .fare-info').first();
        await info.click();
        assert((await info.textContent()).includes(state.throughNote));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'No horizontal page overflow');
        const tooltip=await info.locator('.live-indicator-tooltip').boundingBox();
        assert(tooltip && tooltip.x>=-1 && tooltip.x+tooltip.width<=width+1,'Fare tooltip fits viewport');
        await info.click();
        if (width===375 && lang==='en') {
          await page.mouse.move(0,0);
          await page.screenshot({path:path.resolve(__dirname,'../staging/njt-preview-mobile.png'),fullPage:true});
        }
        await page.evaluate(async () => {
          els.origin.value='North Elizabeth'; els.destination.value='Rahway';
          await renderSearch({requireSchedule:true});
        });
        const unavailable=await page.evaluate(()=>t('fareUnavailable'));
        assert((await page.locator('.result .fare-summary').first().textContent()).includes(unavailable));
      }
    }
    // Missing local fare data leaves timetable searches usable.
    const noFares=await browser.newPage({viewport:{width:375,height:900}});
    await noFares.route('**/njt_fares.js*', route=>route.abort());
    await noFares.route('https://api-endpoint.mta.info/**', route=>route.abort());
    await noFares.goto(base);
    await noFares.waitForFunction(()=>trips.length>0);
    const fallback=await noFares.evaluate(async()=>{
      els.origin.value='New York Penn';els.destination.value='Trenton';
      els.date.value='2026-10-20';els.time.value='7:00 AM';
      await renderSearch({requireSchedule:true});
      return {results:activeSearchState.routes.length,unavailable:document.body.textContent.includes(t('fareUnavailable'))};
    });
    assert(fallback.results>0 && fallback.unavailable);
    assert.deepEqual(errors,[]);
    assert(!requests.some(url=>new URL(url).hostname.endsWith('njtransit.com')),'Browsers must not call NJ Transit APIs');
    console.log('NJ Transit desktop/mobile, three languages, through fares, unavailable prices, and missing-asset fallback passed');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
