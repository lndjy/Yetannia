// Builds Yetannia-卡牌表.xlsx — the "as implemented" card table.
//
// No spreadsheet library is available in this environment, so this writes the OOXML package by
// hand: an .xlsx is just a ZIP holding a handful of XML parts, and every part here is written as
// "stored" (no compression) so a plain CRC32 + local/central headers is enough. Node's zlib is
// deliberately not used, which keeps the writer trivial.
//
// Sheet 1 (卡牌总表) mirrors what the code currently ships, so it can be diffed against the design
// table (卡牌表1.0.xlsx). Sheet 2 maps each card to its source file and lists the keyword glossary.
//
// The data below is hand-maintained: card text in the source lives in Localization templates full
// of {Placeholder:diff()} tokens, which is unreadable in a spreadsheet, so the table stores the
// rendered wording instead. Re-run this after changing cards.
//
// Usage: node .tools/cards-xlsx.js [outputPath]

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------- ZIP writer

const DOS_TIME = 0;
const DOS_DATE = 23073; // 2025-01-01

function crc32(buf) {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zip(files) {
  const parts = [];
  const central = [];
  let offset = 0;

  for (const file of files) {
    const nameBuf = Buffer.from(file.name, 'utf8');
    const data = Buffer.isBuffer(file.data) ? file.data : Buffer.from(file.data, 'utf8');
    const crc = crc32(data);

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4); // version needed
    local.writeUInt16LE(0x0800, 6); // UTF-8 names
    local.writeUInt16LE(0, 8); // stored
    local.writeUInt16LE(DOS_TIME, 10);
    local.writeUInt16LE(DOS_DATE, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);

    parts.push(local, nameBuf, data);

    const cd = Buffer.alloc(46);
    cd.writeUInt32LE(0x02014b50, 0);
    cd.writeUInt16LE(20, 4); // version made by
    cd.writeUInt16LE(20, 6); // version needed
    cd.writeUInt16LE(0x0800, 8);
    cd.writeUInt16LE(0, 10);
    cd.writeUInt16LE(DOS_TIME, 12);
    cd.writeUInt16LE(DOS_DATE, 14);
    cd.writeUInt32LE(crc, 16);
    cd.writeUInt32LE(data.length, 20);
    cd.writeUInt32LE(data.length, 24);
    cd.writeUInt16LE(nameBuf.length, 28);
    cd.writeUInt16LE(0, 30); // extra
    cd.writeUInt16LE(0, 32); // comment
    cd.writeUInt16LE(0, 34); // disk
    cd.writeUInt16LE(0, 36); // internal attrs
    cd.writeUInt32LE(0, 38); // external attrs
    cd.writeUInt32LE(offset, 42);
    central.push(cd, nameBuf);

    offset += local.length + nameBuf.length + data.length;
  }

  const centralBuf = Buffer.concat(central);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(files.length, 8);
  eocd.writeUInt16LE(files.length, 10);
  eocd.writeUInt32LE(centralBuf.length, 12);
  eocd.writeUInt32LE(offset, 16);
  eocd.writeUInt16LE(0, 20);

  return Buffer.concat([...parts, centralBuf, eocd]);
}

// ------------------------------------------------------------- XML helpers

function esc(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
    .replace(/\r?\n/g, '&#10;'); // real line break inside a cell
}

function colName(index) {
  let n = index + 1;
  let name = '';
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

// styleId 0 = default, 1 = bold header, 2 = wrapped + top aligned
function sheetXml(sheet) {
  const cols = sheet.widths
    .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
    .join('');

  const rows = sheet.rows
    .map((cells, r) => {
      const style = r === 0 ? 1 : 2;
      const inner = cells
        .map((value, c) => {
          const ref = `${colName(c)}${r + 1}`;
          if (value === null || value === undefined || value === '') {
            return `<c r="${ref}" s="${style}"/>`;
          }
          return `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${esc(value)}</t></is></c>`;
        })
        .join('');
      return `<row r="${r + 1}">${inner}</row>`;
    })
    .join('');

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols>${cols}</cols><sheetData>${rows}</sheetData></worksheet>`;
}

function buildXlsx(sheets) {
  const contentTypes = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>${sheets
    .map(
      (_, i) =>
        `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`,
    )
    .join('')}<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`;

  const rootRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`;

  const workbook = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${sheets
    .map((s, i) => `<sheet name="${esc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`)
    .join('')}</sheets></workbook>`;

  const workbookRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${sheets
    .map(
      (_, i) =>
        `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`,
    )
    .join('')}<Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`;

  const styles = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;

  const files = [
    { name: '[Content_Types].xml', data: contentTypes },
    { name: '_rels/.rels', data: rootRels },
    { name: 'xl/workbook.xml', data: workbook },
    { name: 'xl/_rels/workbook.xml.rels', data: workbookRels },
    { name: 'xl/styles.xml', data: styles },
  ];
  sheets.forEach((s, i) => files.push({ name: `xl/worksheets/sheet${i + 1}.xml`, data: sheetXml(s) }));

  return zip(files);
}

// ------------------------------------------------------------------- data

const cards = [
  // ---- 基础（Basic）------------------------------------------------------
  {
    name: '打击',
    file: 'YetanniaStrike.cs',
    type: '攻击',
    cost: '1',
    rarity: '基础（Basic）',
    effect: '造成 6 点伤害。\n\n敲后：伤害 6→9。',
  },
  {
    name: '防御',
    file: 'YetanniaDefend.cs',
    type: '技能',
    cost: '1',
    rarity: '基础（Basic）',
    effect: '获得 5 点格挡。\n\n敲后：格挡 5→8。',
  },
  {
    name: '回避',
    file: 'ForesightWard.cs',
    type: '技能',
    cost: '0',
    rarity: '基础（Basic）',
    effect: '获得 3 点格挡。\n先知：获得 4 点格挡。\n\n敲后：格挡 3→4；先知格挡 4→6。',
  },
  {
    name: '试探',
    file: 'OminousDecree.cs',
    type: '攻击',
    cost: '1',
    rarity: '基础（Basic）',
    effect:
      '对所有敌人造成 6 点伤害，并给予所有敌人 1 层易伤和 1 层虚弱。\n先知：没有额外描述，效果与打出相同。\n\n敲后：费用 1→0；伤害与层数不变。',
  },

  // ---- 先古（Ancient）----------------------------------------------------
  {
    name: '合击',
    file: 'OminousDecreeTranscendent.cs',
    type: '攻击',
    cost: '1',
    rarity: '先古（Ancient）',
    effect:
      '给予所有敌人 2 层易伤和 2 层虚弱，并造成 15 点伤害。\n先知：效果与打出相同。\n\n敲后：费用 1→0，伤害 15→20。\n（走「古老之牙」路线时替换初始卡「试探」）',
  },
  {
    name: '引领之光',
    file: 'DarvsProphecy.cs',
    type: '技能',
    cost: '3',
    rarity: '先古（Ancient）',
    effect: '固有。预见你的抽牌堆。消耗。\n\n敲后：费用 3→2。\n（来自达弗的「陈旧的书卷」）',
  },

  // ---- 白（Common）------------------------------------------------------
  {
    name: '挥舞',
    file: 'GlimpseFate.cs',
    type: '技能',
    cost: '0',
    rarity: '白（Common）',
    effect: '预见 1。抽 1 张牌。\n\n敲后：预见 1→2。',
  },
  {
    name: '高举旗帜',
    file: 'Divination.cs',
    type: '技能',
    cost: '1',
    rarity: '白（Common）',
    effect: '预见 3。抽 2 张牌。\n\n敲后：预见 3→4。',
  },
  {
    name: '横扫',
    file: 'PropheticCleave.cs',
    type: '攻击',
    cost: '1',
    rarity: '白（Common）',
    effect: '对所有敌人造成 10 点伤害。\n先知。\n\n敲后：伤害 10→14。',
  },
  {
    name: '后撤',
    file: 'WardOfForesight.cs',
    type: '技能',
    cost: '2',
    rarity: '白（Common）',
    effect: '获得 7 点格挡。\n先知。\n\n敲后：格挡 7→10。',
  },
  {
    name: '试探打击（已删除）',
    file: '(deleted)',
    type: '—',
    cost: '—',
    rarity: '—',
    effect: '已按需求删除（原白卡 JustLucky）。',
  },
  {
    name: '先制',
    file: 'CutThroughFate.cs',
    type: '攻击',
    cost: '1',
    rarity: '白（Common）',
    effect: '造成 7 点伤害。预见 2。抽 1 张牌。\n\n敲后：伤害 7→9，预见 2→3。',
  },
  {
    name: '修顿',
    file: 'ThirdEye.cs',
    type: '技能',
    cost: '1',
    rarity: '白（Common）',
    effect: '获得 7 点格挡。预见 3。\n\n敲后：格挡 7→9，预见 3→5。',
  },
  {
    name: '预备',
    file: 'RearrangedFate.cs',
    type: '技能',
    cost: '0',
    rarity: '白（Common）',
    effect: '将任意数量的手牌放到抽牌堆顶。消耗、保留。\n\n敲后：去掉消耗。',
  },
  {
    name: '先知打击',
    file: 'BuildingMomentum.cs',
    type: '攻击',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '造成 6 点伤害。你每拥有 1 张先知牌，此牌额外造成 2 点伤害。\n先知。\n\n敲后：伤害 6→9，每张增量 2→3。',
  },
  {
    name: '白刃乱舞',
    file: 'FlurryStrike.cs',
    type: '攻击',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '造成 3 点伤害 X 次。X 为本回合此前打出的牌数。\n\n敲后：伤害 3→4。',
  },
  {
    name: '奋不顾身',
    file: 'RecklessCharge.cs',
    type: '攻击',
    cost: '0',
    rarity: '白（Common）',
    effect: '造成 11 点伤害。将一张眩晕加入你的弃牌堆。\n\n敲后：伤害 11→15。',
  },
  {
    name: '伺机而动',
    file: 'WaitForTheMoment.cs',
    type: '攻击',
    cost: '2',
    rarity: '白（Common）',
    effect: '造成 12 点伤害。如果你在本回合内预见过牌，获得 2 点能量。\n\n敲后：伤害 12→16。',
  },

  // ---- 蓝（Uncommon）----------------------------------------------------
  {
    name: '按部就班',
    file: 'BalancedInsight.cs',
    type: '能力',
    cost: '3',
    rarity: '蓝（Uncommon）',
    effect: '获得 1 点力量与 1 点敏捷。\n先知。\n\n敲后：力量 1→2，敏捷 1→2。',
  },
  {
    name: '厚积薄发',
    file: 'AccumulatedFate.cs',
    type: '攻击',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '对所有敌人造成 6 点伤害。本场战斗中每触发过一次先知效果，此牌伤害 +3。（卡面另显示本场已触发先知次数）\n先知。\n\n敲后：伤害 6→9，每次增量 +3→+4。',
  },
  {
    name: '引蛇出洞',
    file: 'UnplayedOmen.cs',
    type: '技能',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect: '不能被打出。\n先知：抽 2 张牌。\n\n敲后：抽牌 2→3。',
  },
  {
    name: '蓄势待发',
    file: 'LatentPower.cs',
    type: '技能',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect: '不能被打出。\n先知：获得 1 点能量。\n\n敲后：能量 1→2。',
  },
  {
    name: '抉择',
    file: 'PurifyingVision.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '预见 2。消耗因此被弃置的牌。抽 2 张牌。\n\n敲后：抽牌 2→3。',
  },
  {
    name: '有条不紊',
    file: 'Foresight.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '在你的回合开始时（抽 5 张之前），预见 3。\n\n敲后：预见 3→4。',
  },
  {
    name: '步步为营',
    file: 'Nirvana.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '每当你预见时，获得 3 点格挡。\n\n敲后：格挡 3→4。',
  },
  {
    name: '回马枪',
    file: 'Weave.cs',
    type: '攻击',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect: '造成 4 点伤害。每当你预见时，将此牌从弃牌堆移回你的手牌。\n\n敲后：伤害 4→6。',
  },
  {
    name: '运筹帷幄',
    file: 'TestSkill.cs',
    type: '技能',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect:
      '将你的所有手牌置于抽牌堆顶，预见 8，然后抽取等量的牌。\n消耗。\n\n敲后：预见 8→10。',
  },
  {
    name: '制敌机先',
    file: 'SeizeTheInitiative.cs',
    type: '攻击',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '造成 9 点伤害。如果目标敌人的意图是攻击，给予其 2 层虚弱。\n\n敲后：伤害 9→12。',
  },
  {
    name: '奇袭',
    file: 'Ambush.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '给予 2 层易伤，获得 1 点力量。如果目标敌人的意图不是攻击，则获得的力量翻倍。\n\n敲后：易伤 2→3，力量 1→2。',
  },
  {
    name: '先见之明',
    file: 'Prescience.cs',
    type: '技能',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect: '固有。预见 3，抽 2 张牌。消耗。\n\n敲后：预见 3→4，抽牌 2→3。',
  },
  {
    name: '韬光养晦',
    file: 'BideTime.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '在本回合保留你的手牌。将手牌中任意数量的牌置于抽牌堆顶。下回合获得 1 点能量。\n\n敲后：下回合能量 1→2。',
  },
  {
    name: '水色睿智',
    file: 'DelayedEcho.cs',
    type: '技能',
    cost: '0',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 2 点能量。本回合结束时，将这张牌的一张复制加入你的弃牌堆。\n消耗。\n\n敲后：能量 2→3。',
  },
  {
    name: '藏器待时',
    file: 'ScryMight.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '打出后每累计预见 6 张牌，获得 1 点力量。\n\n敲后：阈值 6→4。',
  },
  {
    name: '后发先制',
    file: 'ScryAgility.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '打出后每累计预见 7 张牌，获得 1 点敏捷。\n\n敲后：阈值 7→5。',
  },
  {
    name: '挺身而出',
    file: 'UnnamedTechnique.cs',
    type: '技能',
    cost: '2',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 16 点格挡。给予自己 1 层虚弱。下回合获得 1 点能量。\n\n敲后：下回合能量 1→2（格挡与虚弱不变）。',
  },
  {
    name: '能量调和',
    file: 'Equilibrium.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '如果本回合你打出的先知牌数和非先知牌数相等，从抽牌堆检索先知牌和非先知牌各一张加入手牌。\n（当前先知牌 a 张，非先知牌 b 张）\n保留、消耗。\n\n敲后：费用 1→0。',
  },
  {
    name: '现场休整',
    file: 'Reclaim.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '将弃牌堆中至多 2 张牌放到抽牌堆顶。\n\n敲后：获得保留。',
  },

  // ---- 金（Rare）--------------------------------------------------------
  {
    name: '未雨绸缪',
    file: 'PropheticStudy.cs',
    type: '能力',
    cost: '2',
    rarity: '金（Rare）',
    effect: '每当你预见时，抽 1 张牌。\n\n敲后：费用 2→1。',
  },
  {
    name: '积厚成势',
    file: 'FatedVitality.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '打出时，获得卡面上显示的数字点生命上限（基础 2）。\n先知：只把卡面数字抬高 2（不给血上限），本场最多累计到 8。\n消耗。\n\n敲后：基础 2→3；先知增量 +2→+3，上限 8→12。',
  },
  {
    name: '殚精竭虑',
    file: 'CycleOfProphecy.cs',
    type: '能力',
    cost: '0',
    rarity: '金（Rare）',
    effect:
      '获得 2 点能量。预见 2。抽 2 张牌。\n下个回合开始时，将一张眩晕加入你的弃牌堆。\n\n敲后：能量 2→3，预见 2→3，抽牌 2→3。',
  },
  {
    name: '背水一战',
    file: 'GrandProphecy.cs',
    type: '技能',
    cost: '2',
    rarity: '金（Rare）',
    effect:
      '预见 6。消耗因此被弃置的牌，并触发它们的先知效果。抽取剩下的牌。\n\n敲后：预见 6→8。',
  },
  {
    name: '请君入瓮',
    file: 'TestAttack.cs',
    type: '攻击',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '造成 12 点伤害。\n先知：对随机目标打出此牌，然后此牌伤害翻倍。\n\n敲后：伤害 12→16。',
  },
  {
    name: '重整旗鼓',
    file: 'Regroup.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '消耗你抽牌堆、弃牌堆和手牌中的所有状态牌。\n\n敲后：费用 1→0。',
  },
  {
    name: '全力进攻',
    file: 'AllOutAttack.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '你手牌中所有牌的耗能降低 1 点，直到它被打出。\n\n敲后：这张牌自己的费用 1→0。',
  },
  {
    name: '冰刃轮舞',
    file: 'ShuffleReplay.cs',
    type: '攻击',
    cost: '2',
    rarity: '金（Rare）',
    effect:
      '对所有敌人造成 5 点伤害，4 次。\n本场战斗中你每洗牌一次，这张牌获得重放 1。\n\n敲后：次数 4→5。',
  },
  {
    name: '斩铁波',
    file: 'IronWave.cs',
    type: '攻击',
    cost: '0',
    rarity: '白（Common）',
    effect: '造成 4 点伤害，获得 3 点格挡。\n\n敲后：伤害 4→5，格挡 3→5。',
  },
  {
    name: '交叉防御',
    file: 'TwinBulwark.cs',
    type: '技能',
    cost: '1',
    rarity: '白（Common）',
    effect: '获得 5 点格挡，2 次。\n\n敲后：格挡 5→7。',
  },
  {
    name: '水色之舞',
    file: 'CounterStrike.cs',
    type: '攻击',
    cost: '0',
    rarity: '白（Common）',
    effect:
      '造成 11 点伤害。\n只有当敌人的意图是攻击时才能打出。\n\n敲后：伤害 11→15。',
  },
  {
    name: '众志成城',
    file: 'PatientBulwark.cs',
    type: '技能',
    cost: '4',
    rarity: '白（Common）',
    effect:
      '获得 18 点格挡。\n你每抽到一次这张牌，这张牌的耗能-1。\n\n敲后：费用 4→3。',
  },
  {
    name: '霜色华斩',
    file: 'PatientStrike.cs',
    type: '攻击',
    cost: '4',
    rarity: '白（Common）',
    effect:
      '造成 26 点伤害。\n你每抽到一次这张牌，这张牌的耗能-1。\n\n敲后：费用 4→3。',
  },
  {
    name: '严阵以待',
    file: 'ForecastBulwark.cs',
    type: '技能',
    cost: 'X',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 7X 点格挡。下个回合开始时预见 X。\n\n敲后：格挡 7X→9X。',
  },
  {
    name: '命定的抗争',
    file: 'GrowingStrike.cs',
    type: '攻击',
    cost: '2',
    rarity: '蓝（Uncommon）',
    effect:
      '造成 18 点伤害。虚无。\n当这张牌被消耗时，本局游戏中它的伤害永久+2。\n\n敲后：伤害 18→26。',
  },
  {
    name: '因果切断',
    file: 'FatalInsight.cs',
    type: '攻击',
    cost: '2',
    rarity: '金（Rare）',
    effect:
      '造成 13 点伤害。如果击杀目标，永久升级你打出的上一张牌。\n消耗。\n\n敲后：伤害 13→16。',
  },
  {
    name: '夹击之势',
    file: 'EmpoweredVolley.cs',
    type: '攻击',
    cost: 'X',
    rarity: '金（Rare）',
    effect:
      '重复 X 次：获得 1 点力量，对随机敌人造成 10 点伤害。\n\n敲后：伤害 10→14。',
  },
  {
    name: '银铃响起之时',
    file: 'RisingMight.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 3 点临时力量。如果本回合已经打出超过 2 张攻击牌，改为永久获得，并且下回合额外抽 2 张牌。\n\n敲后：力量 3→4。',
  },
  {
    name: '临危不乱',
    file: 'SteadyAgility.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '获得 2 点临时敏捷。如果本回合未受到过伤害，改为永久获得，并且下回合额外获得 2 点能量。\n\n敲后：敏捷 2→3。',
  },
  {
    name: '星光破晓之刻',
    file: 'Judgement.cs',
    type: '能力',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '拥有易伤的敌人受到的伤害增加 25%。拥有虚弱的敌人造成的伤害减少 15%。\n\n敲后：固有。',
  },
  {
    name: '纯爱药丸',
    file: 'PureLovePill.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '获得 10 点格挡，获得 1 层人工制品。消耗。\n\n敲后：格挡 10→14。',
  },
  {
    name: '纯爱形态',
    file: 'PureLoveForm.cs',
    type: '能力',
    cost: '2',
    rarity: '金（Rare）',
    effect:
      '本场战斗中，当你从抽牌堆弃置非先知牌时，使其费用变为 0，直到你下次打出它。\n\n敲后：费用 2→1。',
  },
  {
    name: '长驱直入',
    file: 'Settlement.cs',
    type: '攻击',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '对所有敌人造成 11 点伤害。敌人身上每有一种负面状态，伤害+4。\n\n敲后：伤害 11→15，加成 4→5。',
  },
  {
    name: '她眼中的世界',
    file: 'Insight.cs',
    type: '能力',
    cost: '2',
    rarity: '金（Rare）',
    effect:
      '每回合第一次打出攻击牌时，获得 1 点能量；第一次打出技能牌时，抽 1 张牌；第一次打出能力牌时，预见 2。\n虚无。\n\n敲后：去掉虚无。',
  },

  // ---- 状态牌组（纯爱幻想 / 幻想纯爱 及相关卡）--------------------------------
  {
    name: '纯爱幻想',
    file: 'StrikeStrike.cs',
    type: '状态',
    cost: '1',
    rarity: '状态（Status）',
    effect: '当此牌被消耗时，对随机敌人造成 6 点伤害。消耗。',
  },
  {
    name: '幻想纯爱',
    file: 'DefendDefend.cs',
    type: '状态',
    cost: '1',
    rarity: '状态（Status）',
    effect: '当此牌被消耗时，获得 4 点格挡。消耗。',
  },
  {
    name: '风中笑颜',
    file: 'ReinforceStatus.cs',
    type: '攻击',
    cost: '1',
    rarity: '白（Common）',
    effect: '造成 11 点伤害，将一张幻想纯爱加入你的手牌。\n\n敲后：伤害 11→15。',
  },
  {
    name: '火中白花',
    file: 'SupplyStatus.cs',
    type: '技能',
    cost: '1',
    rarity: '白（Common）',
    effect: '获得 10 点格挡，将一张纯爱幻想加入你的手牌。\n\n敲后：格挡 10→13。',
  },
  {
    name: '常备不懈',
    file: 'ShuffleStatus.cs',
    type: '攻击',
    cost: '0',
    rarity: '白（Common）',
    effect: '造成 7 点伤害，随机将一张纯爱幻想或幻想纯爱放入你的抽牌堆。\n\n敲后：伤害 7→10。',
  },
  {
    name: '趁势而动',
    file: 'PurifyStatus.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '每回合你抽到状态牌的前 1 次，将它消耗。\n\n敲后：前 2 次。',
  },
  {
    name: '破釜沉舟',
    file: 'DetonateStatus.cs',
    type: '攻击',
    cost: '2',
    rarity: '蓝（Uncommon）',
    effect: '消耗你手中全部状态牌，造成 16 点伤害。\n\n敲后：伤害 16→22。',
  },
  {
    name: '少女幻想之忆',
    file: 'TransmuteStatus.cs',
    type: '技能',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '将你抽牌堆、手牌、弃牌堆的所有状态牌随机变为纯爱幻想或幻想纯爱。消耗。\n\n敲后：去掉消耗。',
  },
  {
    name: '冰刃连斩',
    file: 'ExhaustBlast.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '每当你消耗一张牌，对所有敌人造成 3 点伤害。\n\n敲后：伤害 3→4。',
  },
  {
    name: '剑之所指',
    file: 'FreeStatus.cs',
    type: '能力',
    cost: '1',
    rarity: '金（Rare）',
    effect: '你可以免费打出你的纯爱幻想和幻想纯爱。\n\n敲后：固有。',
  },
  {
    name: '心之所向',
    file: 'DoubleStatus.cs',
    type: '能力',
    cost: '1',
    rarity: '金（Rare）',
    effect: '你的纯爱幻想和幻想纯爱造成的伤害、获得的格挡翻倍。\n\n敲后：固有。',
  },
  {
    name: '纵冰横霜',
    file: 'MassStrikeStrike.cs',
    type: '攻击',
    cost: '1',
    rarity: '金（Rare）',
    effect: '造成 18 点伤害，将两张纯爱幻想加入你的手牌。\n\n敲后：伤害 18→23。',
  },
  {
    name: '凛冽冰轮',
    file: 'MassDefendDefend.cs',
    type: '攻击',
    cost: '2',
    rarity: '金（Rare）',
    effect: '对全体敌人造成 21 点伤害，将两张幻想纯爱加入你的弃牌堆。\n\n敲后：伤害 21→28。',
  },
  {
    name: '凯旋之路',
    file: 'StatusDraw.cs',
    type: '能力',
    cost: '2',
    rarity: '金（Rare）',
    effect: '当你消耗一张状态牌时，抽一张牌。\n\n敲后：费用 2→1。',
  },

  // ---- 联机专属（Multiplayer-only）---------------------------------------
  // 这 5 张带 CardMultiplayerConstraint.MultiplayerOnly，单人局里不会出现在任何牌池、
  // 奖励或商店（游戏自带机制），所以单机玩家看不到它们。
  {
    name: '先知的指引',
    file: 'GuidanceOfTheProphet.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '从三张随机能力牌中选择一张加入手牌，本回合免费打出。\n将此牌放入随机一名队友的弃牌堆。\n\n敲后：那三张能力牌是已升级的。\n※ 联机专属。',
  },
  {
    // 用户确认过的错别字修正：卡名是「归途终尽之景」，不是「终竟」——卡图文件名一直叫
    // .tools/cardart/归途终尽之景.png。卡类里 EmberBoon.cs 的 CardLoc 已改成「尽」，
    // 这张表是 README 卡牌总表和 Yetannia-卡牌表.xlsx 的唯一数据源，所以这里也必须同步，
    // 否则下次 package-mod.ps1 / cards-xlsx.js 一跑，「竟」会被重新生成回去。
    name: '归途终尽之景',
    file: 'EmberBoon.cs',
    type: '技能',
    cost: '1',
    rarity: '金（Rare）',
    effect:
      '选择一名队友。本场战斗中，该角色每消耗一张牌，随机生成一张牌加入其手牌。此效果不可叠加。\n消耗。\n\n敲后：生成的是已升级的牌。\n※ 联机专属。',
  },
  {
    name: '身先士卒',
    file: 'SharedFocus.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect: '所有玩家获得 1 点敏捷。\n\n敲后：费用 1→0。\n※ 联机专属。',
  },
  {
    name: '天之恩典',
    file: 'SharedRegen.cs',
    type: '技能',
    cost: '0',
    rarity: '白（Common）',
    effect: '所有玩家获得 2 点再生。消耗。\n\n敲后：再生 2→3。\n※ 联机专属。',
  },
  {
    name: '先知的援助',
    file: 'GiftOfTime.cs',
    type: '技能',
    cost: '3',
    rarity: '蓝（Uncommon）',
    effect:
      '选择一名其他角色。该角色本回合结束时，获得一个额外回合。\n结束你的回合。\n消耗。\n\n敲后：费用 3→2。\n※ 联机专属。',
  },
  {
    name: '回应愿景之心',
    file: 'SharedMight.cs',
    type: '能力',
    cost: '1',
    rarity: '蓝（Uncommon）',
    effect:
      '选择一名队友。本场战斗中，当你获得力量和敏捷时（不因此牌），其获得等量力量和敏捷。\n\n敲后：固有。\n※ 联机专属。',
  },
  {
    name: '回溯',
    file: 'Retrospect.cs',
    type: '技能',
    cost: 'X',
    rarity: '金（Rare）',
    effect: '随机打出你弃牌堆的 X 张牌。\n\n敲后：X → X+1。\n※ 写法对齐原版「倾泻」(Cascade)。',
  },
  {
    name: '星痕化',
    file: 'StarscarForm.cs',
    type: '技能',
    cost: '2',
    rarity: '金（Rare）',
    effect: '下个回合，获得 1 层无实体。消耗。\n\n敲后：费用 2→1。',
  },
];

const keywords = [
  ['先知', '当此牌从抽牌堆进入弃牌堆时，触发本牌的先知效果。先知后面没有额外描述时，表示「从抽牌堆被弃置时的效果和打出时一样」。（从手牌被弃置不触发）'],
  ['预见 X', '查看抽牌堆顶的 X 张牌，可任意弃置其中的牌。'],
  ['消耗', '打出后本场战斗不再出现。'],
  ['固有', '战斗开始时必定在起始手牌中。'],
  ['不能被打出', '不能主动打出，只能通过其他效果处理。'],
  ['易伤', '受到的攻击伤害提高。'],
  ['虚弱', '造成的攻击伤害降低。'],
  ['眩晕', '不能被打出的状态牌。'],
  ['再生', '在你的回合结束时回复等量生命，然后减少 1 层。'],
];

// ------------------------------------------------------------------ output

// The mod's version, read straight from the manifest so the table always states which build it
// describes. .tools/package-mod.ps1 regenerates this file on every package, so bumping the version
// in Yetannia.json updates the table for free — there is no second place to keep in sync.
function readModVersion() {
  try {
    const manifest = JSON.parse(
      fs.readFileSync(path.join(__dirname, '..', 'Yetannia', 'Yetannia.json'), 'utf8'));
    return manifest.version || '(no version)';
  } catch (e) {
    return `(unreadable: ${e.message})`;
  }
}

const MOD_VERSION = readModVersion();

// Card faces state their upgrade inline as "<base effect>\n\n敲后：<what changes>". The table shows
// that in its own column instead, so the upgraded card can be read on its own. Nothing is invented:
// the text is split at the marker, and anything after a trailing "※ ..." note belongs to the base
// text rather than to the upgrade.
function splitUpgrade(effect) {
  const marker = '敲后：';
  const i = effect.indexOf(marker);
  if (i < 0) return [effect, ''];

  let base = effect.slice(0, i).replace(/\n+$/, '');
  let up = effect.slice(i + marker.length).trim();

  const note = up.indexOf('\n※');
  if (note >= 0) {
    base = `${base}\n${up.slice(note + 1).trim()}`;
    up = up.slice(0, note).trim();
  }

  return [base, up];
}

// The upgraded cost is already written into the upgrade text as "费用 1→0", so read it from there
// rather than keeping a second copy of the number that could drift.
function upgradedCost(cost, effect) {
  const m = effect.match(/费用\s*([0-9X]+)\s*→\s*([0-9X]+)/);
  return m ? m[2] : cost;
}

const mainSheet = {
  name: '卡牌总表',
  widths: [26, 8, 8, 12, 16, 62, 62],
  rows: [
    [`耶坦尼娅 Yetannia — 卡牌总表   ${MOD_VERSION}`, '', '', '', '', '', ''],
    ['名称', '类型', '花费', '升级后花费', '稀有度', '效果', '升级后效果'],
    ...cards.map((c) => {
      const [base, up] = splitUpgrade(c.effect);
      return [c.name, c.type, c.cost, upgradedCost(c.cost, c.effect), c.rarity, base, up];
    }),
  ],
};

const refRows = [
  [`耶坦尼娅 Yetannia — 对照（源文件）   ${MOD_VERSION}`, '', '', '', ''],
  ['本表由 .tools/cards-xlsx.js 依最新代码与版本号自动生成，手改会在下次打包时被覆盖。', '', '', '', ''],
  ['名称', '源文件', '类型', '花费', '稀有度'],
  ...cards.map((c) => [c.name, c.file, c.type, c.cost, c.rarity]),
  [],
  ['关键词', '说明'],
  ...keywords,
];

const refSheet = {
  name: '对照（源文件）',
  widths: [26, 32, 8, 8, 16],
  rows: refRows,
};

const out = process.argv[2] || path.join(__dirname, '..', 'Yetannia-卡牌表.xlsx');
fs.writeFileSync(out, buildXlsx([mainSheet, refSheet]));

const rarityCount = {};
for (const c of cards) rarityCount[c.rarity] = (rarityCount[c.rarity] || 0) + 1;
const typeCount = {};
for (const c of cards) typeCount[c.type] = (typeCount[c.type] || 0) + 1;

console.log(`wrote ${out} (${fs.statSync(out).size} bytes)`);
console.log(`version: ${MOD_VERSION}`);
console.log(`cards: ${cards.length}`);
console.log('by rarity:', JSON.stringify(rarityCount));
console.log('by type  :', JSON.stringify(typeCount));

// ------------------------------------------------- README card table

// The README's 卡牌总览 section is generated from the same `cards` array as the spreadsheet.
//
// It used to be maintained by hand and had drifted badly: 58 data rows against 82 real cards, the
// heading still claiming "60 张", and 34 cards — every batch added after the table was last touched,
// including 回溯 / 星痕化 / 临危不乱 / 银铃响起之时 — simply absent. package-mod.ps1 runs this script
// on every release, so generating the section here means adding a card cannot leave the README behind.
//
// The prose AROUND the generated block stays hand-written; only the block between the two markers is
// owned by this script. If the markers are missing the sync is skipped with a message rather than
// guessing at a range, because a bad guess would silently delete part of the document.
const README_BEGIN = '<!-- BEGIN CARD TABLE (generated by .tools/cards-xlsx.js - do not edit by hand) -->';
const README_END = '<!-- END CARD TABLE -->';

// A card kept only as a record of something removed. It has no type/cost/rarity, so it cannot go in
// a table with those columns; it is reported in a footnote instead of being dropped in silence.
const isRetired = (c) => c.file === '(deleted)';

function renderReadmeCardTable() {
  const live = cards.filter((c) => !isRetired(c));

  // First-appearance order, so the groups follow the order the cards are declared in above rather
  // than an alphabetisation that would put 基础 first by accident.
  const order = [];
  for (const c of live) if (!order.includes(c.rarity)) order.push(c.rarity);

  const lines = [`**共 ${live.length} 张。**`, ''];

  for (const rarity of order) {
    const group = live.filter((c) => c.rarity === rarity);
    lines.push(`**${rarity}，${group.length} 张**`, '');
    lines.push('| 卡 | 费 | 类型 | 效果 |', '|---|---|---|---|');
    for (const c of group) {
      // A markdown table cell cannot hold a newline. The effect text uses a blank line before the
      // 敲后 clause, which becomes <br> so the upgrade note stays visually separate.
      const effect = c.effect.replace(/\n\n/g, '<br>').replace(/\n/g, ' ');
      const cls = c.file.replace(/\.cs$/, '');
      const name = c.file === '(deleted)' ? c.name : `${c.name} \`${cls}\``;
      lines.push(`| ${name} | ${c.cost} | ${c.type} | ${effect} |`);
    }
    lines.push('');
  }

  const retired = cards.filter(isRetired);
  if (retired.length > 0) {
    lines.push('> 不列入上表的记录项（已删除，仅作存档）：' + retired.map((c) => c.name).join('、') + '。');
    lines.push('');
  }

  return lines.join('\n').trimEnd();
}

function syncReadme() {
  const readme = path.join(__dirname, '..', 'README.md');
  if (!fs.existsSync(readme)) {
    console.log('readme: not found, skipped');
    return;
  }

  const src = fs.readFileSync(readme, 'utf8');
  const begin = src.indexOf(README_BEGIN);
  const end = src.indexOf(README_END);
  if (begin < 0 || end < 0 || end < begin) {
    console.log('readme: markers missing, skipped - add them around the card table to enable syncing');
    return;
  }

  const next = src.slice(0, begin + README_BEGIN.length) + '\n' + renderReadmeCardTable() + '\n' + src.slice(end);
  if (next === src) {
    console.log('readme: card table already up to date');
    return;
  }

  fs.writeFileSync(readme, next, 'utf8'); // no BOM - README.md is read as UTF-8 by every tool here
  console.log(`readme: card table regenerated (${cards.filter((c) => !isRetired(c)).length} cards)`);
}

syncReadme();
