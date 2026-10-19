const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:375,height:900}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);
    await page.evaluate(()=>ensureScheduleLoaded());
    await page.locator('#origin').fill('Grand Central Madison');
    const matches=page.locator('#origin-options [role="option"]');
    assert.equal(await matches.count(),1);
    await matches.first().click();
    const results = await page.evaluate(() => {
      const day = dateFromIso('2026-10-19');
      if (!requiresUnsupportedMultiTransfer({id:'STM'},{id:'LIRR_73'},day)) throw new Error('Missing two-transfer explanation for Greenport');
      const pairs=[['GCT','LIRR_179'],['LIRR_102','LIRR_141'],['STM','LIRR_179'],['LIRR_179','STM'],['LIRR_179','NHV']];
      return pairs.map(([from,to])=>{
        const start=performance.now();
        const routes=findRoutes(from,to,360,'leave',day);
        if (routes.some(route=>route.legs.length>2)) throw new Error('More than one transfer');
        for (const route of routes.filter(r=>r.legs.length===2)) {
          const [a,b]=route.legs;
          if (b.departure-a.arrival < minimumTransferMinutes(a,b)) throw new Error('Unsafe transfer');
        }
        if (to === 'NHV' && !routes.some(route=>route.legs.length===2 && route.legs[0].toId==='NYP')) throw new Error('Missing Penn Amtrak connection');
        const first=routes[0];
        return {from,to,count:routes.length,ms:Math.round(performance.now()-start),html:first?renderRoute(first,360,'leave',day,'lirr-test',false):'',fares:first?calculateRouteFare(first):null};
      });
    });
    assert(results.every(r=>r.count>0),JSON.stringify(results.map(({html,...r})=>r)));
    assert(results[2].html.includes('Grand Central Madison'));
    assert(results[2].html.includes('Grand Central Terminal'));
    assert(results[2].html.includes('Combo Ticket'));
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify(results.map(({html,...r})=>r)));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
