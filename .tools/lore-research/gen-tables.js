// Generate per-character roster tables (sorted by localization key).
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));

const RAR = { Basic: "初始", Common: "普通", Uncommon: "罕见", Rare: "稀有", Ancient: "先古" };
const TYP = { Attack: "攻击", Skill: "技能", Power: "能力" };
const CN = {
  IRONCLAD: "铁甲战士",
  SILENT: "静默猎手",
  DEFECT: "故障机器人",
  NECROBINDER: "亡灵契约师",
  REGENT: "储君",
};

for (const [ck, blob] of Object.entries(data)) {
  const cards = blob.cards;
  const zhLens = cards.map((c) => [...c.zh].length);
  const avg = (a) => (a.reduce((x, y) => x + y, 0) / a.length).toFixed(2);
  const c4 = cards.filter((c) => [...c.zh].length === 4).length;
  const c2 = cards.filter((c) => [...c.zh].length === 2).length;
  const byType = {};
  for (const c of cards) byType[c.type] = (byType[c.type] || 0) + 1;
  const byRar = {};
  for (const c of cards) byRar[c.rarity] = (byRar[c.rarity] || 0) + 1;

  const L = [];
  L.push(`**统计**：共 ${cards.length} 张 ｜ 卡名平均 ${avg(zhLens)} 个汉字（2 字 ${c2} / 4 字 ${c4}，四字格占 ${((c4 / cards.length) * 100).toFixed(1)}%）`);
  L.push(`｜ 类型：${["Attack", "Skill", "Power"].filter((t) => byType[t]).map((t) => `${TYP[t]} ${byType[t]}`).join(" / ")}`);
  L.push(`｜ 稀有度：${["Basic", "Common", "Uncommon", "Rare", "Ancient"].filter((r) => byRar[r]).map((r) => `${RAR[r]} ${byRar[r]}`).join(" / ")}`);
  L.push("");
  L.push(`| key | 中文名（English Name） | 稀有度 | 类型 | 费 |`);
  L.push(`| --- | --- | --- | --- | --- |`);
  for (const c of cards) {
    L.push(`| \`${c.key}\` | ${c.zh}（${c.en}） | ${RAR[c.rarity] || c.rarity} | ${TYP[c.type] || c.type} | ${c.cost == null ? "?" : c.cost} |`);
  }
  fs.writeFileSync(path.join(OUT, `_t-${ck}.md`), L.join("\n") + "\n", "utf8");
  console.log(`${ck}: wrote ${cards.length} rows`);
}
