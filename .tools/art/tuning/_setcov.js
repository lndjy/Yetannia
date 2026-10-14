// One-shot patcher: sets the per-icon coverage target on each add() in paint.js.
// Throwaway tooling - run once with `node _setcov.js` then ignored.
'use strict';
const fs = require('fs');
const p = require('path').join(__dirname, 'paint.js');
let t = fs.readFileSync(p, 'utf8');
const COV = {
  prophet_tally: 0.68, foresight: 0.64, nirvana: 0.70, prophetic_study: 0.66,
  cycle_of_prophecy: 0.62, pure_love_form: 0.70, delayed_echo: 0.70, delayed_scry: 0.62,
  scry_might: 0.72, scry_agility: 0.60, judgement: 0.56, ember_boon: 0.60,
  granted_turn: 0.60, insight: 0.58, purify: 0.62, exhaust_blast: 0.60,
  free_status: 0.62, double_status: 0.52, status_draw: 0.68, shared_might: 0.54,
  steady_agility: 0.70, starscar_form: 0.54, agate_potion_belt: 0.58, foresight_charm: 0.62,
  prophets_bracelet: 0.56, prophets_eye: 0.52, prophets_eye_plus: 0.58, energy_yetannia: 0.74,
};
let n = 0, miss = [];
for (const [name, cov] of Object.entries(COV)) {
  const re = new RegExp("(add\\('" + name + "',\\s*'[a-z]+',\\s*'[a-zA-Z]+',\\s*)([0-9.]+)(,)");
  if (!re.test(t)) { miss.push(name); continue; }
  t = t.replace(re, '$1' + cov + '$3');
  n++;
}
fs.writeFileSync(p, t);
console.log('patched ' + n + '/' + Object.keys(COV).length + (miss.length ? '  MISSED: ' + miss.join(',') : ''));
