// Builds the human-facing contact sheet: every Yetannia v2 icon at 256 px next to the closest
// base-game icon of the same category, plus a base-game reference strip for calibration.
//
// Images are copied into an ASCII working dir first so the file:// URLs used by the Edge
// screenshot never have to carry the non-ASCII workspace path.
//
//   node sheet.js          -> writes C:\temp\art\sheet\sheet.html + sheet-size.json
//   then: .tools/art/sheetshot.ps1
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const IMAGES = path.join(ROOT, '.tools', 'pckproject', 'Yetannia', 'images');
const REF = path.join(HERE, 'ref');
const OUT = 'C:\\temp\\art\\sheet';
const IMG = path.join(OUT, 'img');

fs.mkdirSync(IMG, { recursive: true });

const pairs = JSON.parse(fs.readFileSync(path.join(REF, 'pairs.json'), 'utf8'));
const manifest = JSON.parse(fs.readFileSync('C:\\temp\\art\\manifest.json', 'utf8'));

function copy(src, tag) {
  if (!fs.existsSync(src)) return null;
  const dst = path.join(IMG, tag + '.png');
  fs.copyFileSync(src, dst);
  return 'img/' + tag + '.png';
}

const rows = [];
// the mod's energy orb is a UI element, so its comparison targets are the base game's own energy
// orbs (EnergyIconHelper -> ui_atlas.sprites/card/energy_<colour>.tres), not a power icon.
const ORB_REFS = ['energy_regent', 'energy_ironclad'];
for (const icon of manifest.icons) {
  const isOrb = icon.group === 'orb';
  const isInline = icon.group === 'texticon';
  const mineSrc = isOrb
    ? path.join(IMAGES, 'ui', 'energy_yetannia.png')
    : isInline
      ? path.join(IMAGES, 'ui', 'energy_yetannia_small.png')
      : path.join(IMAGES, icon.group === 'power' ? 'powers_big' : 'relics_big', icon.name + '.png');
  const mine = copy(mineSrc, 'mine_' + icon.name);
  const key = (isOrb ? 'orb' : icon.group) + '/' + icon.name;
  const refIds = isOrb ? ORB_REFS : (pairs[key] || []).slice(0, 2);
  const refs = refIds.map((id, i) => copy(
    isOrb ? path.join(REF, 'ui', id + '.png')
      : path.join(REF, icon.group === 'power' ? 'powers' : 'relics', id + '.png'),
    'ref_' + icon.name + '_' + i)).filter(Boolean);
  rows.push({ name: icon.name, group: icon.group, cat: icon.cat, mine, refs, refIds });
}

// the calibration strip: a plain sample of the base game's own icons
const STRIP_POWERS = ['strength_power', 'dexterity_power', 'barricade_power', 'intangible_power',
  'echo_form_power', 'loop_power', 'doom_power', 'flame_barrier_power',
  'free_power_power', 'duplication_power', 'plating_power', 'star_next_turn_power'];
const STRIP_RELICS = ['belt_buckle', 'arcane_scroll', 'beautiful_bracelet', 'paels_eye', 'glass_eye', 'vajra'];
const STRIP_ENERGY = ['energy_regent', 'energy_ironclad', 'energy_colorless'];
const strip = [];
for (const id of STRIP_POWERS) {
  const p = copy(path.join(REF, 'powers', id + '.png'), 'strip_' + id);
  if (p) strip.push({ src: p, label: id });
}
for (const id of STRIP_RELICS) {
  const p = copy(path.join(REF, 'relics', id + '.png'), 'strip_' + id);
  if (p) strip.push({ src: p, label: id });
}
for (const id of STRIP_ENERGY) {
  const p = copy(path.join(REF, 'ui', id + '.png'), 'strip_' + id);
  if (p) strip.push({ src: p, label: id });
}

const COLS = 4;
const CELL = 256;
const LABEL = 54;
const GUTTER = 26;
const PAD = 28;
const STRIP_CELL = 116;
const gridW = COLS * CELL * 2 + COLS * GUTTER;
const width = gridW + PAD * 2;
const stripRows = Math.ceil(strip.length / 9);
const height = PAD + 118 + (stripRows * (STRIP_CELL + 30) + 58) + 62
  + Math.ceil(rows.length / COLS) * (CELL + LABEL) + PAD;

const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Yetannia icons v2 vs base game</title><style>
  html,body{margin:0;padding:0;background:#12141a;color:#e8ecf2;
    font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;}
  #page{width:${width}px;padding:${PAD}px;box-sizing:border-box;}
  h1{font-size:30px;font-weight:600;margin:0 0 6px 0;letter-spacing:.2px;}
  h2{font-size:19px;font-weight:600;margin:26px 0 4px 0;color:#a9b6c8;}
  .sub{font-size:14px;color:#7f8b9c;margin:0 0 18px 0;line-height:1.5;}
  .strip{display:grid;grid-template-columns:repeat(9,${STRIP_CELL}px);gap:14px;margin-bottom:6px;}
  .strip figure{margin:0;text-align:center;}
  .strip img{width:${STRIP_CELL}px;height:${STRIP_CELL}px;display:block;image-rendering:auto;
    background:#1b1e26;border-radius:8px;}
  .strip figcaption{font-size:10px;color:#7c8798;margin-top:3px;word-break:break-all;line-height:1.2;}
  .grid{display:grid;grid-template-columns:repeat(${COLS},${CELL * 2}px);gap:${GUTTER}px;}
  .cell{display:flex;flex-direction:column;}
  .pair{display:flex;gap:0;}
  .pair .half{width:${CELL}px;}
  .pair img{width:${CELL}px;height:${CELL}px;display:block;background:#1b1e26;}
  .pair .half:first-child img{border-radius:12px 0 0 12px;}
  .pair .half:last-child img{border-radius:0 12px 12px 0;}
  .cap{font-size:12px;line-height:1.3;height:${LABEL}px;padding-top:5px;box-sizing:border-box;}
  .mine{color:#dce6f5;font-weight:600;}
  .theirs{color:#8b97a8;}
  .cat{font-size:10px;color:#5e6a7c;text-transform:uppercase;letter-spacing:.6px;}
  .divider{height:1px;background:#242833;margin:10px 0 0 0;}
  .legend{display:flex;gap:34px;font-size:13px;color:#8b97a8;margin:14px 0 0 0;}
  .legend b{color:#dce6f5;font-weight:600;}
</style></head><body><div id="page">
  <h1>Yetannia icon set v2 &mdash; painted to match the base game</h1>
  <p class="sub">Left of each pair is the new Yetannia icon (256&times;256); right is the closest
  Slay the Spire 2 icon of the same category, extracted from <code>SlayTheSpire2.pck</code>
  (<code>images/powers/*.png</code> and <code>images/relics/*.png</code>, the 256&times;256 authoring
  sources the game's <code>power_atlas</code>/<code>relic_atlas</code> are packed from).</p>

  <h2>Base game reference strip</h2>
  <div class="strip">
    ${strip.map(s => `<figure><img src="${s.src}"><figcaption>${esc(s.label)}</figcaption></figure>`).join('\n    ')}
  </div>
  <div class="divider"></div>

  <h2>Pairwise comparison</h2>
  <div class="legend"><span><b>left</b> = Yetannia v2</span><span><b>right</b> = base game</span>
  <span>cells are 256&times;256, shown 1:1</span></div>
  <div class="grid">
    ${rows.map(r => `<div class="cell"><div class="pair">
      <div class="half"><img src="${r.mine}"></div>
      <div class="half"><img src="${r.refs[0] || ''}"></div>
    </div><div class="cap">
      <div class="mine">${esc(r.name)} <span class="cat">${esc(r.cat)}</span></div>
      <div class="theirs">vs ${esc((r.refIds || []).join(', ') || 'no vanilla sibling')}</div>
    </div></div>`).join('\n    ')}
  </div>
</div></body></html>`;

fs.writeFileSync(path.join(OUT, 'sheet.html'), html, 'utf8');
fs.writeFileSync(path.join(OUT, 'sheet-size.json'), JSON.stringify({ width, height }, null, 2), 'utf8');
console.log('contact sheet html -> ' + path.join(OUT, 'sheet.html'));
console.log('pairs: ' + rows.length + '  strip: ' + strip.length);
console.log('window-size needed: ' + width + ' x ' + height);
