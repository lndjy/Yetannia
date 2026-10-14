// Applies the display names from 卡牌表1.0.xlsx to the existing card files.
//
// Only the two title strings passed to CardLoc are touched — class names, file names and model IDs
// stay as they are, so existing saves keep working. Every replacement must match exactly once;
// the script aborts on a mismatch rather than silently skipping a card.
//
// Usage: node .tools/rename-cards.js [--check]

const fs = require('fs');
const path = require('path');

// file -> [old zh, new zh, old en, new en]
const renames = {
  'ForesightWard.cs': ['预知之壁', '回避', 'Foresight Ward', 'Evade'],
  'OminousDecree.cs': ['厄运宣告', '试探', 'Ominous Decree', 'Probe'],
  'OminousDecreeTranscendent.cs': ['厄运宣告·超越', '合击', 'Ominous Decree, Transcendent', 'Pincer Strike'],
  'DarvsProphecy.cs': ['达弗的预言', '引领之光', "Darv's Prophecy", 'Guiding Light'],
  'GlimpseFate.cs': ['命运一瞥', '挥舞', 'Glimpse Fate', 'Brandish'],
  'Divination.cs': ['占卜', '高举旗帜', 'Divination', 'Raise the Banner'],
  'PropheticCleave.cs': ['先知横扫', '横扫', 'Prophetic Cleave', 'Sweep'],
  'WardOfForesight.cs': ['预见之壁', '后撤', 'Ward of Foresight', 'Fall Back'],
  'JustLucky.cs': ['侥幸', '试探', 'Just Lucky', 'Probe'],
  'CutThroughFate.cs': ['斩断命运', '先制', 'Cut Through Fate', 'Preemptive Strike'],
  'ThirdEye.cs': ['第三只眼', '修顿', 'Third Eye', 'Xiudun'],
  'RearrangedFate.cs': ['重排命运', '预备', 'Rearranged Fate', 'Prepare'],
  'BalancedInsight.cs': ['均衡洞察', '按部就班', 'Balanced Insight', 'Step by Step'],
  'AccumulatedFate.cs': ['宿命累积', '预见打击', 'Accumulated Fate', 'Prophetic Strike'],
  'UnplayedOmen.cs': ['未卜之兆', '引蛇出洞', 'Unplayed Omen', 'Lure Out'],
  'LatentPower.cs': ['潜伏之力', '蓄势待发', 'Latent Power', 'Poised'],
  'PurifyingVision.cs': ['净化视野', '抉择', 'Purifying Vision', 'Choice'],
  'Foresight.cs': ['先见之明', '有条不紊', 'Foresight', 'Methodical'],
  'Nirvana.cs': ['涅槃', '步步为营', 'Nirvana', 'Cautious Advance'],
  'Weave.cs': ['编织', '回马枪', 'Weave', 'Backswing'],
  'TestSkill.cs': ['test（技能）', '运筹帷幄', 'test (Skill)', 'Strategize'],
  'PropheticStudy.cs': ['先知研习', '未雨绸缪', 'Prophetic Study', 'Forewarned'],
  'FatedVitality.cs': ['命定之躯', '积厚成势', 'Fated Vitality', 'Accumulate Might'],
  'CycleOfProphecy.cs': ['先知轮回', '殚精竭虑', 'Cycle of Prophecy', 'Exhaustive Planning'],
  'GrandProphecy.cs': ['大预言', '破釜沉舟', 'Grand Prophecy', 'Burn the Boats'],
  'TestAttack.cs': ['test（攻击）', '请君入瓮', 'test (Attack)', 'Into the Trap'],
};

const dir = path.join(__dirname, '..', 'Yetannia', 'Code', 'Cards');
const checkOnly = process.argv.includes('--check');
const problems = [];
let changed = 0;

for (const [file, [oldZh, newZh, oldEn, newEn]] of Object.entries(renames)) {
  const full = path.join(dir, file);
  if (!fs.existsSync(full)) {
    problems.push(`${file}: missing`);
    continue;
  }

  let text = fs.readFileSync(full, 'utf8');
  let next = text;

  for (const [from, to] of [
    [`"${oldZh}"`, `"${newZh}"`],
    [`"${oldEn}"`, `"${newEn}"`],
  ]) {
    const count = next.split(from).length - 1;
    if (count !== 1) {
      problems.push(`${file}: expected exactly 1 occurrence of ${from}, found ${count}`);
      continue;
    }
    next = next.replace(from, to);
  }

  if (next === text) continue;

  // The replacements only ever substitute same-length-free literal text, so re-read the result to
  // make sure both titles really are the new ones before writing.
  if (!next.includes(`"${newZh}"`) || !next.includes(`"${newEn}"`)) {
    problems.push(`${file}: result does not contain the new names`);
    continue;
  }

  if (!checkOnly) fs.writeFileSync(full, next);
  changed++;
}

for (const p of problems) console.log('PROBLEM ' + p);
console.log(`${checkOnly ? 'would change' : 'changed'} ${changed} file(s), ${problems.length} problem(s)`);
if (problems.length) process.exit(1);
