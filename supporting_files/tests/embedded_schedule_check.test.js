const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');

const builder = fs.readFileSync(path.join(__dirname, '../scripts/build_search_schedule.js'), 'utf8');
const source = builder.slice(builder.indexOf('function normalizeEmbeddedSchedule('), builder.indexOf('if (fs.existsSync(boardPath))'));
const context = vm.createContext({ Buffer, zlib });
vm.runInContext(source, context);
const normalize = context.normalizeEmbeddedSchedule;
const board = (data, level, title = 'Board') => Buffer.from(`<title>${title}</title><script id="all-stations-schedule" type="application/octet-stream">${zlib.gzipSync(data, { level }).toString('base64')}</script>`);
const data = JSON.stringify({ trips: Array(100).fill({ station: 'OSB' }) });
assert.equal(normalize(board(data, 1)), normalize(board(data, 9)));
assert.notEqual(normalize(board(data, 9)), normalize(board('{}', 9)));
assert.notEqual(normalize(board(data, 9)), normalize(board(data, 9, 'Changed')));
assert.throws(() => normalize(Buffer.from('<script id="all-stations-schedule" type="application/octet-stream">invalid</script>')));
console.log('Embedded schedule checks accept equivalent compression and reject changed or corrupt content.');
