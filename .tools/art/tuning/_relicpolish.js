// One-shot relic polish, round 7. Relics are now close but still too bright for vanilla's muted
// metal (highlightPct 19.6 vs 5.1, p90 0.846 vs 0.681) and their content reaches the frame edge
// (ringAlphaPct 6.8 vs 3.4).
// Throwaway tooling - run once with `node _relicpolish.js`.
'use strict';
const fs = require('fs');
const path = require('path');
const FILE = path.join(__dirname, 'paint.js');
let t = fs.readFileSync(FILE, 'utf8');
const R = [
  // dimmer, dustier metals - vanilla relics average luma 0.371 against the powers' 0.462
  [`    bronze:    ['#fff4d8', '#f6d79c', '#d5a44e', '#a87b2c', '#7a5518', '#4d350c', '#241804'],
    starlight: ['#f6fbff', '#cfe8ff', '#96c4f7', '#5f8ede', '#3d63b4', '#233c80', '#0e1740'],`,
   `    bronze:    ['#f3e2bd', '#dcb877', '#b08539', '#825c1f', '#5a3c11', '#372308', '#180f04'],
    starlight: ['#f6fbff', '#cfe8ff', '#96c4f7', '#5f8ede', '#3d63b4', '#233c80', '#0e1740'],`],
  [`    ivory:   ['#fffbf2', '#f2e7cf', '#dbc9a2', '#b7a077', '#897352', '#5a4931', '#2b2114'],
    amber:   ['#fff3d0', '#ffd98a', '#e8a72c', '#b87a12', '#82530a', '#523304', '#261701'],`,
   `    ivory:   ['#f4ecdb', '#ddd0b1', '#c0ac83', '#9a855e', '#6f5c3e', '#463824', '#201a10'],
    amber:   ['#f2e2b6', '#e6bf6d', '#c88c1c', '#99630c', '#6a4206', '#402702', '#1c1101'],`],
  [`  var WARM_MUL = 1;   // relics take a dimmer, cooler key light than powers`,
   `  var WARM_MUL = 1;   // relics take a dimmer, cooler key light than powers (0.30 for relics)`],
  [`    WARM_MUL = def.group === 'relic' ? 0.45 : 1;`, `    WARM_MUL = def.group === 'relic' ? 0.30 : 1;`],
  // keep relic content off the frame edge: vanilla relic ringAlphaPct is 3.4 (powers 3.6, but the
  // relic atlas slices are trimmed so the 256 sources are the honest reference here)
  [`    var sBboxMax = 0.965 * RENDER / Math.max(bw, bh);`,
   `    var sBboxMax = (def.group === 'relic' ? 0.90 : 0.965) * RENDER / Math.max(bw, bh);`],
  // the bronzeBright relic should read as gilded, not as a lamp
  [`    bronzeBright: ['#fff8da', '#ffe07a', '#e8b32c', '#b98a14', '#8a6508', '#5a4104', '#2b1e01'],`,
   `    bronzeBright: ['#f7ebc4', '#eccf7c', '#cf9c22', '#9f7610', '#734f06', '#472f03', '#211601'],`],
];
let n = 0; const miss = [];
for (const [a, b] of R) {
  if (!t.includes(a)) { miss.push(a.split('\n')[0].trim().slice(0, 70)); continue; }
  t = t.replace(a, b); n++;
}
fs.writeFileSync(FILE, t);
console.log('patched ' + n + '/' + R.length);
if (miss.length) { console.log('MISSED:'); miss.forEach(x => console.log('  ' + x)); }
