// Streams a (possibly huge) Slay the Spire 2 godot.log and reports what is in it,
// without ever holding the whole file in memory.
//
// Usage: node analyze-log.js <path> [maxSamplesPerBucket]

const fs = require("fs");
const readline = require("readline");

const path = process.argv[2];
const maxSamples = Number(process.argv[3] || 12);

const total = { lines: 0, bytes: 0 };
const byLevel = new Map();
const templates = new Map();
const templateSample = new Map();
const interesting = [];
const INTERESTING = /\[scry|scrycheck|\[Yetannia|Exception|StackTrace|\[ERROR\]|\[WARN\].*(Yetannia|scry)|GlimpseFate|GLIMPSE_FATE/i;

function templateOf(line) {
  // Collapse the variable parts so repeated spam collapses into one bucket.
  return line
    .replace(/^\s*\[[A-Z]+\]\s*/, "")
    .replace(/\d+(\.\d+)?/g, "#")
    .replace(/0x[0-9a-f]+/gi, "#")
    .slice(0, 160);
}

const rl = readline.createInterface({
  input: fs.createReadStream(path, { encoding: "utf8" }),
  crlfDelay: Infinity,
});

rl.on("line", (line) => {
  total.lines++;
  total.bytes += Buffer.byteLength(line) + 1;

  const level = (line.match(/^\s*\[([A-Z]+)\]/) || [, "(none)"])[1];
  byLevel.set(level, (byLevel.get(level) || 0) + 1);

  const t = templateOf(line);
  templates.set(t, (templates.get(t) || 0) + 1);
  if (!templateSample.has(t)) templateSample.set(t, line.slice(0, 220));

  if (INTERESTING.test(line) && interesting.length < 400) interesting.push(line.slice(0, 300));
});

rl.on("close", () => {
  console.log("=== file ===");
  console.log("lines =", total.lines.toLocaleString(), " bytes =", total.bytes.toLocaleString());
  console.log("\n=== by level ===");
  [...byLevel.entries()].sort((a, b) => b[1] - a[1]).forEach(([k, v]) => {
    console.log(String(v).padStart(12), k);
  });

  console.log("\n=== top 20 repeated line shapes ===");
  [...templates.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20).forEach(([t, n], i) => {
    const pct = ((n / total.lines) * 100).toFixed(1);
    console.log(`\n#${i + 1}  ${n.toLocaleString()} lines (${pct}%)`);
    console.log("   " + (templateSample.get(t) || t));
  });

  console.log("\n=== interesting lines (first " + interesting.length + ") ===");
  interesting.slice(0, maxSamples === 0 ? 0 : 400).forEach((l) => console.log(l));
});
