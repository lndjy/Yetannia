// Builds the 256x256 icon sheet HTML + a manifest describing cell -> file mapping.
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const OUTDIR = 'C:\\temp\\icogen';           // ASCII path so file:// URLs stay simple
const COLS = 6;
const CELL = 256;

fs.mkdirSync(OUTDIR, { recursive: true });

const glyphs = fs.readFileSync(path.join(HERE, 'glyphs.js'), 'utf8');

const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>yetannia icons</title><style>
html,body{margin:0;padding:0;background:transparent;overflow:hidden;}
#sheet{display:grid;grid-template-columns:repeat(${COLS},${CELL}px);grid-auto-rows:${CELL}px;gap:0;margin:0;padding:0;width:${COLS * CELL}px;}
#sheet canvas{display:block;width:${CELL}px;height:${CELL}px;margin:0;padding:0;border:0;}
</style></head><body>
<div id="sheet"></div>
<script>
${glyphs}
(function(){
  var sheet=document.getElementById('sheet');
  var icons=window.ICONS, colors=window.__COLORS, oc=window.__OUTLINE_CATS;
  var dpr=1;
  for(var i=0;i<icons.length;i++){
    var cv=document.createElement('canvas');
    cv.width=256*dpr; cv.height=256*dpr;
    cv.setAttribute('data-name',icons[i].name);
    sheet.appendChild(cv);
    var ctx=cv.getContext('2d');
    ctx.save();
    ctx.scale(dpr,dpr);
    window.__DRAW_ICON(ctx,icons[i],colors,oc);
    ctx.restore();
  }
  document.title='ready-'+icons.length;
})();
</script>
</body></html>`;

fs.writeFileSync(path.join(OUTDIR, 'sheet256.html'), html, 'utf8');

// manifest: replicate the ICONS order without a DOM
const names = [];
const re = /add\('([^']+)',\s*'([^']+)',\s*'([^']+)'/g;
let m;
while ((m = re.exec(glyphs)) !== null) names.push({ name: m[1], group: m[2], cat: m[3] });

const rows = Math.ceil(names.length / COLS);
const manifest = names.map((n, i) => ({
  index: i, name: n.name, group: n.group, cat: n.cat,
  col: i % COLS, row: Math.floor(i / COLS),
  x: (i % COLS) * CELL, y: Math.floor(i / COLS) * CELL, size: CELL,
}));

fs.writeFileSync(path.join(OUTDIR, 'manifest.json'), JSON.stringify({
  cell: CELL, cols: COLS, rows, width: COLS * CELL, height: rows * CELL, icons: manifest,
}, null, 2), 'utf8');

console.log('sheet:', COLS * CELL + 'x' + rows * CELL, 'icons:', manifest.length);
manifest.forEach(x => console.log('  ' + x.index + ' r' + x.row + 'c' + x.col + ' ' + x.group + '/' + x.name));
