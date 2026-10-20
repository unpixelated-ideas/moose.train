const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.resolve(__dirname, '../../index.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('    init();', '');
const context = vm.createContext({ document: { getElementById: () => ({}), querySelector() {} }, window: {}, console, Date });
vm.runInContext(script, context);
const run = code => vm.runInContext(code, context);
run('currentLanguage = "ko"');
const stations = run('stationIndex.map(station => station.name)');
for (const name of stations) {
  const label = run(`displayStationName(${JSON.stringify(name)})`);
  assert.match(label, /[가-힣]/, `${name} needs a Korean transliteration`);
  assert(label.startsWith(`${name} (`), `${name} retains its English name`);
}
for (const language of ['en', 'es']) {
  run(`currentLanguage = ${JSON.stringify(language)}`);
  for (const name of stations) {
    assert.equal(run(`displayStationName(${JSON.stringify(name)})`), name);
  }
}
console.log(`Verified Korean labels and English/Spanish names for all ${stations.length} stations.`);
