const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const page = await browser.newPage({viewport:{width:390,height:950}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    // Fixed fares must work entirely from the local snapshot.
    await page.route('https://backend-unified.mylirr.org/**',route=>route.abort());
    await page.goto(base);
    await page.evaluate(()=>ensureScheduleLoaded());
    const results=await page.evaluate(()=>{
      const date=dateFromIso('2026-10-19');
      return [['LIRR_132','LIRR_211'],['LIRR_91','LIRR_179'],['GCT','LIRR_359'],['LIRR_179','LIRR_199']].map(([from,to])=>{
        const routes=findRoutes(from,to,360,'leave',date);
        if (!routes.length) throw new Error('No test journey: '+from+' '+to);
        const quotes=routes.map(route=>({fare:calculateRouteFare(route),html:renderRoute(route,360,'leave',date,'fare-test',false)}));
        if (quotes.some(q=>!q.fare || !Number.isInteger(q.fare.amountCents))) throw new Error('Unpriced LIRR journey');
        if (quotes.some(q=>q.html.includes('Check fare') || q.html.includes('checkMtaFare'))) throw new Error('Fallback link remains');
        return {from,to,quotes};
      });
    });
    assert(results[0].quotes.some(q=>q.fare.fareType==='VIA_ONE_WAY' && q.fare.amountCents===800 && q.html.includes('One-way via Jamaica')));
    assert(results[1].quotes.some(q=>q.fare.fareType==='VIA_ONE_WAY' && q.fare.amountCents===725));
    assert(results[2].quotes.some(q=>q.fare.amountCents===1000));
    assert(results[3].quotes.some(q=>q.fare.amountCents===1600));
    // Also render each translated fare label and amount for a mobile-width card.
    for (const language of ['en','ko','es']) {
      const html=results[0].quotes.find(q=>q.fare.fareType==='VIA_ONE_WAY').html;
      await page.evaluate(({language,html})=>{
        currentLanguage=language;
        const fare={amountCents:800,currency:'USD',fareType:'VIA_ONE_WAY',peakStatus:'OFF_PEAK',viaStationName:'Jamaica'};
        if (!renderFareSummary(fare).includes('$8.00')) throw new Error('Translated fare missing');
        document.querySelector('#results').innerHTML=html;
      },{language,html});
      assert(await page.locator('.fare-summary').count()>0);
    }
    assert.deepEqual(errors,[]);
    console.log('Offline browser fares passed: via Jamaica, via Hicksville, Elmont, Mets, no external fallback, three languages');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
