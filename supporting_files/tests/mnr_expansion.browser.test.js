const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:390,height:950}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.route('https://api-endpoint.mta.info/**',route=>route.abort());
    await page.goto(base);
    await page.evaluate(()=>ensureScheduleLoaded());
    const sourceDownload = await page.evaluate(()=>timetableCsvLinks.find(link=>link.href.includes('mnr_gtfs_')).href);
    assert(sourceDownload.endsWith('.csv.gz'));
    const response = await page.request.get(base + '/' + sourceDownload);
    assert.equal(response.status(), 200);
    assert.deepEqual([...(await response.body()).subarray(0,2)], [31,139]);
    await page.locator('#origin').fill('Pough');
    await page.locator('#origin').dispatchEvent('input');
    await page.waitForFunction(()=>document.querySelector('#origin-options').textContent.includes('Poughkeepsie'));
    await page.locator('#origin').fill('Wassaic');
    await page.locator('#origin').dispatchEvent('input');
    await page.waitForFunction(()=>document.querySelector('#origin-options').textContent.includes('Wassaic'));
    const routes = await page.evaluate(()=>{
      const isoDate=(() => {
  const groups = [
    trips.filter(t=>t.agency==='Metro-North' && t.service==='Hudson Line' && t.stops.some(s=>s.id==='POU')),
    trips.filter(t=>t.agency==='Metro-North' && t.service==='Harlem Line' && t.stops.some(s=>s.id==='MNR_177')),
    trips.filter(t=>t.agency==='Amtrak' && t.stops.some(s=>s.id==='NYP') && t.stops.some(s=>s.id==='POU')),
  ];
  if (groups.some(group=>!group.length)) throw new Error('Expanded service missing from schedule');
  const first = groups.map(group=>group.map(t=>t.serviceStartDate).sort()[0]).sort().at(-1);
  for (let offset=0;offset<21;offset++) {
    const date=addDays(dateFromIso(first),offset);
    if (date.getDay()>0 && date.getDay()<6 && groups.every(group=>group.some(t=>serviceApplies(t,date)))) return localDateIso(date);
  }
  throw new Error('No overlapping weekday coverage for expanded services');
})();
      const date=dateFromIso(isoDate);
      const find=(to)=>findRoutesForStationSelection({id:'NYC_RAIL'},{id:to},360,'leave',date);
      const hudson=find('POU');
      const harlem=find('MNR_177');
      const stadium=find('YANKEES');
      if (!hudson.some(r=>r.legs[0].trip.agency==='Amtrak') || !hudson.some(r=>r.legs[0].trip.agency==='Metro-North')) throw new Error('Comparison missing');
      const mnr=hudson.find(r=>r.legs.length===1 && r.legs[0].trip.agency==='Metro-North');
      const north=harlem.find(r=>calculateRouteFare(r));
      if (!north || !stadium.length || stadium.some(r=>calculateRouteFare(r))) throw new Error('Harlem/stadium fare coverage');
      return {isoDate,mnr,north,stadium:stadium[0]};
    });
    for (const language of ['en','ko','es']) {
      for (const route of [routes.mnr,routes.north,routes.stadium]) {
        await page.evaluate(({route,language,isoDate})=>{
          currentLanguage=language;
          const date=dateFromIso(isoDate);
          // Service dates become strings across the browser boundary.
          route.legs.forEach(leg=>leg.serviceDate=leg.serviceDate ? new Date(leg.serviceDate) : date);
          document.querySelector('#results').innerHTML=renderRoute(route,360,'leave',date,'expansion-test',false);
        },{route,language,isoDate:routes.isoDate});
        assert(await page.locator('#results').textContent());
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Mobile overflow');
      }
    }
    assert.deepEqual(errors,[]);
    console.log('Mobile station suggestions, Hudson comparison, Harlem fares, stadium suppression, and three-language cards passed.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
