// Extraction for lore research: join official card pools (game data, for character attribution ONLY)
// with the official localized card text (zhs/eng cards.json).
const fs = require("fs");
const path = require("path");

const ROOT = "D:\\桌面\\sts2mod\\.tools";
const LOC = path.join(ROOT, "gamefiles", "localization");
const CARDS_DIR = path.join(ROOT, "decomp-proj", "MegaCrit", "sts2", "Core", "Models", "Cards");
const POOL_DIR = path.join(ROOT, "decomp-proj", "MegaCrit", "sts2", "Core", "Models", "CardPools");
const OUT = path.join(ROOT, "lore-research");

const zhs = JSON.parse(fs.readFileSync(path.join(LOC, "zhs", "cards.json"), "utf8"));
const eng = JSON.parse(fs.readFileSync(path.join(LOC, "eng", "cards.json"), "utf8"));

const CHARS = [
  ["IRONCLAD", "IroncladCardPool"],
  ["SILENT", "SilentCardPool"],
  ["DEFECT", "DefectCardPool"],
  ["NECROBINDER", "NecrobinderCardPool"],
  ["REGENT", "RegentCardPool"],
];

function pascalToKey(name) {
  let s = name.replace(/([A-Z]+)([A-Z][a-z])/g, "$1_$2");
  s = s.replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  return s.toUpperCase();
}

const report = [];
function log(x) { report.push(x); }

const data = {};
for (const [charKey, poolFile] of CHARS) {
  const src = fs.readFileSync(path.join(POOL_DIR, poolFile + ".cs"), "utf8");
  const classes = [...src.matchAll(/ModelDb\.Card<([A-Za-z0-9_]+)>\(\)/g)].map((m) => m[1]);
  const cards = [];
  for (const cls of classes) {
    const key = pascalToKey(cls);
    const zt = zhs[key + ".title"];
    const et = eng[key + ".title"];
    const zd = zhs[key + ".description"];
    const ed = eng[key + ".description"];
    if (zt === undefined) { log(`MISSING-LOC ${charKey} ${cls} -> ${key}`); continue; }
    let cost = null, type = null, rarity = null;
    const f = path.join(CARDS_DIR, cls + ".cs");
    if (fs.existsSync(f)) {
      const t = fs.readFileSync(f, "utf8");
      const m = t.match(/base\(\s*(-?\d+|X)\s*,\s*CardType\.(\w+)\s*,\s*CardRarity\.(\w+)/);
      if (m) { cost = m[1]; type = m[2]; rarity = m[3]; }
      else log(`NO-CTOR ${charKey} ${cls}`);
    } else log(`NO-FILE ${charKey} ${cls}`);
    cards.push({ key, cls, cost, type, rarity, zh: zt, en: et, zhDesc: zd, enDesc: ed });
  }
  cards.sort((a, b) => a.key.localeCompare(b.key));
  data[charKey] = { poolFile, count: classes.length, cards };
  log(`${charKey}: pool=${classes.length} localized=${cards.length}`);
}

fs.writeFileSync(path.join(OUT, "joined.json"), JSON.stringify(data, null, 1), "utf8");
fs.writeFileSync(path.join(OUT, "extract-report.txt"), report.join("\n"), "utf8");
console.log(report.join("\n"));
