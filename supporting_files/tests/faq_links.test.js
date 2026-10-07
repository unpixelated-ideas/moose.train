const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const page = fs.readFileSync(path.join(__dirname, '../../faq.html'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
for (const html of [page, app]) {
  for (const m of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) if (m[1].trim()) new vm.Script(m[1]);
}
function source(name) {
  const start = page.indexOf(`    function ${name}(`);
  return page.slice(start, page.indexOf('\n    function ', start + 1));
}
const c = vm.createContext({URL, location:{href:'https://moose.train/faq.html?lang=ko',hash:''}});
vm.runInContext(source('extractObject') + source('faqLink') + source('openLinkedFaq'), c);
const content = c.extractObject(app, 'faqContent');
const ids = content.en.map(x=>x.id);
assert.equal(new Set(ids).size,ids.length);
for(const lang of ['en','ko','es']) {
 assert.deepEqual(Array.from(content[lang],x=>x.id),Array.from(ids));
 c.currentLanguage=lang;
 const url=new URL(c.faqLink('does-moose-train-calculate-ticket-prices'));
 assert.equal(url.searchParams.get('lang'),lang);
 assert.equal(url.hash,'#does-moose-train-calculate-ticket-prices');
}
let scrolled=false; const details={open:false};
c.document={getElementById:id=>id===ids[8]?{classList:{contains:()=>true},querySelector:()=>details,scrollIntoView:()=>{scrolled=true;}}:null};
c.location.hash='#'+ids[8];c.openLinkedFaq();assert(details.open);assert(scrolled);
c.location.hash='#%broken';assert.doesNotThrow(()=>c.openLinkedFaq());
console.log('FAQ IDs, localized URLs, anchor expansion, and script syntax passed.');
