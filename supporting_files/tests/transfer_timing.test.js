const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
process.env.TZ = 'America/New_York';
const html = fs.readFileSync(require('path').join(__dirname, '../../index.html'), 'utf8');
function source(name) {
  const start = html.indexOf(`    function ${name}(`);
  const end = html.indexOf('\n    function ', start + 1);
  assert(start >= 0);
  return html.slice(start, end);
}
const context = vm.createContext({Date, Math, MAX_TRANSFER_MINUTES:180, TRANSFER_BUFFER:5,
 transferStationIds:new Set(['STM']), trips:[],
 serviceApplies:(trip,date)=>trip.serviceDate === date.toISOString().slice(0,10),
 firstLegPassesDestinationBeforeTransfer:()=>false, firstLegContinuesToDestinationAfterTransfer:()=>false,
 secondLegServedOriginBeforeTransfer:()=>false, isWaterburyBranch:()=>false,
 searchLegIndex:()=>context.index, matchesSearch:()=>true,
 sortRoutes:x=>x, filterDominatedRoutes:x=>x, dedupeRoutes:x=>x, filterBestTransferConnections:x=>x,
});
for(const name of ['realtimeEventServiceMinutes','routeServiceApplies','localDateWithOffset','dayOffset','makeRoute','minimumTransferMinutes','findRoutes']) vm.runInContext(source(name),context);
context.routeDisplayOffset=()=>0;
const event={epochSeconds:new Date('2026-09-27T00:55:00-04:00').getTime()/1000,minutes:55,delaySeconds:0};
assert.equal(context.realtimeEventServiceMinutes(event,'2026-09-26',1495),1495);
assert.equal(1834-context.realtimeEventServiceMinutes(event,'2026-09-26',1495),339);
assert.equal(context.realtimeEventServiceMinutes({minutes:55,delaySeconds:0},'',1495),1495);
assert.equal(context.realtimeEventServiceMinutes({minutes:2,delaySeconds:180},'',1439),1442);
assert.equal(context.realtimeEventServiceMinutes({epochSeconds:new Date('2026-11-02T00:55:00-05:00').getTime()/1000,minutes:55},'2026-11-01',1495),1495);
const date=new Date('2026-09-26T12:00:00Z');
const trip={key:'a',serviceDate:'2026-09-26'};
assert(context.routeServiceApplies({legs:[{trip,departure:1834}]},date,0,'depart'));
assert(!context.routeServiceApplies({legs:[{trip:{serviceDate:'2026-09-27'},departure:1834}]},date,0,'depart'));
context.routeServiceApplies=()=>true;
const first={trip,fromId:'GCT',toId:'STM',departure:1418,arrival:1495};
for(const [wait,count] of [[4,0],[5,1],[180,1],[181,0],[339,0]]) {
 const second={trip:{key:'b'},fromId:'STM',toId:'MYS',departure:1495+wait,arrival:1608+wait};
 context.index=new Map([['GCT',[first]],['STM',[second]]]);
 assert.equal(context.findRoutes('GCT','MYS',1400,'depart',date).length,count,`wait ${wait}`);
 assert.equal(context.findRoutes('GCT','MYS',1400,'depart',date,Infinity).length,wait>=5?1:0);
}
// Station minimums apply regardless of operator, including same-operator transfers.
for (const [station, minimum] of [['NYP',20], ['GCT',15], ['STM',5]]) {
 for (const agency of ['LIRR','Metro-North','Amtrak']) {
  for (const wait of [minimum-1, minimum]) {
   const inbound={...first,toId:station,trip:{key:'a',agency}};
   const outbound={trip:{key:'b',agency},fromId:station,toId:'MYS',departure:1495+wait,arrival:1608+wait};
   context.transferStationIds=new Set([station]);
   context.index=new Map([['ORIGIN',[inbound]],[station,[outbound]]]);
   assert.equal(context.findRoutes('ORIGIN','MYS',1400,'depart',date).length,wait>=minimum?1:0,`${station} ${agency} wait ${wait}`);
  }
 }
}
context.transferStationIds=new Set(['STM']);
context.index=new Map([['GCT',[first]],['STM',[{trip:{key:'b'},fromId:'STM',toId:'MYS',departure:1834,arrival:1900}]]]);
assert(!html.includes('data-i18n="transferBuffer"'), 'Homepage hides the minimum connection time');
vm.runInContext(source('emptyStateForSearch'),context);
context.latestSearchDateForStationSelection=()=>'';
context.stationSearchIds=s=>[s.id];
context.requiresUnsupportedMultiTransfer=()=>false;
assert.equal(context.emptyStateForSearch({id:'GCT'},{id:'MYS'},date,1400,'depart').key,'transferWaitTooLong');
context.index=new Map();
assert.equal(context.emptyStateForSearch({id:'GCT'},{id:'MYS'},date,1400,'depart').key,'noResults');
new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
console.log('Transfer timing, service dates, limits, and messaging passed.');
