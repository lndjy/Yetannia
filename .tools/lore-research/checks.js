// Targeted checks: bare placeholders, mid-sentence icons, prose-like (no placeholder) cards.
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));
const CHARS = Object.keys(data);
const all = [];
for (const ck of CHARS) for (const c of data[ck].cards) all.push({ ...c, ck });
const out = [];
function L(s) { out.push(s); }

L("=== 裸占位符 {Var}（不含 : 或 |）出现情况 ===");
for (const c of all) {
  const m = [...(c.zhDesc || "").matchAll(/\{[A-Za-z]+[^}:|]*\}/g)];
  if (m.length) L(`${c.ck} | ${c.key} | ${c.zh} | ${m.map((x) => x[0]).join(" ")}`);
}

L("\n=== energyPrefix 出现在句中出现次数 ===");
let n = 0;
for (const c of all) {
  const k = ((c.zhDesc || "").match(/energyPrefix/g) || []).length;
  if (k) { n += k; L(`${c.ck} | ${c.key} | ${c.zh} | ${(c.zhDesc || "").replace(/\n/g, "\\n")}`); }
}
L(`合计 ${n}`);

L("\n=== 不含任何 {占位符} 的卡（读起来最像纯文字描述） ===");
for (const ck of CHARS) {
  const list = data[ck].cards.filter((c) => !/\{/.test(c.zhDesc || "")).map((c) => `${c.zh}(${c.en})`);
  L(`${ck} (${list.length}): ${list.join("、")}`);
}

L("\n=== 描述字数最长/最短的卡 ===");
const byDesc = [...all].sort((a, b) => [...b.zhDesc].length - [...a.zhDesc].length);
L("最长:");
for (const c of byDesc.slice(0, 5)) L(`  ${c.ck} | ${c.zh} | ${[...c.zhDesc].length}字`);
L("最短:");
for (const c of byDesc.slice(-5)) L(`  ${c.ck} | ${c.zh} | ${[...c.zhDesc].length}字 | ${(c.zhDesc || "").replace(/\n/g, "\\n")}`);

L("\n=== 各角色卡名含「打击」的卡 ===");
for (const ck of CHARS) L(`${ck}: ${data[ck].cards.filter((c) => c.zh.includes("打击")).map((c) => c.zh).join("、")}`);

L("\n=== 四字格占比对比 ===");
for (const ck of CHARS) {
  const n2 = data[ck].cards.length;
  const c4 = data[ck].cards.filter((c) => [...c.zh].length === 4).length;
  L(`${ck}\t${c4}/${n2}\t${((c4 / n2) * 100).toFixed(1)}%`);
}

fs.writeFileSync(path.join(OUT, "checks.txt"), out.join("\n"), "utf8");
console.log(out.join("\n"));
