// Verify every quoted string in cards.md against the official localization (verbatim check).
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const LOC = "D:\\桌面\\sts2mod\\.tools\\gamefiles\\localization";
const md = fs.readFileSync(path.join(OUT, "cards.md"), "utf8");
const data = JSON.parse(fs.readFileSync(path.join(OUT, "joined.json"), "utf8"));
const zhsAll = JSON.parse(fs.readFileSync(path.join(LOC, "zhs", "cards.json"), "utf8"));
const lib = JSON.parse(fs.readFileSync(path.join(LOC, "zhs", "card_library.json"), "utf8"));
const sel = JSON.parse(fs.readFileSync(path.join(LOC, "zhs", "card_selection.json"), "utf8"));

// candidate corpus: every description and title in the whole zhs cards.json (not just the 5 pools)
const descs = [];
const titles = new Set();
for (const k of Object.keys(zhsAll)) {
  if (k.endsWith(".description")) descs.push(zhsAll[k]);
  else if (k.endsWith(".title")) titles.add(zhsAll[k]);
}
const extras = [...Object.values(lib), ...Object.values(sel)];
const keyOf = new Map(); // key -> zh title, for label verification
for (const ck of Object.keys(data)) for (const c of data[ck].cards) keyOf.set(c.key, c.zh);

const fail = [];
const ok = [];
const lines = md.split("\n");

function checkQuote(text, where) {
  if (!text.trim()) return;
  if (descs.includes(text) || descs.some((d) => d.includes(text))) return ok.push(text);
  if (extras.includes(text)) return ok.push(text);
  fail.push(`${where} :: ${JSON.stringify(text)}`);
}

// 1) blockquotes
let buf = [];
let bufStart = 0;
function flush() {
  if (!buf.length) return;
  let rest = buf.slice();
  // optional first line: "`KEY` 中文名" label
  const label = rest[0].match(/^`([A-Z0-9_]+)`\s*(.*)$/);
  if (label) {
    const [k, name] = [label[1], label[2].trim()];
    if (!keyOf.has(k)) { fail.push(`LABEL-UNKNOWN-KEY line ${bufStart} :: ${k}`); buf = []; return; }
    if (name && keyOf.get(k) !== name) fail.push(`LABEL-MISMATCH line ${bufStart} :: ${k} expected "${keyOf.get(k)}" got "${name}"`);
    else ok.push(`label ${k}`);
    rest = rest.slice(1);
  }
  const raw = rest.join("\n");
  if (raw.trim()) checkQuote(raw, `quote@line ${bufStart}`);
  buf = [];
}

for (let i = 0; i < lines.length; i++) {
  const L = lines[i];
  if (L.startsWith("> ")) {
    if (!buf.length) bufStart = i + 1;
    buf.push(L.slice(2));
  } else if (L.trim() === ">") {
    buf.push("");
  } else {
    flush();
  }
}
flush();

// 2) inline code spans containing placeholders or [gold] tags
const CJK = /[\u4e00-\u9fff]/;
const inlineRe = /`([^`\n]+)`/g;
let m;
while ((m = inlineRe.exec(md))) {
  const s = m[1];
  if (!/[{}[\]]/.test(s)) continue;      // needs a placeholder or tag
  if (!CJK.test(s)) continue;            // schematic / path / tag-only
  if (s.includes("…")) continue;         // deliberately truncated ellipsis quote
  if (s.startsWith('"')) continue;       // verified by the lib check below
  if (/\\|\.cs\b/.test(s)) continue;     // file path
  if (/^[A-Z0-9_]+$/.test(s)) continue;  // key
  checkQuote(s, "inline");
}

// 3) full-width double-quoted values from card_library.json in tables
const libRe = /"([A-Z_]+)": "([^"]+)"/g;
while ((m = libRe.exec(md))) {
  const [, k, v] = m;
  if (lib[k] === v || sel[k] === v) ok.push(`lib ${k}`);
  else fail.push(`LIB-MISMATCH :: ${k} => ${JSON.stringify(v)} (official: ${JSON.stringify(lib[k] ?? sel[k])})`);
}

console.log(`OK checks: ${ok.length}`);
console.log(`FAILURES: ${fail.length}`);
for (const f of fail) console.log("  " + f);
if (!fail.length) console.log("\n全部引用与官方文本逐字一致（含占位符与标点）。");
