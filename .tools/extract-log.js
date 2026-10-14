// Targeted extraction from a huge godot.log: exception fingerprints, [ERROR] lines,
// anything attributable to Yetannia, and scry traces.
//
// Usage: node extract-log.js <path>

const fs = require("fs");
const readline = require("readline");

const path = process.argv[2];

const exceptionCounts = new Map();   // "System.FooException: msg" -> count
const errorLines = [];
const yetanniaHits = [];
const scryLines = [];
const versionLines = [];
const failedMods = new Map();

const MAX = 200;

const rl = readline.createInterface({
  input: fs.createReadStream(path, { encoding: "utf8" }),
  crlfDelay: Infinity,
});

rl.on("line", (line) => {
  const trimmed = line.trim();

  // Exception fingerprints: "System.XException: message"
  const m = trimmed.match(/^(?:\[[A-Z]+\]\s*)?((?:[A-Z][A-Za-z0-9_.]*\.)?[A-Za-z0-9_.]*Exception[A-Za-z0-9_]*):\s*(.*)$/);
  if (m && !trimmed.startsWith("at ")) {
    const key = m[1] + ": " + m[2].slice(0, 150);
    exceptionCounts.set(key, (exceptionCounts.get(key) || 0) + 1);
  }

  if (/^\s*\[ERROR\]/.test(line) && errorLines.length < MAX) errorLines.push(line.slice(0, 300));

  if (/Yetannia/i.test(line) && /Exception|at Yetannia|ERROR|failed|error/i.test(line) && yetanniaHits.length < MAX) {
    yetanniaHits.push(line.slice(0, 300));
  }

  if (/\[scry|scrycheck/i.test(line) && scryLines.length < MAX) scryLines.push(line.slice(0, 300));

  if (/Yetannia \(v|Loaded Mods|Yetannia.*version|Skipping loading mod/i.test(line) && versionLines.length < MAX) {
    versionLines.push(line.slice(0, 220));
  }

  const fm = line.match(/skipped patch type ([^:]+):/);
  if (fm) failedMods.set(fm[1], (failedMods.get(fm[1]) || 0) + 1);
});

rl.on("close", () => {
  console.log("=== distinct exception fingerprints (top 15) ===");
  [...exceptionCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15).forEach(([k, n]) => {
    console.log(String(n).padStart(9), k);
  });

  console.log("\n=== [ERROR] lines (" + errorLines.length + " shown) ===");
  errorLines.forEach((l) => console.log(l));

  console.log("\n=== lines mentioning Yetannia AND error/exception (" + yetanniaHits.length + ") ===");
  yetanniaHits.forEach((l) => console.log(l));

  console.log("\n=== [scry] / scrycheck lines (" + scryLines.length + ") ===");
  scryLines.forEach((l) => console.log(l));

  console.log("\n=== mod load / version lines ===");
  versionLines.forEach((l) => console.log(l));

  console.log("\n=== harmony patch types that failed (" + failedMods.size + ") ===");
  [...failedMods.entries()].slice(0, 25).forEach(([k, n]) => console.log(String(n).padStart(6), k));
});
