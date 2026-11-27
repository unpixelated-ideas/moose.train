const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../moose.train-departure-board.html'),'utf8');
const context=vm.createContext({preferences:{language:'ko'},document:{createElement:()=>({})}});
vm.runInContext(html.slice(html.indexOf('const koreanNames='),html.indexOf('function words()')),context);
for(const [input,english,korean] of [['MADISON','Madison','매디슨'],['GUILFORD','Guilford','길퍼드'],['Eastbound to New London','New London','뉴 런던'],['Westbound to New Haven Union Station','New Haven','뉴 헤이븐']]){
 context.input=input;assert.equal(vm.runInContext('boardDisplayName(input)',context),english);assert.equal(vm.runInContext('stationName(input)',context),korean);
}
for(const [agency,train,expected] of [['CTrail','CTrail 4400B','4400B'],['CTrail','CT Rail 1699','1699'],['Metro-North','EB1902','EB1902'],['LIRR','2718','2718'],['Amtrak','1150','1150']]){
 context.trip={agency,train};assert.equal(vm.runInContext('boardTrainNumber(trip)',context),expected);
}
for(const [agency,service] of [['Amtrak','Northeast Regional'],['LIRR','Port Washington Branch'],['Metro-North','Harlem Line'],['NJ Transit','Port Jervis Line'],['CTrail','Shore Line East'],['CTrail','Hartford Line']]){
 for(const [mode,expected] of [['railroad',[agency==='CTrail'?service:agency]],['line',[service]],['both',[agency,service]]]){
  context.preferences.trainLabel=mode;
  context.trip={agency,service};
  assert.equal(vm.runInContext('JSON.stringify(boardTrainLabels(trip))',context),JSON.stringify(expected));
 }
}
context.trip={agency:'Amtrak'};
assert.equal(vm.runInContext('boardTrainLabels(trip).join()',context),'Amtrak');
context.allTrips=[
 {agency:'LIRR',stops:[{id:'LIRR_11',name:'Broadway'},{id:'NYP',name:'New York Penn'}]},
 {agency:'NJ Transit',stops:[{id:'NJT_25',name:'Broadway'},{id:'NYP',name:'New York Penn'}]},
];
vm.runInContext(html.slice(html.indexOf('const duplicateStationRailroads ='),html.indexOf('// Shareable board URLs')),context);
assert.deepEqual(
 JSON.parse(vm.runInContext('JSON.stringify(stationOptions().map(s=>[s.id,qualifiedBoardName(s.name,s.railroad)]))',context)),
 [['LIRR_11','Broadway (LIRR)'],['NJT_25','Broadway (NJ Transit)'],['NYP','New York Penn']]
);
console.log('Board station casing, destination names, Korean translation, and train-number formatting passed.');
