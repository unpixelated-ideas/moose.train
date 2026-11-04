const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../../moose.train-departure-board.html'), 'utf8');
const code = html.slice(html.indexOf('// Shareable board URLs'), html.indexOf('let stationSearchMatches=[];'));
const stations = [{id:'OSB',name:'Old Saybrook'},{id:'CL',name:'Clinton'},{id:'LIRR_11',name:'Broadway'},{id:'NJT_25',name:'Broadway'}];
async function check(query, expected) {
 const location = new URL('https://moose.train/moose.train-departure-board.html'+query);
 const preferences = {direction:'west',walkingTime:'99'};
 let selected = stations[0], result;
 const context = vm.createContext({URL,URLSearchParams,location,preferences,console,allTrips:[],
  stationOptions:()=>stations,loadEmbeddedTrips:async()=>[],
  normalizeWalkingTime:value=>/^\d+(?:-\d+)?$/.test(value||'')?value.replace('-','–'):'',
  selectStation:station=>{selected=station;context.selectedStation=station;},selectedStation:selected,
  applyPreferences:()=>{},refresh:()=>{},history:{replaceState:(_,__,url)=>{result=new URL(url);}}
 });
 vm.runInContext(code,context);
 await vm.runInContext('initializeBoardUrl()',context);
 assert.equal(selected.name,expected[0]);assert.equal(preferences.direction,expected[1]);assert.equal(preferences.walkingTime,expected[2]);
 assert.equal(result.searchParams.get('station'),expected[3]);assert.equal(preferences.visibleTrains,Number(new URLSearchParams(query).get('rows'))||7);
 return result;
}
(async()=>{
 let url=await check('?station=clinton&direction=E&walk=5-10',['Clinton','east','5–10','clinton']);
 assert.equal(url.searchParams.get('direction'),'E');assert.equal(url.searchParams.get('walk'),'5-10');
 url=await check('?station=old-saybrook',['Old Saybrook','both','','old-saybrook']);
 assert.equal(url.searchParams.has('direction'),false);assert.equal(url.searchParams.has('walk'),false);
 await check('?station=broadway-nj-transit&direction=W',['Broadway','west','','broadway-nj-transit']);
 await check('?station=clinton&rows=11',['Clinton','both','','clinton']);
 await check('?station=clinton&rows=5',['Clinton','both','','clinton']);
 await check('?station=clinton&direction=invalid&walk=invalid',['Clinton','both','','clinton']);
 console.log('Departure board URL restoration, defaults, ranges, disambiguation, and invalid options passed.');
})().catch(error=>{console.error(error);throw error;});
