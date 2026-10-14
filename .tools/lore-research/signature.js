// Refined: signature morphemes (2-gram appearing in >=2 cards of exactly one character),
// suffixes, four-char titles, and corpus-wide verb/noun counts.
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));
const CHARS = Object.keys(data);
const out = [];
function L(s) { out.push(s); }

// card -> character maps
const cardOwner = new Map();
for (const ck of CHARS) for (const c of data[ck].cards) cardOwner.set(c.key, ck);

// for each 2-gram, count cards per character (titles only)
const gram = new Map(); // gram -> Map(char -> count)
for (const ck of CHARS) {
  for (const c of data[ck].cards) {
    const t = [...c.zh];
    const seen = new Set();
    for (let i = 0; i + 2 <= t.length; i++) seen.add(t.slice(i, i + 2).join(""));
    for (const g of seen) {
      if (!gram.has(g)) gram.set(g, new Map());
      const m = gram.get(g);
      m.set(ck, (m.get(ck) || 0) + 1);
    }
  }
}

L("=== A. 签名词素：某角色≥2张卡的标题中出现，其他角色0张 ===");
for (const ck of CHARS) {
  const sig = [...gram.entries()]
    .filter(([, m]) => (m.get(ck) || 0) >= 2 && m.size === 1)
    .sort((a, b) => b[1].get(ck) - a[1].get(ck))
    .map(([g, m]) => `${g}×${m.get(ck)}`);
  L(`\n[${ck}] (${sig.length}) ${sig.join(" ")}`);
}

L("\n\n=== B. 标题末二字分布（Top 12） ===");
for (const ck of CHARS) {
  const m = new Map();
  for (const c of data[ck].cards) {
    const t = [...c.zh];
    if (t.length < 2) continue;
    const s = t.slice(-2).join("");
    m.set(s, (m.get(s) || 0) + 1);
  }
  L(`${ck}: ${[...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => `${k}×${v}`).join(" ")}`);
}

L("\n=== C. 各角色四字卡名清单 ===");
for (const ck of CHARS) {
  const four = data[ck].cards.filter((c) => [...c.zh].length === 4).map((c) => c.zh);
  L(`${ck} (${four.length}): ${four.join("、")}`);
}

L("\n=== D. 各角色二字卡名清单 ===");
for (const ck of CHARS) {
  const two = data[ck].cards.filter((c) => [...c.zh].length === 2).map((c) => c.zh);
  L(`${ck} (${two.length}): ${two.join("、")}`);
}

L("\n=== E. 全库常用动词（描述文本，按总出现次数） ===");
const VERBS = ["造成", "获得", "给予", "失去", "抽", "丢弃", "消耗", "打出", "添加", "变化", "升级", "击杀", "斩杀", "回复", "增加", "翻倍", "触发", "花费", "移除", "洗牌", "选择", "生成", "召唤", "铸造", "激发", "随机", "立即", "额外", "本回合", "在你的回合", "每当", "如果"];
const allTxt = CHARS.map((ck) => data[ck].cards.map((c) => c.zhDesc).join(" ")).join(" ");
for (const w of VERBS) L(`${w}\t${allTxt.split(w).length - 1}`);

L("\n=== F. 全库常用名词（描述文本） ===");
const NOUNS = ["格挡", "力量", "易伤", "虚弱", "敏捷", "集中", "中毒", "小刀", "充能球", "手牌", "抽牌堆", "弃牌堆", "消耗牌堆", "生命", "最大生命值", "能量", "敌人", "所有敌人", "随机敌人", "状态牌", "攻击牌", "技能牌", "能力牌", "无色牌", "灵魂", "虚无", "灾厄", "奥斯提", "铸造", "君王之剑", "星", "金币", "回合", "层", "点", "张"];
for (const w of NOUNS) L(`${w}\t${allTxt.split(w).length - 1}`);

L("\n=== G. 引号/特殊标点在描述中的用法 ===");
const quotes = [];
for (const ck of CHARS) for (const c of data[ck].cards) {
  if (/[“”]/.test(c.zhDesc || "") || /[“”]/.test(c.zh)) quotes.push(`${ck} | ${c.key} | ${c.zh} | ${c.zhDesc}`);
}
L(quotes.join("\n"));

L("\n=== H. 特殊标点：叹号/问号/省略号在描述中的用法 ===");
const punct = [];
for (const ck of CHARS) for (const c of data[ck].cards) {
  if (/[！？…]/.test(c.zhDesc || "")) punct.push(`${ck} | ${c.key} | ${c.zhDesc}`);
}
L(punct.join("\n") || "（无）");

fs.writeFileSync(path.join(OUT, "signature.txt"), out.join("\n"), "utf8");
console.log(out.join("\n"));
