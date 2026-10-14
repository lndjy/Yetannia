const fs = require('fs');
const path = require('path');
const out = process.argv[2];

// ---- 1. card table, lifted verbatim from .tools/cards-xlsx.js -----------------
const src = fs.readFileSync(path.join(__dirname, 'cards-xlsx.js'), 'utf8');
const start = src.indexOf('const cards = [');
const end = src.indexOf('\n];', start);
if (start < 0 || end < 0) throw new Error('card array not found');
const cards = eval(src.slice(start + 'const cards = '.length, end + 2));

// ---- 2. sample art, inlined as data URLs so canvas export is never tainted ---
function dataUrl(p) {
  const b = fs.readFileSync(p);
  return 'data:image/png;base64,' + b.toString('base64');
}
const samples = {
  cardNormal: dataUrl('.tools/pckproject/Yetannia/images/card_portraits/test.png'),
  cardRare:   dataUrl('.tools/pckproject/Yetannia/images/card_portraits/test2.png'),
  icon:       dataUrl('.tools/crops/icon_a.png'),
  select:     dataUrl('.tools/crops/select_a.png'),
  blank:      dataUrl('.tools/pckproject/Yetannia/images/card_portraits/blank.png'),
};

fs.writeFileSync(path.join(out, 'cards.js'),
  'window.YETANNIA_CARDS = ' + JSON.stringify(cards, null, 0) + ';\n', 'utf8');
fs.writeFileSync(path.join(out, 'samples.js'),
  'window.YETANNIA_SAMPLES = ' + JSON.stringify(samples) + ';\n', 'utf8');

console.log('cards  :', cards.length);
console.log('samples:', Object.keys(samples).map(k => k + '=' + Math.round(samples[k].length / 1024) + 'KB').join(' '));
