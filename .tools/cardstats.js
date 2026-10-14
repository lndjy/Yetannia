// Parses the decompiled Slay the Spire 2 card sources and reports, per (rarity, type, cost),
// the numeric payload of each card. Used to benchmark Yetannia's cards against the base game.
//
// Usage: node cardstats.js <cardsDir> [poolFile1 poolFile2 ...]
const fs = require("fs");
const path = require("path");

const cardsDir = process.argv[2];
const poolFiles = process.argv.slice(3);

function readPool(file) {
  const t = fs.readFileSync(file, "utf8");
  return [...new Set([...t.matchAll(/ModelDb\.Card<([A-Za-z0-9_]+)>/g)].map((m) => m[1]))];
}

function num(re, text) {
  const m = text.match(re);
  return m ? parseFloat(m[1]) : null;
}

function upgradeOf(text, varName) {
  // e.g. base.DynamicVars.Damage.UpgradeValueBy(3m) or DynamicVars["X"].UpgradeValueBy(2m)
  const re = new RegExp(
    `${varName}[^;]{0,80}?UpgradeValueBy\\((\\d+(?:\\.\\d+)?)m\\)`,
    "g"
  );
  const all = [...text.matchAll(re)].map((m) => parseFloat(m[1]));
  return all.length ? all.reduce((a, b) => a + b, 0) : null;
}

const wanted = new Set();
for (const f of poolFiles) for (const n of readPool(f)) wanted.add(n);

const rows = [];
for (const name of wanted) {
  const f = path.join(cardsDir, name + ".cs");
  if (!fs.existsSync(f)) continue;
  const t = fs.readFileSync(f, "utf8");

  const ctor = t.match(/base\((-?\d+),\s*CardType\.(\w+),\s*CardRarity\.(\w+)/);
  if (!ctor) continue;
  const cost = parseInt(ctor[1], 10);
  const type = ctor[2];
  const rarity = ctor[3];
  if (rarity === "Status" || rarity === "Curse" || rarity === "Token" || rarity === "Quest") continue;

  const dmg = num(/new DamageVar\((\d+(?:\.\d+)?)m/, t);
  const blk = num(/new BlockVar\((\d+(?:\.\d+)?)m/, t);
  const vuln = num(/PowerVar<VulnerablePower>\((?:[^,]+,\s*)?(\d+(?:\.\d+)?)m/, t);
  const weak = num(/PowerVar<WeakPower>\((?:[^,]+,\s*)?(\d+(?:\.\d+)?)m/, t);
  const cards = num(/new CardsVar\((\d+)\)/, t);
  const energy = num(/new EnergyVar\((\d+)\)/, t);

  // A rough "value" score: the video's baseline treats one Vulnerable/Weak layer as worth
  // slightly more than 3, so 3 is a conservative stand-in.
  const value = (dmg || 0) + (blk || 0) + 3 * ((vuln || 0) + (weak || 0));

  rows.push({
    name, cost, type, rarity,
    dmg, blk, vuln, weak, cards, energy,
    value,
    dmgUp: upgradeOf(t, "Damage"),
    blkUp: upgradeOf(t, "Block"),
    vulnUp: upgradeOf(t, "Vulnerable"),
    weakUp: upgradeOf(t, "Weak"),
    cardsUp: upgradeOf(t, "Cards"),
  });
}

// Aggregate: for each rarity+type+cost bucket, average damage / block of the *pure* cards.
function bucket(keyFn) {
  const m = new Map();
  for (const r of rows) {
    const k = keyFn(r);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(r);
  }
  return m;
}

function stats(list) {
  const pureDmg = list.filter((r) => r.dmg && !r.blk && !r.vuln && !r.weak);
  const pureBlk = list.filter((r) => r.blk && !r.dmg && !r.vuln && !r.weak);
  const avg = (a, f) => (a.length ? (a.reduce((s, x) => s + f(x), 0) / a.length).toFixed(1) : "-");
  return {
    n: list.length,
    pureDmgN: pureDmg.length,
    pureDmg: avg(pureDmg, (r) => r.dmg),
    pureDmgUp: avg(pureDmg.filter((r) => r.dmgUp != null), (r) => r.dmgUp),
    pureBlkN: pureBlk.length,
    pureBlk: avg(pureBlk, (r) => r.blk),
    pureBlkUp: avg(pureBlk.filter((r) => r.blkUp != null), (r) => r.blkUp),
  };
}

const byRarityType = bucket((r) => `${r.rarity}/${r.type}`);
console.log("=== per rarity/type, PURE damage & block (avg base / avg upgrade) ===");
console.log("bucket".padEnd(22), "n", "pureDmg n/base/up", "  pureBlk n/base/up");
for (const [k, list] of [...byRarityType.entries()].sort()) {
  const s = stats(list);
  console.log(
    k.padEnd(22),
    String(s.n).padStart(2),
    `  ${String(s.pureDmgN).padStart(2)} ${String(s.pureDmg).padStart(5)} ${String(s.pureDmgUp).padStart(4)}`,
    `     ${String(s.pureBlkN).padStart(2)} ${String(s.pureBlk).padStart(5)} ${String(s.pureBlkUp).padStart(4)}`
  );
}

console.log("\n=== rarity/type/cost, PURE damage cards (with names) ===");
const byRTC = bucket((r) => `${r.rarity}/${r.type}/${r.cost}c`);
for (const [k, list] of [...byRTC.entries()].sort()) {
  const pure = list.filter((r) => r.dmg && !r.blk && !r.vuln && !r.weak);
  if (!pure.length) continue;
  console.log(k.padEnd(20), `n=${pure.length}`);
  for (const r of pure.sort((a, b) => (a.dmgUp ?? 0) - (b.dmgUp ?? 0))) {
    console.log(`    ${String(r.dmg).padStart(3)} -> +${r.dmgUp ?? "?"}`.padEnd(16), r.name);
  }
}

console.log("\n=== rarity/type/cost, PURE block cards (with names) ===");
for (const [k, list] of [...byRTC.entries()].sort()) {
  const pure = list.filter((r) => r.blk && !r.dmg && !r.vuln && !r.weak);
  if (!pure.length) continue;
  console.log(k.padEnd(20), `n=${pure.length}`);
  for (const r of pure.sort((a, b) => (a.blkUp ?? 0) - (b.blkUp ?? 0))) {
    console.log(`    ${String(r.blk).padStart(3)} -> +${r.blkUp ?? "?"}`.padEnd(16), r.name);
  }
}

console.log("\n=== cards with Vulnerable or Weak (all) ===");
for (const r of rows.filter((x) => x.vuln || x.weak).sort((a, b) => a.cost - b.cost || a.rarity.localeCompare(b.rarity))) {
  console.log(
    `  ${r.rarity}/${r.type} ${String(r.cost).padStart(2)}c`.padEnd(28),
    `dmg=${String(r.dmg ?? "-").padStart(4)} blk=${String(r.blk ?? "-").padStart(4)} vuln=${r.vuln ?? "-"}${r.vulnUp ? "(+" + r.vulnUp + ")" : ""} weak=${r.weak ?? "-"}${r.weakUp ? "(+" + r.weakUp + ")" : ""}`.padEnd(52),
    r.name
  );
}
