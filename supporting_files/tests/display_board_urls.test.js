const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../../moose.train-departure-board.html'), 'utf8');
const code = html.slice(html.indexOf('// Shareable board URLs'), html.indexOf('let stationSearchMatches=[];'));
const duplicateStationRailroads = require('../reference/duplicate_station_railroads.json');
const stations = [{id:'OSB',name:'Old Saybrook'},{id:'CL',name:'Clinton'},{id:'LIRR_11',name:'Broadway'},{id:'NJT_25',name:'Broadway'},
 {id:'WPT',name:'Westport'},{id:'WSP',name:'Westport'},
 {id:'MAD',name:'Madison'},{id:'NJT_77',name:'Madison'},
 {id:'LIRR_130',name:'Murray Hill'},{id:'NJT_99',name:'Murray Hill'}];
async function check(query, expected) {
 const location = new URL('https://moose.train/moose.train-departure-board.html'+query);
 const preferences = {direction:'west',walkingTime:'99',language:'en'};
 let selected = stations[0], result;
 const context = vm.createContext({URL,URLSearchParams,location,preferences,console,allTrips:[],duplicateStationRailroads,
  stationOptions:()=>stations,readSchedule:async()=>[],
  normalizeWalkingTime:value=>/^\d+(?:-\d+)?$/.test(value||'')?value.replace('-','–'):'',
  selectStation:station=>{selected=station;context.selectedStation=station;},selectedStation:selected,
  applyPreferences:()=>{},refresh:()=>{},history:{replaceState:(_,__,url)=>{result=new URL(url);}}
 });
 vm.runInContext(code,context);
 await vm.runInContext('initializeBoardUrl()',context);
 assert.equal(selected.name,expected[0]);assert.equal(preferences.direction,expected[1]);assert.equal(preferences.walkingTime,expected[2]);
 assert.equal(result.searchParams.get('station'),expected[3]);assert.equal(preferences.visibleTrains,Number(new URLSearchParams(query).get('rows'))||8);
 if(expected[4])assert.equal(selected.id,expected[4]);
 return result;
}
(async()=>{
 let url=await check('?station=clinton&direction=E&walk=5-10',['Clinton','east','5–10','clinton']);
 assert.equal(url.searchParams.get('direction'),'E');assert.equal(url.searchParams.get('walk'),'5-10');
 url=await check('?station=old-saybrook',['Old Saybrook','both','','old-saybrook']);
 assert.equal(url.searchParams.has('direction'),false);assert.equal(url.searchParams.has('walk'),false);
 await check('?station=broadway-nj-transit&direction=W',['Broadway','west','','broadway-nj-transit']);
 await check('?station=westport',['Westport','both','','westport','WPT']);
 await check('?station=westport-amtrak',['Westport','both','','westport-amtrak','WSP']);
 await check('?station=madison',['Madison','both','','madison-shore-line-east','MAD']);
 await check('?station=murray-hill',['Murray Hill','both','','murray-hill-lirr','LIRR_130']);
 await check('?station=clinton&rows=11',['Clinton','both','','clinton']);
 await check('?station=clinton&rows=5',['Clinton','both','','clinton']);
 await check('?station=clinton&direction=invalid&walk=invalid',['Clinton','both','','clinton']);
 console.log('Departure board URL restoration, defaults, ranges, disambiguation, and invalid options passed.');
})().catch(error=>{console.error(error);throw error;});
