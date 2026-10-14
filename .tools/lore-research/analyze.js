// Analysis pass: build readable per-character listings + statistics.
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));

const RAR = { Basic: "初始", Common: "普通", Uncommon: "罕见", Rare: "稀有", Ancient: "先古", Status: "状态", Curse: "诅咒", Token: "衍生", Quest: "任务", Event: "事件" };
const TYP = { Attack: "攻击", Skill: "技能", Power: "能力", Status: "状态", Curse: "诅咒" };

const lines = [];
function L(s) { lines.push(s); }

const summary = [];
for (const [ck, blob] of Object.entries(data)) {
  const cards = blob.cards;
  const txt = [];
  txt.push(`\n########## ${ck} (${cards.length} cards) ##########`);
  for (const c of cards) {
    txt.push(`${c.key}\t${c.zh}\t${c.en}\t${RAR[c.rarity] || c.rarity}\t${TYP[c.type] || c.type}\t${c.cost == null ? "?" : c.cost}\t${c.zhDesc}`);
  }
  fs.writeFileSync(path.join(OUT, `list-${ck}.txt`), txt.join("\n"), "utf8");

  // stats
  const zhLens = cards.map((c) => [...c.zh].length);
  const avg = (a) => (a.reduce((x, y) => x + y, 0) / a.length).toFixed(2);
  const c4 = cards.filter((c) => [...c.zh].length === 4).length;
  const c2 = cards.filter((c) => [...c.zh].length === 2).length;
  const c3 = cards.filter((c) => [...c.zh].length === 3).length;
  const c5 = cards.filter((c) => [...c.zh].length === 5).length;
  const c6p = cards.filter((c) => [...c.zh].length >= 6).length;
  const descLens = cards.map((c) => [...(c.zhDesc || "")].length);
  const byType = {}, byRar = {};
  for (const c of cards) {
    byType[c.type] = (byType[c.type] || 0) + 1;
    byRar[c.rarity] = (byRar[c.rarity] || 0) + 1;
  }
  const withParen = cards.filter((c) => /[（(]/.test(c.zh)).length;
  const latinInZh = cards.filter((c) => /[A-Za-z]/.test(c.zh)).length;
  summary.push([
    ck,
    `n=${cards.length}`,
    `avgTitle=${avg(zhLens)}`,
    `2字=${c2} 3字=${c3} 4字=${c4}(${((c4 / cards.length) * 100).toFixed(0)}%) 5字=${c5} 6+字=${c6p}`,
    `avgDesc=${avg(descLens)}`,
    `types=${JSON.stringify(byType)}`,
    `rarity=${JSON.stringify(byRar)}`,
    `zh含标点括号=${withParen}`,
    `zh含拉丁字母=${latinInZh}`,
  ].join(" | "));
  L(`${ck}: n=${cards.length} avgTitleLen=${avg(zhLens)} 4char=${c4} (${((c4 / cards.length) * 100).toFixed(1)}%) avgDescLen=${avg(descLens)}`);
}

fs.writeFileSync(path.join(OUT, "list-ALL.txt"), lines.join("\n"), "utf8");
fs.writeFileSync(path.join(OUT, "stats.txt"), summary.join("\n"), "utf8");

// corpus-wide de-duplication check: which zh titles appear in >1 character pool
const owner = new Map();
for (const [ck, blob] of Object.entries(data)) for (const c of blob.cards) {
  if (!owner.has(c.zh)) owner.set(c.zh, []);
  owner.get(c.zh).push(ck);
}
const shared = [...owner.entries()].filter(([, v]) => v.length > 1);
const sharedTxt = shared.map(([k, v]) => `${k} <- ${v.join(",")}`);
fs.writeFileSync(path.join(OUT, "shared-titles.txt"), sharedTxt.join("\n"), "utf8");
console.log(summary.join("\n"));
console.log("\nSHARED TITLES ACROSS CHARACTERS: " + shared.length);
console.log(sharedTxt.join("\n"));
