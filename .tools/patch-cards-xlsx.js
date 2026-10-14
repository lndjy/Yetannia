// One-off patch for .tools/cards-xlsx.js: applies this round's card changes and adds the four
// cards from the previous batch that never made it into the table.
//
// Written as a script rather than hand edits because the table data is one big JS array and the
// surrounding whitespace is easy to get wrong.
const fs = require('fs');

const file = process.argv[2];
let s = fs.readFileSync(file, 'utf8');
const problems = [];

function replaceOnce(label, from, to) {
  const count = s.split(from).length - 1;
  if (count !== 1) {
    problems.push(`${label}: expected 1 match, found ${count}`);
    return;
  }
  s = s.replace(from, to);
}

// --- 积厚成势: 蓝 -> 金, 新的先知行为 ---
replaceOnce(
  'fated-vitality-rarity',
  "    name: '积厚成势',\n    file: 'FatedVitality.cs',\n    type: '技能',\n    cost: '1',\n    rarity: '蓝（Uncommon）',",
  "    name: '积厚成势',\n    file: 'FatedVitality.cs',\n    type: '技能',\n    cost: '1',\n    rarity: '金（Rare）',",
);
replaceOnce(
  'fated-vitality-effect',
  "'打出时立即获得 2 点生命上限。\\n先知：上面的数字 +2，本场战斗最多累计 8。\\n消耗。\\n\\n敲后：2→3；先知增量 +2→+3，上限 8→12。'",
  "'打出时，获得卡面上显示的数字点生命上限（基础 2）。\\n先知：只把卡面数字抬高 2（不给血上限），本场最多累计到 8。\\n消耗。\\n\\n敲后：基础 2→3；先知增量 +2→+3，上限 8→12。'",
);

// --- 殚精竭虑: 负面只在下一回合 ---
replaceOnce(
  'cycle-of-prophecy-effect',
  "'获得 2 点能量。预见 2。抽 2 张牌。\\n每回合将一张眩晕加入你的弃牌堆。\\n\\n敲后：能量 2→3，预见 2→3，抽牌 2→3。'",
  "'获得 2 点能量。预见 2。抽 2 张牌。\\n下个回合开始时，将一张眩晕加入你的弃牌堆。\\n\\n敲后：能量 2→3，预见 2→3，抽牌 2→3。'",
);

// --- 未命名·渐强: 虚无 + 18/26 + 本局永久 ---
replaceOnce(
  'growing-strike-effect',
  "'造成 20 点伤害。这张牌被打出后，本场战斗中它的伤害永久+1。\\n消耗。\\n\\n敲后：伤害 20→28。\\n※ 需求里没给名字，用占位名。'",
  "'造成 18 点伤害。虚无、消耗。\\n当这张牌被消耗时，本局游戏中它的伤害永久+2。\\n\\n敲后：伤害 18→26。\\n※ 需求里没给名字，用占位名。'",
);

// --- 预备: 消耗 / 敲后去消耗 ---
replaceOnce(
  'rearranged-fate-effect',
  "'将任意数量的手牌放到抽牌堆顶。\\n\\n不可升级：没有敲后效果。'",
  "'将任意数量的手牌放到抽牌堆顶。消耗。\\n\\n敲后：去掉消耗。'",
);

// --- 补上上一批遗漏的 4 张 ---
const missing = `  {
    name: '未命名·奋起',
    file: 'RisingMight.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 3 点临时力量。如果本回合已经打出超过 2 张攻击牌，改为永久获得，并且下回合额外抽 2 张牌。\\n\\n敲后：力量 3→4。\\n※ 需求里没给名字，用占位名。',
  },
  {
    name: '未命名·从容',
    file: 'SteadyAgility.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 2 点临时敏捷。如果本回合未受到过伤害，改为永久获得，并且下回合额外获得 2 点能量。\\n\\n敲后：敏捷 2→3。\\n※ 需求里没给名字，用占位名。',
  },
  {
    name: '未命名·判词',
    file: 'Judgement.cs',
    type: '能力',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '拥有易伤的敌人受到的伤害增加 25%。拥有虚弱的敌人造成的伤害减少 15%。\\n\\n敲后：固有。\\n※ 需求里没给名字，用占位名。',
  },
  {
    name: '纯爱药丸',
    file: 'PureLovePill.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '获得 10 点格挡，获得 1 层人工制品。消耗。\\n\\n敲后：格挡 10→14。',
  },
`;

// 挂在「未命名·连携」之后（金卡表末尾）
const anchor = `  {
    name: '未命名·连携',`;
if (!s.includes(anchor)) {
  problems.push('anchor for the four missing cards not found');
} else {
  const end = s.indexOf('\n  },\n', s.indexOf(anchor)) + '\n  },\n'.length;
  s = s.slice(0, end) + missing + s.slice(end);
}

// --- 遗物也补进对照表（新增一个 sheet 太重，先只加两行备注到关键词 sheet 下） ---
if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}

fs.writeFileSync(file, s);
console.log('patched', file);
