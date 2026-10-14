// One-off: pulls the base game's own energy orb icons out of ui_atlas so the contact sheet can put
// the mod's energy orb next to them (EnergyIconHelper -> ui_atlas.sprites/card/energy_<colour>.tres).
//   node fetch-energy.js      -> writes C:\temp\artref\ctex\atlas__ui_atlas*.ctex + tres files
'use strict';
const fs = require('fs');
const path = require('path');

const PCK = 'D:\\SteamLibrary\\steamapps\\common\\Slay the Spire 2\\SlayTheSpire2.pck';
const WORK = 'C:\\temp\\artref';
const src = fs.readFileSync(path.join(__dirname, 'fetch-refs.js'), 'utf8');
const readerSrc = src.slice(src.indexOf('const MAGIC'), src.indexOf('const argv ='));
const readIndex = new Function('fs', readerSrc + '\nreturn readIndex;')(fs);

const idx = readIndex(PCK);
const fd = fs.openSync(PCK, 'r');
function readEntry(name) {
  const e = idx.get(name);
  if (!e) return null;
  const buf = Buffer.alloc(e.size);
  fs.readSync(fd, buf, 0, e.size, e.offset);
  return buf;
}
fs.mkdirSync(path.join(WORK, 'ctex'), { recursive: true });
const tresDir = path.join(WORK, 'tres', 'ui_atlas.sprites', 'card');
fs.mkdirSync(tresDir, { recursive: true });

let ctex = 0, tres = 0;
for (const [name] of idx) {
  if (/^\.godot\/imported\/ui_atlas_0\.png-.*\.(bptc|s3tc)\.ctex$/.test(name)) {
    fs.writeFileSync(path.join(WORK, 'ctex', 'atlas__' + path.basename(name)), readEntry(name));
    ctex++;
  }
  if (/^images\/atlases\/ui_atlas\.sprites\/card\/energy_[a-z]+\.tres$/.test(name)) {
    fs.writeFileSync(path.join(tresDir, path.basename(name)), readEntry(name));
    tres++;
  }
}
fs.closeSync(fd);
console.log('ui_atlas ctex: ' + ctex + '  energy .tres: ' + tres);
