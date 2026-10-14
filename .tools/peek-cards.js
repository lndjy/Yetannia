// One-off: show the type/rarity lines of selected cards in cards-xlsx.js so edits can be verified.
const fs = require('fs');
const s = fs.readFileSync(process.argv[2], 'utf8');

for (const n of ['奇袭', '殚精竭虑', '厚积薄发', '积厚成势', '未命名·渐强', '预备']) {
  const i = s.indexOf("name: '" + n + "'");
  if (i < 0) { console.log(n, '=> NOT FOUND'); continue; }
  const seg = s.slice(i, i + 200).split('\n').slice(0, 5).map((x) => x.trim()).join(' | ');
  console.log(n, '=>', seg);
}

console.log('--- 是否已有第 15 批的 4 张 ---');
for (const n of ['未命名·奋起', '未命名·从容', '未命名·判词', '纯爱药丸']) {
  console.log(n, '=>', s.includes("name: '" + n + "'"));
}
