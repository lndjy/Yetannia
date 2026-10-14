const fs=require("fs"), path=require("path");
const dir=process.argv[2];
const pool=fs.readFileSync(process.argv[3],"utf8");
const names=[...new Set([...pool.matchAll(/ModelDb\.Card<([A-Za-z0-9_]+)>/g)].map(m=>m[1]))];
const counts={Attack:0,Skill:0,Power:0,Other:0};
const byRarity={};
for (const n of names) {
  const f=path.join(dir,n+".cs");
  if (!fs.existsSync(f)) continue;
  const t=fs.readFileSync(f,"utf8");
  const m=t.match(/base\(-?\d+,\s*CardType\.(\w+),\s*CardRarity\.(\w+)/);
  if (!m) { counts.Other++; continue; }
  counts[m[1] in counts ? m[1] : "Other"]++;
  byRarity[m[2]] = byRarity[m[2]] || {Attack:0,Skill:0,Power:0,Other:0};
  byRarity[m[2]][m[1] in counts ? m[1] : "Other"]++;
}
const total=Object.values(counts).reduce((a,b)=>a+b,0);
console.log(`${path.basename(process.argv[3])}: ${total} cards`);
console.log("  type:", Object.entries(counts).filter(([k,v])=>v).map(([k,v])=>`${k} ${v} (${(v*100/total).toFixed(0)}%)`).join(", "));
for (const [r,c] of Object.entries(byRarity)) {
  const t=Object.values(c).reduce((a,b)=>a+b,0);
  console.log(`  ${r} (${t}):`, Object.entries(c).filter(([k,v])=>v).map(([k,v])=>`${k} ${v}`).join(", "));
}
