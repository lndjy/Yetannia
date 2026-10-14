// Builds the human review contact sheet: all 27 icons, 256x256 cells, dark bg, name under each.
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const OUTDIR = 'C:\\temp\\icogen';
const COLS = 6, CELL = 256, GAP = 26, PAD = 34, CAP = 30;

const glyphs = fs.readFileSync(path.join(HERE, 'glyphs.js'), 'utf8');
const man = JSON.parse(fs.readFileSync(path.join(OUTDIR, 'manifest.json'), 'utf8'));
const rows = Math.ceil(man.icons.length / COLS);
const W = PAD * 2 + COLS * CELL + (COLS - 1) * GAP;
const H = PAD * 2 + rows * (CELL + CAP) + (rows - 1) * GAP + 44;

const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>yetannia icon review</title><style>
html,body{margin:0;padding:0;background:#14161c;}
#wrap{width:${W}px;height:${H}px;box-sizing:border-box;padding:${PAD}px;background:#14161c;font-family:"Segoe UI",Arial,sans-serif;}
h1{margin:0 0 18px 0;font-size:22px;font-weight:600;color:#e6ebf5;letter-spacing:.4px;}
h1 span{color:#8b93a7;font-weight:400;font-size:15px;margin-left:10px;}
#grid{display:grid;grid-template-columns:repeat(${COLS},${CELL}px);gap:${GAP}px;}
.cell{width:${CELL}px;}
.cell canvas{display:block;width:${CELL}px;height:${CELL}px;}
.cap{height:${CAP}px;line-height:${CAP}px;text-align:center;color:#c3cbdb;font-size:17px;}
.cap b{color:#ffffff;font-weight:600;}
.cap i{color:#7f889b;font-style:normal;font-size:13px;margin-left:6px;}
</style></head><body>
<div id="wrap">
<h1>Yetannia icon set <span>27 icons &middot; 256&times;256 &middot; powers violet / crimson / emerald / steel / slate / gold, relics bronze</span></h1>
<div id="grid"></div>
</div>
<script>
${glyphs}
(function(){
  var grid=document.getElementById('grid'), icons=window.ICONS, colors=window.__COLORS, oc=window.__OUTLINE_CATS;
  for(var i=0;i<icons.length;i++){
    var cell=document.createElement('div'); cell.className='cell';
    var cv=document.createElement('canvas'); cv.width=256; cv.height=256;
    cell.appendChild(cv);
    var cap=document.createElement('div'); cap.className='cap';
    cap.innerHTML='<b>'+icons[i].name+'</b><i>'+icons[i].group+' &middot; '+icons[i].cat+'</i>';
    cell.appendChild(cap);
    grid.appendChild(cell);
    var ctx=cv.getContext('2d');
    window.__DRAW_ICON(ctx,icons[i],colors,oc);
  }
  document.title='ready';
})();
</script>
</body></html>`;

fs.writeFileSync(path.join(OUTDIR, 'contact.html'), html, 'utf8');
console.log('contact sheet', W + 'x' + H);
