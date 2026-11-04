const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../moose.train-departure-board.html'),'utf8');
const code=html.slice(html.indexOf("document.getElementById('board-settings-button').addEventListener"),html.indexOf("document.getElementById('halloween-toggle').addEventListener"));
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:'',handlers:{},addEventListener(type,fn){this.handlers[type]=fn;},showModal(){this.open=true;},close(){this.open=false;},focus(){}});return elements.get(id);}
const preferences={visibleTrains:7,direction:'both',walkingTime:''};let saves=0,applies=0,count;
vm.runInNewContext(code,{document:{getElementById:element},preferences,Number,JSON,localStorage:{setItem(){saves++;}},updateBoardSettingsLabels:n=>count=n,applyPreferences:()=>applies++,normalizeWalkingTime:v=>v==='bad'?null:v.replace('-','–'),boardSettingsText:()=>({error:'Invalid'})});
element('board-settings-button').handlers.click();
element('board-size').value='11';element('board-size').handlers.input({target:element('board-size')});element('board-direction').value='west';element('board-walking-time').value='5-10';
assert.equal(count,5);assert.deepEqual(preferences,{visibleTrains:7,direction:'both',walkingTime:''});assert.equal(saves,0);
element('board-settings-close').handlers.click();
assert.equal(saves,0);assert.equal(applies,0);
element('board-settings-button').handlers.click();assert.equal(element('board-size').value,9);assert.equal(element('board-direction').value,'both');assert.equal(element('board-walking-time').value,'');
element('board-size').value='5';element('board-direction').value='east';element('board-walking-time').value='bad';element('board-settings-form').handlers.submit({preventDefault(){}});assert.equal(saves,0);
element('board-walking-time').value='5-10';element('board-settings-form').handlers.submit({preventDefault(){}});
assert.deepEqual(preferences,{visibleTrains:11,direction:'east',walkingTime:'5–10'});assert.equal(saves,1);assert.equal(applies,1);assert.equal(element('board-settings-dialog').open,false);
console.log('Settings remain drafts until Save; X discards edits, reopening restores saved values, and validation prevents invalid saves.');
