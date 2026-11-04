const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.resolve(__dirname, '../../moose.train-departure-board.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
const fixedNow = Date.parse('2026-11-03T15:00:00Z'); // 10:00 Eastern
class Clock extends Date { constructor(...args) { super(...(args.length ? args : [fixedNow])); } static now() { return fixedNow; } }
const context = vm.createContext({ Intl, TextDecoder, Uint8Array, Date: Clock, preferences:{direction:'both'}, console, setInterval() {}, document: { addEventListener() {} } });
vm.runInContext(script.slice(0, script.indexOf('function upcoming(')), context);
vm.runInContext(script.slice(script.indexOf('function upcoming('), script.indexOf('function cell(')), context);
const run = code => vm.runInContext(code, context);
// Real GTFS-RT wire format, including MTA field 1005 and signed delay values.
function varint(value) { let n=BigInt.asUintN(64,BigInt(value));const bytes=[];do{let b=Number(n&127n);n>>=7n;bytes.push(b|(n?128:0));}while(n);return Buffer.from(bytes); }
function wire(id,value) { const bytes=typeof value==='string'?Buffer.from(value):value;return Buffer.isBuffer(bytes)?Buffer.concat([varint(id*8+2),varint(bytes.length),bytes]):Buffer.concat([varint(id*8),varint(value)]); }
const event=Buffer.concat([wire(1,-60),wire(2,Math.floor(fixedNow/1000)+600)]);
const stop=Buffer.concat([wire(4,'11'),wire(3,event),wire(1005,wire(1,'2'))]);
const descriptor=Buffer.concat([wire(1,'internal'),wire(3,'20261103'),wire(5,'1')]);
const update=Buffer.concat([wire(1,descriptor),wire(2,stop)]);
context.encoded=new Uint8Array(Buffer.concat([wire(1,wire(3,Math.floor(fixedNow/1000))),wire(2,Buffer.concat([wire(1,'436'),wire(3,update)]))]));
assert.equal(run('decodeBoardLiveFeed(encoded).entity[0].tripUpdate.stopTimeUpdate[0].railroad.track'),'2');
assert.equal(run('decodeBoardLiveFeed(encoded).entity[0].tripUpdate.stopTimeUpdate[0].departure.delay'),-60);
context.truncated=new Uint8Array([10,100,1]);
assert.throws(()=>run('decodeBoardLiveFeed(truncated)'),/Invalid live feed length/);

run(`
selectedStation={id:'GCT',name:'Grand Central'};
var day=new Date(2026,10,3);
var trip={agency:'Metro-North',train:'123',staticRouteId:'3',staticTripId:'static-123',serviceDates:'2026-11-03',serviceDays:'',stops:[{id:'GCT',departure:590,pickupType:'0'},{id:'STM',departure:650,pickupType:'0'}]};
var prediction=Date.now()/1000+600;
var message={header:{timestamp:Date.now()/1000},entity:[{id:'123',tripUpdate:{trip:{tripId:'internal-123',routeId:'3',startDate:'20261103'},stopTimeUpdate:[{stopId:APP_TO_MNR_GTFS_STOP_ID.get('GCT'),departure:{time:prediction}},{stopId:APP_TO_MNR_GTFS_STOP_ID.get('STM'),arrival:{time:prediction+3600}}]}}]};
function install(){boardLiveSnapshots.set('Metro-North',normalizeBoardLive(message,'Metro-North'));}
install();
`);
assert.equal(run("boardLiveAtStop(trip,trip.stops[0],day,0).status"), 'live');
assert.equal(run('upcoming([trip]).length'), 1, 'Keep delayed trains whose scheduled departure has passed');
assert.equal(run('upcoming([trip])[0].relative'), 610);
run("message.entity[0].tripUpdate.stopTimeUpdate[0].railroad={track:'105'};install();");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).track'), '105', 'Use the selected station track');
run('delete message.entity[0].tripUpdate.stopTimeUpdate[0].departure;install();');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).status'), 'track', 'Track does not require a departure prediction');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).track'), '105');
run('message.entity[0].tripUpdate.stopTimeUpdate[0].departure={time:prediction};install();');

assert.equal(run('boardLiveAtStop(trip,trip.stops[0],new Date(2026,10,4),0)'), null, 'Service date must match');
run("message.entity[0].tripUpdate.trip.routeId='2';install();");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'), null, 'Do not match another line');
run("message.entity[0].tripUpdate.trip.routeId='3';message.entity[0].tripUpdate.trip.scheduleRelationship=3;install();");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).status'), 'canceled');
run('message.entity[0].tripUpdate.trip.scheduleRelationship=0;message.entity[0].tripUpdate.stopTimeUpdate[0].scheduleRelationship=1;install();');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).status'), 'skipped');
run('message.entity[0].tripUpdate.stopTimeUpdate[0].scheduleRelationship=2;install();');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'), null, 'NO_DATA must not imply a live prediction');
run('message.entity[0].tripUpdate.stopTimeUpdate[0].scheduleRelationship=0;message.entity[0].tripUpdate.stopTimeUpdate[0].departure={delay:1200};install();');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).relative'), 610, 'Delay-only departure predictions are applied');
run('message.entity[0].tripUpdate.stopTimeUpdate.reverse();install();');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'), null, 'Reject opposite-direction stop order');
run('message.entity[0].tripUpdate.stopTimeUpdate.reverse();install();');
run('boardLiveSnapshots.get("Metro-North").timestamp-=121;');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'), null, 'Expired feed falls back to schedule');
assert.throws(() => run('normalizeBoardLive({...message,header:{timestamp:Date.now()/1000-121}},"Metro-North")'), /Stale/);
run(`
trip={...trip,agency:'LIRR',staticTripId:'lirr-123',staticRouteId:'1'};
message.entity[0].tripUpdate.trip={tripId:'lirr-123',routeId:'1',startDate:'20261103'};
message.entity[0].tripUpdate.stopTimeUpdate=[{stopId:APP_TO_LIRR_GTFS_STOP_ID.get('GCT'),departure:{time:prediction}},{stopId:APP_TO_LIRR_GTFS_STOP_ID.get('NYP'),arrival:{time:prediction+300}}];
trip.stops=[trip.stops[0],{id:'NYP',departure:620}];
boardLiveSnapshots.set('LIRR',normalizeBoardLive(message,'LIRR'));
`);
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).status'), 'live');
run("trip.staticTripId='another-trip'");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'), null, 'LIRR requires exact static trip ID');
run(`
boardLiveSnapshots.delete('LIRR');
trip={...trip,train:'2718',staticDirectionId:'0',staticRouteId:'7',stops:[{id:'GCT',departure:503,pickupType:'0'},{id:'LIRR_65',departure:560}]};
var signData={is_stale:false,is_suppressed:false,arrivals:[{railroad:'LIRR',train_num:'2718',run_date:'2026-11-03',direction:'E',time:Date.parse('2026-11-03T13:23:00Z')/1000,track:'203',sched_track:'U3',status:{canceled:false}}]};
boardTrainTimeTracks.set('GCT',normalizeTrainTimeTracks(signData,'GCT',Date.now()/1000));
`);
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).track'),'203','TrainTime supplies a track when GTFS is unavailable');
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0).status'),'track','Track availability alone is not a live ETA');
run("trip.train='9999'");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'),null,'Do not borrow another train track');
run("trip.train='2718';signData.arrivals[0].track='';boardTrainTimeTracks.set('GCT',normalizeTrainTimeTracks(signData,'GCT',Date.now()/1000));");
assert.equal(run('boardLiveAtStop(trip,trip.stops[0],day,0)'),null,'Do not substitute the scheduled platform group for a live track');
assert.throws(()=>run("normalizeTrainTimeTracks({...signData,is_stale:true},'GCT',Date.now()/1000)"),/stale/);
console.log('Display board realtime matching, delayed departures, cancellations, skipped stops, freshness, and LIRR identity passed.');
