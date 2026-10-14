// Translation-convention metrics + punctuation anomalies (evidence for the 用字习惯 section).
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));
const CHARS = Object.keys(data);
const out = [];
function L(s) { out.push(s); }

const all = [];
for (const ck of CHARS) for (const c of data[ck].cards) all.push({ ...c, ck });

const count = (re) => all.filter((c) => re.test(c.zhDesc || "")).length;
L("=== 用字变体统计（454 张卡，命中卡数） ===");
for (const [name, re] of [
  ["这张牌", /这张牌/], ["此牌", /此牌/], ["该牌", /该牌/],
  ["敌人", /敌人/], ["敌方", /敌方/], ["所有敌人", /所有敌人/], ["随机敌人", /随机敌人/], ["一名敌人", /一名敌人/],
  ["你", /你/], ["自身", /自身/], ["自己", /自己/],
  ["另一名玩家", /另一名玩家/], ["另一位玩家", /另一位玩家/], ["其他玩家", /其他玩家/], ["所有玩家", /所有玩家/], ["盟友", /盟友/],
  ["在本回合", /在本回合/], ["在这个回合", /在这个回合/], ["本回合中", /本回合中/],
  ["获得", /获得/], ["得到", /得到/],
  ["变化为", /变化为/], ["变为", /变为/],
  ["[gold]标签", /\[gold\]/],
  ["{...diff()}动态值", /\{[\w:()|]*(diff|energyIcons|starIcons|percentLess|percentMore)[\w:()|]*\}/],
  ["{IfUpgraded}", /\{IfUpgraded/],
  ["{InCombat}", /\{InCombat/],
  ["花括号在句首(占位符开头)", /^\{/],
  ["[gold]在句首", /^\[gold\]/],
]) L(`${name}\t${count(re)}`);

L("\n=== 标点异常 / 疑点（这些卡值得 Mod 作者注意） ===");
const anomalies = all.filter((c) => {
  const d = c.zhDesc || "";
  return /[,;:!?]/.test(d) || /[，。；：][^\n]*\s+[点张层]/.test(d) || (d.length > 0 && !/[。！）|}]$/.test(d)) || / {2,}/.test(d) || /[^\n]点[gold]/.test(d);
});
for (const c of anomalies) {
  const d = (c.zhDesc || "").replace(/\n/g, "\\n");
  L(`${c.ck} | ${c.key} | ${c.zh} | ${d}`);
}

L("\n=== 卡名中出现的汉字总数 / 去重字数 ===");
const s = new Set();
for (const c of all) for (const ch of c.zh) s.add(ch);
L(`不同汉字数：${s.size}`);
L(`全部汉字：${[...s].join("")}`);

fs.writeFileSync(path.join(OUT, "conventions.txt"), out.join("\n"), "utf8");
console.log(out.join("\n"));
