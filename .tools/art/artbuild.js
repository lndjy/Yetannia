// Builds the icon render sheet (HTML) + manifest for the v2 painted icon set.
// 512x512 cells, zero gap, so artcrop.js can slice the Edge screenshot exactly.
// Usage: node artbuild.js
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const OUT = 'C:\\temp\\art';            // ASCII path so file:// URLs stay simple
const COLS = 4;
const CELL = 512;

fs.mkdirSync(OUT, { recursive: true });

const paint = fs.readFileSync(path.join(HERE, 'paint.js'), 'utf8');

// pull the icon list order out of paint.js without a DOM
const names = [];
const re = /add\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*([\d.]+),/g;
let m;
while ((m = re.exec(paint)) !== null) names.push({ name: m[1], group: m[2], cat: m[3], fill: +m[4] });

if (!names.length) throw new Error('no icons parsed out of paint.js');

const rows = Math.ceil(names.length / COLS);
const W = COLS * CELL, H = rows * CELL;

const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>yetannia icons v2</title><style>
html,body{margin:0;padding:0;background:transparent;overflow:hidden;}
#sheet{display:grid;grid-template-columns:repeat(${COLS},${CELL}px);grid-auto-rows:${CELL}px;gap:0;margin:0;padding:0;width:${W}px;}
#sheet canvas{display:block;width:${CELL}px;height:${CELL}px;margin:0;padding:0;border:0;}
</style></head><body>
<div id="sheet"></div>
<script>
${paint}
(function(){
  var sheet=document.getElementById('sheet');
  var icons=window.__ICONS;
  for(var i=0;i<icons.length;i++){
    var cv=document.createElement('canvas');
    cv.width=${CELL}; cv.height=${CELL};
    sheet.appendChild(cv);
    var ctx=cv.getContext('2d');
    window.__DRAW_ICON(ctx, icons[i]);
  }
  document.title='ready-'+icons.length;
})();
</script>
</body></html>`;

fs.writeFileSync(path.join(OUT, 'sheet.html'), html, 'utf8');

const manifest = {
  cell: CELL, cols: COLS, rows, width: W, height: H,
  icons: names.map((n, i) => ({
    index: i, name: n.name, group: n.group, cat: n.cat, fill: n.fill,
    col: i % COLS, row: Math.floor(i / COLS),
    x: (i % COLS) * CELL, y: Math.floor(i / COLS) * CELL, size: CELL,
  })),
};
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
console.log('sheet ' + W + 'x' + H + '  icons=' + manifest.icons.length);
manifest.icons.forEach(x => console.log('  ' + String(x.index).padStart(2) + ' r' + x.row + 'c' + x.col + ' ' + x.group.padEnd(5) + ' ' + x.cat.padEnd(12) + ' ' + x.name));
