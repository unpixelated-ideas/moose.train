// Test the production functions and committed timetable, not copies of the logic.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
process.env.TZ = 'America/New_York';
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({document:{getElementById:()=>({}),querySelector(){}},window:{},console,Date});
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);
run(`
  const fare = (from,to,peak='OFF_PEAK') => calculateMetroNorthFare({originStationId:from,destinationStationId:to,peakStatus:peak});
  const leg = (fromId,toId,direction='0',peak='OFF_PEAK') => ({fromId,toId,trip:{agency:'Metro-North',staticDirectionId:direction,farePeakStatus:peak}});
`);
for (const [from,to,peak,cents] of [
  ['GCT','YNY','OFF_PEAK',925],['YNY','GCT','PEAK',1250],
  ['GCT','CRT','OFF_PEAK',1175],['GCT','POU','PEAK',2825],
  ['GCT','MNR_177','OFF_PEAK',2200],['GCT','MNR_74','PEAK',1375],
  ['YNY','POU','OFF_PEAK',1675],['POU','YNY','PEAK',1675],
  ['FOR','MNR_74','OFF_PEAK',450],['MNR_74','FOR','PEAK',450],
  ['GCT','MNR_9','OFF_PEAK',525],['MNR_61','H125','PEAK',725],
  ['GCT','STM','OFF_PEAK',1325],['STM','NHV','PEAK',950],
]) assert.equal(run(`fareAmountCents(fare('${from}','${to}','${peak}'))`),cents,`${from} → ${to} ${peak}`);
assert.equal(run(`fare('GCT','YANKEES')`),null,'Stadium trains must remain unpriced');
assert.equal(run(`calculateMetroNorthRouteFare({legs:[leg('GCT','MNR_94'),leg('MNR_94','MNR_177')]}).amount`),22,'Southeast transfer has one fare');
assert.equal(run(`calculateMetroNorthRouteFare({legs:[leg('GCT','MNR_94','0','PEAK'),leg('MNR_94','MNR_177','0','OFF_PEAK')]}).amount`),29.75,'Terminal train determines peak fare with a shuttle');
assert.equal(run(`calculateMetroNorthRouteFare({legs:[leg('YNY','H125','1'),leg('H125','MNR_74')]}).amountCents`),1950,'Direction change requires two tickets');
assert.equal(run(`calculateMetroNorthRouteFare({legs:[leg('FOR','H125','1'),leg('H125','MNR_9')]}).amountCents`),1050,'No single CityTicket for direction change');
assert.equal(run(`calculateMetroNorthRouteFare({legs:[leg('YNY','CRT'),leg('CRT','MNR_74','1') ]})`),null,'Unverified reversal stays unpriced');
assert.equal(run(`calculateRouteFare({legs:[leg('YNY','CRT'),{fromId:'CRT',toId:'POU',trip:{agency:'Amtrak'}}]})`),null,'Do not quote partial mixed-operator totals');
assert.equal(run(`new Set(stationIndex.map(s=>s.id)).size === stationIndex.length`),true,'Unique station IDs');
assert.equal(run(`stationIndex.filter(s=>s.name==='Yankees-E 153 St').length`),1,'Keep existing stadium identity');
assert.equal(run(`stationIndex.some(s=>/Highbridge|Springdale MW|Port Jervis|Pascack/i.test(s.name))`),false);
run(`
  const liveDate = dateFromIso('2026-10-19');
  const hudsonTrip = {agency:'Metro-North',service:'Hudson Line',route:'Hudson Line',train:'871',stops:[{id:'GCT'},{id:'YNY'},{id:'POU'}]};
  const liveUpdate = {operator:'Metro-North',trainNumber:'871',routeId:'1',serviceDate:'2026-10-19',stopUpdates:[{stopId:'1'},{stopId:'18'},{stopId:'51'}]};
`);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[liveUpdate]},liveDate) === liveUpdate`),true);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[{...liveUpdate,routeId:'2'}]},liveDate)`),null);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[liveUpdate,{...liveUpdate}]},liveDate)`),null);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[{...liveUpdate,serviceDate:'2026-10-18'}]},liveDate,liveDate)`),null);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[{...liveUpdate,stopUpdates:[{stopId:'51'},{stopId:'18'},{stopId:'1'}]}]},liveDate)`),null);
assert.equal(run(`metroNorthRealtimeTripAllowsRouteId({service:'Harlem Line',route:'Harlem Line'},'2')`),true);
assert.equal(run(`metroNorthRealtimeTripAllowsRouteId({service:'New Haven Line',route:'New Haven Line'},'2')`),false);
assert.equal(run(`legFromStops({}, {departure:10,pickupType:'1'}, {arrival:20})`),null);
assert.equal(run(`legFromStops({}, {departure:10}, {arrival:20,dropOffType:'1'})`),null);
run(`
  const canceled = {...liveUpdate,isCanceled:true,stopUpdates:[]};
  const now = Math.floor(Date.now()/1000);
  const cancellationFeed = {header:{timestamp:now},entity:[{id:'871',tripUpdate:{trip:{tripId:'internal',routeId:'1',startDate:'20261019',scheduleRelationship:3}}}]};
`);
assert.equal(run(`normalizeMetroNorthRealtimeFeed(cancellationFeed).tripUpdates[0].isCanceled`),true);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[canceled]},liveDate,liveDate) === canceled`),true);
assert.equal(run(`matchMetroNorthRealtimeTrip(hudsonTrip,{tripUpdates:[{...canceled,routeId:''}]},liveDate,liveDate)`),null);
assert.equal(run(`normalizeMetroNorthRealtimeFeed({header:{timestamp:Math.floor(Date.now()/1000)-121},entity:[]})`),null);
context.schedule = JSON.parse(fs.readFileSync(path.join(root, 'supporting_files/assets/schedule/search.json'), 'utf8'));
run(`const prepared = decodeSearchSchedule(schedule); trips = prepared.trips; stations = uniqueStations(prepared.metadata); stationSequencesByDirection = buildStationSequencesByDirection(trips);`);
const downloads = run('buildTimetableCsvLinks(prepared.metadata)');
assert(downloads.some(link=>link.href.includes('mnr_gtfs_') && link.href.endsWith('.csv.gz')));
for (const link of downloads) assert(fs.existsSync(path.join(root, link.href)), `Missing timetable download: ${link.href}`);
const testDate = run(`(() => {
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
})()`);
const search = (from,to,date=testDate) => run(`findRoutesForStationSelection({id:'${from}'},{id:'${to}'},360,'leave',dateFromIso('${date}'))`);
for (const destination of ['YNY','CRT','POU']) {
  const started = performance.now();
  const routes = search('NYC_RAIL',destination);
  assert(routes.some(r=>r.legs.length===1 && r.legs[0].trip.agency==='Metro-North'),`MNR comparison ${destination}`);
  assert(routes.some(r=>r.legs.length===1 && r.legs[0].trip.agency==='Amtrak'),`Amtrak comparison ${destination}`);
  assert(routes.filter(r=>r.legs[0].trip.agency==='Amtrak').every(r=>r.legs[0].fromId==='NYP'));
  console.log(`NYC → ${destination}: ${routes.length} options (${Math.round(performance.now()-started)} ms)`);
}
for (const [from,to] of [['GCT','MNR_74'],['GCT','MNR_177'],['YNY','MNR_74'],['STM','MNR_74'],['GCT','YANKEES']]) {
  const routes=search(from,to);
  assert(routes.length,`No timetable routes: ${from} → ${to}`);
  assert(routes.every(r=>r.legs.length<=2));
  if (to==='YANKEES') {
    context.stadiumRoute=routes[0];
    assert.equal(run('calculateRouteFare(stadiumRoute)'),null);
  }
}
assert(run(`trips.some(t=>t.service==='Harlem Line' && t.stops.some(s=>s.id==='MNR_177'))`));
console.log('Hudson/Harlem production fares, live matching, boarding restrictions, station coverage, and timetable searches passed.');
