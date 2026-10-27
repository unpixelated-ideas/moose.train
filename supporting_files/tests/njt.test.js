const assert = require('node:assert/strict');
const {serviceDateForGroups} = require('./helpers/service_date');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
process.env.TZ = 'America/New_York';
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const asset = fs.readFileSync(path.join(root, 'supporting_files/assets/njt_fares.js'), 'utf8');
const fareData = JSON.parse(fs.readFileSync(path.join(root, 'supporting_files/assets/njt_fares.json'), 'utf8'));
const context = vm.createContext({document:{getElementById:()=>({}),querySelector(){}},window:{},console,Date});
vm.runInContext(asset, context);
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);
assert.equal(run('JSON.stringify(window.MOOSE_NJT_FARES)'), JSON.stringify(fareData));
const hash = crypto.createHash('sha256').update(asset).digest('hex').slice(0,16);
assert(html.includes(`njt_fares.js?v=${hash}`), 'Fare asset version must match the generated data');
assert(Object.keys(fareData.fares).length, 'Published fare snapshot must not be empty');
for (const quote of Object.values(fareData.fares)) {
  assert(Number.isInteger(quote.amountCents) && quote.amountCents > 0);
  assert.equal(typeof quote.viaSecaucusOnly, 'boolean');
}
// Fare behavior uses controlled quotes. A provider correcting a price or adding
// a previously withheld pair must not break the daily publication checks.
run(`
  window.MOOSE_NJT_FARES = {version:1,currency:'USD',sourceUrl:'https://www.njtransit.com/train-to',retrievedAt:new Date().toISOString(),fares:{
    'NYP>TRE':{amountCents:2000,viaSecaucusOnly:false},
    'NJT_123>NYP':{amountCents:2300,viaSecaucusOnly:false},
    'NJT_142>NJT_63':{amountCents:1200,viaSecaucusOnly:false},
    'NYP>EWR':{amountCents:1800,viaSecaucusOnly:false},
  }};
  const njtLeg = (fromId,toId) => ({fromId,toId,trip:{agency:'NJ Transit',service:'Northeast Corridor',staticRouteId:fromId==='NJT_123'||toId==='NJT_123'?'6':'10'}});
`);
for (const pair of [['NYP','TRE'],['NJT_123','NYP'],['NJT_142','NJT_63']]) {
  context.pair = pair;
  assert(run('calculateNjtFare([njtLeg(...pair)]).amountCents > 0'));
}
assert.equal(run(`calculateNjtFare([njtLeg('NJT_109','NJT_127')])`),null,'Withheld fare remains unpriced');
assert.equal(run(`calculateNjtFare([njtLeg('NJT_127','NJT_109')])`),null);
assert.equal(run(`calculateNjtFare([njtLeg('NYP','TRE')], 'CHILD')`),null,'No inferred discounts');
assert.equal(run(`calculateNjtFare([njtLeg('NJT_123','SEC'),njtLeg('SEC','NYP')]).amountCents`),2300,'Use one through fare, not two leg fares');
assert.equal(run(`calculateNjtFare([njtLeg('NJT_123','SEC'),njtLeg('NWK','NYP')])`),null,'Disconnected legs');
assert.equal(run(`calculateNjtFare([njtLeg('NJT_123','SEC'),njtLeg('SEC','NYP'),njtLeg('NYP','TRE')])`),null);
assert.equal(run(`calculateRouteFare({legs:[njtLeg('TRE','NYP'),{fromId:'NYP',toId:'NHV',trip:{agency:'Amtrak'}}]})`),null,'No partial mixed-operator total');
assert(run(`renderFareSummary(calculateNjtFare([njtLeg('NYP','EWR')])).includes('AirTrain')`));
assert(run(`renderFareSummary(calculateNjtFare([njtLeg('NJT_123','SEC'),njtLeg('SEC','NYP')])).includes('One ticket')`));
run(`window.MOOSE_NJT_FARES.fares['NJT_123>NYP'].viaSecaucusOnly = true;`);
assert.equal(run(`calculateNjtFare([njtLeg('NJT_123','NYP')])`),null,'Preserve source applicability restrictions');
assert(run(`calculateNjtFare([njtLeg('NJT_123','SEC'),njtLeg('SEC','NYP')])`));
run(`window.MOOSE_NJT_FARES.fares['NJT_123>NJT_142']={amountCents:2000,viaSecaucusOnly:false};`);
assert.equal(run(`calculateNjtFare([njtLeg('NJT_123','SEC'),{...njtLeg('SEC','NJT_142'),trip:{agency:'NJ Transit',staticRouteId:'14'}}])`),null,'Unreviewed West of Hudson transfer patterns remain unpriced');
run(`window.MOOSE_NJT_FARES.retrievedAt = new Date(Date.now() - 31*86400000).toISOString();`);
assert.equal(run(`calculateNjtFare([njtLeg('NYP','TRE')])`),null,'Stale fare data does not silently persist');
run(`window.MOOSE_NJT_FARES = null;`);
assert.equal(run(`calculateNjtFare([njtLeg('NYP','TRE')])`),null,'Fare asset failure does not break searches');
assert.equal(run(`isMetroNorthRealtimeTrip({agency:'NJ Transit',service:'New Haven Line',route:'New Haven Line'})`),false);
assert.equal(run(`isMetroNorthFareLeg(njtLeg('NYP','TRE'))`),false,'West of Hudson must not use East of Hudson fares');
for (const [id,term] of [['SEC','Secaucus'],['NWK','Newark Penn Station'],['EWR','EWR'],['NJT_123','Port Jervis'],['NJT_142','Spring Valley']]) {
  context.id = id; context.term = term;
  assert(run(`stationIndex.some(s=>s.id===id && stationMatchesQuery(s,term))`),term);
}
context.schedule = JSON.parse(fs.readFileSync(path.join(root,'supporting_files/assets/schedule/search.json'),'utf8'));
run(`const prepared=decodeSearchSchedule(schedule); trips=prepared.trips; stationSequencesByDirection=buildStationSequencesByDirection(trips);`);
const calendar = run('({dateFromIso, localDateIso, addDays, serviceApplies})');
const directTrips = (from, to, agency) => run(`candidateLegsFromStation(${JSON.stringify(from)},${JSON.stringify(to)}).filter(leg=>leg.toId===${JSON.stringify(to)} && leg.trip.agency===${JSON.stringify(agency)}).map(leg=>leg.trip)`);
for (const [from,to,agency] of [['NYP','TRE','NJ Transit'],['NYP','TRE','Amtrak'],['NJT_123','NJT_63','NJ Transit'],['NJT_142','NJT_63','NJ Transit']]) {
  context.from=from;context.to=to;context.agency=agency;
  context.testDate = serviceDateForGroups([directTrips(from,to,agency)], calendar, {label:`${from} → ${to} ${agency}`});
  assert(run(`findRoutes(from,to,0,'depart',dateFromIso(testDate)).some(r=>r.legs.length===1 && r.legs[0].trip.agency===agency)`),`${from} → ${to} ${agency}`);
}
context.testDate = serviceDateForGroups([directTrips('NJT_123','SEC','NJ Transit'), directTrips('SEC','NYP','NJ Transit')], calendar, {label:'Port Jervis via Secaucus'});
assert(run(`findRoutes('NJT_123','NYP',0,'depart',dateFromIso(testDate)).some(r=>r.legs.length===2 && r.legs[0].toId==='SEC')`));
assert.equal(run(`findRoutes('NJT_123','NHV',0,'depart',dateFromIso(testDate)).length`),0,'No special two-transfer exception');
assert(run(`trips.filter(t=>t.agency==='NJ Transit').every(t=>/^[0-9]+$/.test(t.train))`),'No replacement buses');
assert(run(`trips.filter(t=>t.agency==='Amtrak').some(t=>t.stops.some(s=>s.id==='NWK'))`));
for (const lang of ['en','ko','es']) {
  context.lang=lang;
  assert(run(`faqContent[lang].find(f=>f.id==='what-areas-does-moose-train-currently-support').content.includes('Port Jervis')`));
  assert(run(`Boolean(translations[lang].fareUnavailable)`));
}
console.log('NJ Transit fares, station identities, source isolation, Amtrak corridor coverage, and one-transfer searches passed');
