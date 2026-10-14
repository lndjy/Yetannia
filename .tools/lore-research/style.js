// Style metrics: lexicon frequency, exclusivity, sentence stats.
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));
const out = [];
function L(s) { out.push(s); }

const LEX = [
  // mechanics keywords / imagery roots
  "力量", "格挡", "易伤", "虚弱", "敏捷", "集中", "中毒", "小刀", "充能球", "生成", "激发", "冰霜", "闪电", "黑暗", "等离子", "玻璃",
  "召唤", "奥斯提", "灵魂", "灾厄", "虚无", "消耗", "抽牌堆", "弃牌堆", "手牌", "铸造", "君王之剑", "星", "星辰", "敌人", "所有敌人",
  "生命", "最大生命值", "回合", "攻击牌", "技能牌", "能力牌", "状态牌", "随机", "选择", "盟友", "玩家",
  // verbs
  "造成", "获得", "给予", "失去", "抽", "丢弃", "消耗", "打出", "添加", "变化", "升级", "击杀", "斩杀", "回复", "增加", "翻倍", "触发", "花费",
];
const IMAGERY = {
  IRONCLAD: ["血", "火", "焰", "燃烧", "力量", "格挡", "易伤", "消耗", "痛", "怒", "恶魔", "伤", "战"],
  SILENT: ["毒", "中毒", "小刀", "刀", "弃", "抽", "虚弱", "影", "暗", "刺", "敏捷", "虚"],
  DEFECT: ["充能球", "生成", "激发", "集中", "闪电", "冰霜", "黑暗", "等离子", "玻璃", "状态牌", "能量", "数据", "核心"],
  NECROBINDER: ["奥斯提", "灵魂", "灾厄", "召唤", "死", "亡", "虚", "骨", "坟", "墓", "灵", "魂", "幽冥"],
  REGENT: ["铸造", "君王之剑", "星", "无色牌", "虚弱", "易伤", "力量", "王", "光", "剑"],
};

L("=== 1. 每个角色的意象词根命中次数（标题+描述，按出现次数计） ===");
for (const [ck, blob] of Object.entries(data)) {
  const txt = blob.cards.map((c) => c.zh + " " + c.zhDesc).join(" ");
  const hits = IMAGERY[ck].map((w) => {
    const n = txt.split(w).length - 1;
    return `${w}:${n}`;
  });
  L(`${ck}: ${hits.join("  ")}`);
}

L("\n=== 2. 机制关键词出现次数（全角色） ===");
const lexRows = [];
for (const [ck, blob] of Object.entries(data)) {
  const txt = blob.cards.map((c) => c.zh + " " + c.zhDesc).join(" ");
  const row = { ck };
  for (const w of LEX) row[w] = txt.split(w).length - 1;
  lexRows.push(row);
}
L("词\t" + Object.keys(lexRows[0]).filter((k) => k !== "ck").join("\t"));
for (const r of lexRows) L(Object.keys(r).map((k) => r[k]).join("\t"));

L("\n=== 3. 标题用词专属性（2字词，仅出现在一个角色的标题中） ===");
const titleTokens = {};
for (const [ck, blob] of Object.entries(data)) {
  for (const c of blob.cards) {
    const t = [...c.zh];
    for (let i = 0; i + 2 <= t.length; i++) {
      const g = t.slice(i, i + 2).join("");
      if (!titleTokens[g]) titleTokens[g] = new Set();
      titleTokens[g].add(ck);
    }
  }
}
for (const [ck] of Object.entries(data)) {
  const only = Object.entries(titleTokens).filter(([, s]) => s.size === 1 && s.has(ck)).map(([g]) => g);
  L(`${ck} 专属标题2字片段(${only.length}): ${only.join(" ")}`);
}

L("\n=== 4. 描述句数与句长 ===");
for (const [ck, blob] of Object.entries(data)) {
  let sents = 0, chars = 0, multi = 0, you = 0, ally = 0, ex = 0, quote = 0;
  for (const c of blob.cards) {
    const d = c.zhDesc || "";
    const parts = d.split("。").filter((x) => x.trim());
    sents += parts.length;
    chars += [...d].length;
    if (parts.length >= 2) multi++;
    if (/你/.test(d)) you++;
    if (/另一名玩家|盟友|所有玩家|其他玩家/.test(d)) ally++;
    if (/！|!/.test(c.zh)) ex++;
    if (/[“”]/.test(d) || /[“”]/.test(c.zh)) quote++;
  }
  L(`${ck}: 卡数=${blob.cards.length} 总句数=${sents} 平均每卡句数=${(sents / blob.cards.length).toFixed(2)} 平均每句字数=${(chars / sents).toFixed(1)} 多句卡占比=${((multi / blob.cards.length) * 100).toFixed(0)}% 含"你"的卡=${you} 含多人用词=${ally} 标题含感叹号=${ex} 含引号=${quote}`);
}

L("\n=== 5. 标题含感叹号/引号的卡 ===");
for (const [ck, blob] of Object.entries(data)) {
  const hits = blob.cards.filter((c) => /[！!]/.test(c.zh) || /[“”]/.test(c.zh)).map((c) => `${c.zh}(${c.en})`);
  L(`${ck}: ${hits.join(" | ") || "（无）"}`);
}

L("\n=== 6. 描述首词分布（前2字） ===");
for (const [ck, blob] of Object.entries(data)) {
  const m = {};
  for (const c of blob.cards) {
    const first = [...(c.zhDesc || "")].slice(0, 2).join("");
    m[first] = (m[first] || 0) + 1;
  }
  const top = Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => `${k}(${v})`);
  L(`${ck}: ${top.join(" ")}`);
}

L("\n=== 7. 英文名含专有名词（大写专名/所有人称） ===");
for (const [ck, blob] of Object.entries(data)) {
  const hits = blob.cards.filter((c) => /'s\b|'/.test(c.en)).map((c) => `${c.zh}(${c.en})`);
  L(`${ck} 含撇号所有格: ${hits.join(" | ") || "（无）"}`);
}

L("\n=== 8. 中文名与英文名的字数关系 ===");
for (const [ck, blob] of Object.entries(data)) {
  const zl = blob.cards.map((c) => [...c.zh].length);
  const el = blob.cards.map((c) => c.en.split(" ").length);
  const avg = (a) => (a.reduce((x, y) => x + y, 0) / a.length).toFixed(2);
  L(`${ck}: 中文平均${avg(zl)}字, 英文平均${avg(el)}词, 中文字数范围 ${Math.min(...zl)}-${Math.max(...zl)}`);
}

L("\n=== 9. 全库最长的中文卡名 ===");
const all = [];
for (const [ck, blob] of Object.entries(data)) for (const c of blob.cards) all.push([...c.zh].length + "|" + ck + "|" + c.zh + "|" + c.en);
all.sort((a, b) => parseInt(b) - parseInt(a));
L(all.slice(0, 12).join("\n"));

fs.writeFileSync(path.join(OUT, "style-metrics.txt"), out.join("\n"), "utf8");
console.log(out.join("\n"));
