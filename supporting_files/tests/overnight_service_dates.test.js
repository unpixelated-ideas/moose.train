const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
process.env.TZ = 'America/New_York';
const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({ document: {getElementById:()=>({}), querySelector(){}}, window:{}, Date, console });
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);
run(`trips = [{key:'amtrak-66-fixture', agency:'Amtrak',service:'Northeast Regional',route:'Northeast Regional',direction:'east',train:'66',staticTripId:'308343',
  serviceDays:'weekday',serviceStartDate:'2026-09-28',serviceEndDate:'2026-09-28',stops:[
  {id:'NYP',name:'New York Penn',index:0,sequence:0,arrival:1751,departure:1784},
  {id:'OSB',name:'Old Saybrook',index:1,sequence:1,arrival:1914,departure:1914}]}];`);
const date = '2026-09-29';
function search(origin='NYP', mode='leave', time=60, day=date, destination='OSB') {
  return run(`findRoutesForStationSelection({id:${JSON.stringify(origin)}},{id:${JSON.stringify(destination)}},${time},${JSON.stringify(mode)},dateFromIso(${JSON.stringify(day)}))`);
}
function render(route, mode='leave', time=60, day=date) {
 context.route = route;
 return run(`renderRoute(route,${time},${JSON.stringify(mode)},dateFromIso(${JSON.stringify(day)}),'test',false)`);
}
for (const origin of ['NYP','NYC_RAIL']) {
 for (const [mode,time] of [['leave',60],['arrive',480]]) {
  const results = search(origin,mode,time);
  const matches = results.filter(r=>r.legs.length===1 && r.legs[0].trip.staticTripId==='308343');
  assert.equal(matches.length,1,`${origin} ${mode}: train 66 exactly once`);
  const route = matches[0];
  assert.equal(route.departure,344); assert.equal(route.arrival,474); assert.equal(route.duration,130);
  assert.equal(route.legs[0].originStop.departure,1784,'GTFS time stays intact');
  assert.equal(route.legs[0].serviceDate.getDate(),28);
  const rendered = render(route,mode,time);
  assert.match(rendered,/5:44 AM/); assert.match(rendered,/7:54 AM/); assert.match(rendered,/2h 10m/);
  assert(!rendered.includes('Next day'));
 }
}
function trip(key, times, overrides={}) {
 return {key, agency:'Test',service:'Test',route:'Test',direction:'east',train:key,
 serviceDays:'weekday',serviceStartDate:'2026-09-28',serviceEndDate:'2026-09-28',
 stops:times.map(([id,arrival,departure],index)=>({id,name:id,index,sequence:index,arrival,departure})),...overrides};
}
function setTrips(items) { context.items=items; run('trips = items'); }
const overnight = trip('night',[['NYP',null,1784],['OSB',1914,null]]);
setTrips([overnight]); assert.equal(search().length,1);
setTrips([{...overnight,serviceDays:'sunday'}]); assert.equal(search().length,0,'inactive original service day');
setTrips([{...overnight,serviceDays:'sunday',serviceDates:'2026-09-28'}]); assert.equal(search().length,1,'addition');
setTrips([{...overnight,rawNotes:'does not operate 2026-09-28'}]); assert.equal(search().length,0,'removal');
setTrips([{...overnight,serviceStartDate:'2026-09-29',serviceEndDate:'2026-09-30'}]); assert.equal(search().length,0,'before service range');
setTrips([{...overnight,serviceEndDate:'2026-09-27'}]); assert.equal(search().length,0,'after service range');
setTrips([trip('long',[['NYP',null,3224],['OSB',3354,null]],{serviceStartDate:'2026-09-27',serviceEndDate:'2026-09-27',serviceDays:'sunday'})]);
for(const [mode,time] of [['leave',60],['arrive',480]]) {
 const results=search('NYP',mode,time); assert.equal(results.length,1,'53:44 departure');
 assert.equal(results[0].departure,344); assert.match(render(results[0],mode,time),/5:44 AM/);
}
setTrips([trip('day',[['NYP',null,600],['OSB',660,null]],{serviceEndDate:'2026-10-01'})]);
for(const [mode,time] of [['leave',540],['arrive',720]]) {
 const results=search('NYP',mode,time); assert.equal(results.length,1,'no adjacent-day duplicates');
 assert.equal(results[0].duration,60); assert.match(render(results[0],mode,time),/10:00 AM/);
}
const first=trip('first',[['NYP',null,1410],['NHV',1450,null]]);
const second=trip('second',[['NHV',null,20],['OSB',60,null]],{serviceStartDate:date,serviceEndDate:date});
setTrips([first,second]);
for(const [mode,time,day] of [['leave',1380,'2026-09-28'],['arrive',90,date]]) {
 const routes=search('NYP',mode,time,day); assert.equal(routes.length,1,'cross-service-date transfer');
 const route=routes[0]; assert.equal(route.legs.length,2); assert.equal(route.duration,90);
 assert.equal(route.legs[1].departure-route.legs[0].arrival,10);
 const rendered=render(route,mode,time,day); assert.match(rendered,/11:30 PM/); assert.match(rendered,/12:20 AM/); assert.match(rendered,/1:00 AM/);
}
for(const wait of [4,5,180,181]) {
 setTrips([first,{...second,stops:[{...second.stops[0],departure:10+wait},{...second.stops[1],arrival:60+wait}]}]);
 assert.equal(search('NYP','leave',1380,'2026-09-28').length,wait>=5&&wait<=180?1:0,`buffer/wait ${wait}`);
}
setTrips([trip('restricted',[['NYP',null,null],['OSB',660,null]])]); assert.equal(search().length,0);
setTrips([trip('restricted',[['NYP',null,600],['OSB',null,null]])]); assert.equal(search().length,0);
// Search limits are applied to dated instances, including adjacent calendar days.
setTrips([trip('next',[['NYP',null,60],['OSB',120,null]],{serviceStartDate:date,serviceEndDate:date})]);
assert.equal(search('NYP','leave',60,'2026-09-28').length,0,'24 hours is outside the 23:59 window');
assert.equal(search('NYP','leave',61,'2026-09-28').length,1,'23:59 endpoint is included');
setTrips([trip('previous',[['NYP',null,1320],['OSB',1380,null]])]);
assert.equal(search('NYP','arrive',480).length,1,'arrive by includes previous evening inside window');
setTrips([trip('late',[['NYP',null,720],['OSB',780,null]],{serviceEndDate:date}),
 trip('early',[['NYP',null,600],['OSB',660,null]],{serviceEndDate:date})]);
assert.deepEqual(Array.from(search(),r=>r.departure),[600,720]);
assert.deepEqual(Array.from(search('NYP','arrive',800),r=>r.arrival),[780,660]);
setTrips([overnight, {...overnight,key:'duplicate'}]);
assert.equal(search().length,1,'identical source rows do not duplicate dated results');
// Civil-day offsets stay 1440 minutes even over a DST transition.
setTrips([trip('dst',[['NYP',null,1784],['OSB',1914,null]],
 {serviceStartDate:'2026-11-01',serviceEndDate:'2026-11-01',serviceDays:'sunday'})]);
assert.equal(search('NYP','leave',60,'2026-11-02')[0].departure,344);
// A predicted time remains relative to its source service date until displayed.
assert.equal(run(`realtimeLegDeparture({serviceOffset:-1440,realtime:{departure:{predicted:1789}}})`),349);
console.log('Overnight search and rendered results passed: Penn and combined NYC, both modes, calendars, transfers, 48+ hours, restrictions and duplicates.');
