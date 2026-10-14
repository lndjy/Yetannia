// Dedupes the noise out of a huge godot.log: unique [ERROR] messages and unique
// Yetannia stack frames, each with a count.
//
// Usage: node dedupe-errors.js <path>

const fs = require("fs");
const readline = require("readline");

const path = process.argv[2];

const errors = new Map();
const frames = new Map();
const gameActions = new Map();

const rl = readline.createInterface({
  input: fs.createReadStream(path, { encoding: "utf8" }),
  crlfDelay: Infinity,
});

rl.on("line", (line) => {
  const trimmed = line.trim();

  if (trimmed.startsWith("[ERROR]")) {
    // Collapse ids/numbers so repeated instances of the same failure group together.
    const key = trimmed.replace(/\d+/g, "#").slice(0, 240);
    if (!errors.has(key)) errors.set(key, { n: 0, sample: trimmed.slice(0, 240) });
    errors.get(key).n++;
  }

  const f = trimmed.match(/^\s*at (Yetannia[^(]*)(\(.*)?$/);
  if (f) {
    const key = f[1].trim();
    frames.set(key, (frames.get(key) || 0) + 1);
  }

  const g = trimmed.match(/GameAction (\S+) .*? completed with exception: (.*)$/);
  if (g) {
    const key = g[1] + " :: " + g[2].replace(/\d+/g, "#").slice(0, 160);
    gameActions.set(key, (gameActions.get(key) || 0) + 1);
  }
});

rl.on("close", () => {
  console.log("=== unique [ERROR] messages (" + errors.size + ") ===");
  [...errors.values()].sort((a, b) => b.n - a.n).forEach((e) => {
    console.log(String(e.n).padStart(7), e.sample);
  });

  console.log("\n=== Yetannia stack frames (" + frames.size + ") ===");
  [...frames.entries()].sort((a, b) => b[1] - a[1]).forEach(([k, n]) => {
    console.log(String(n).padStart(7), k);
  });

  console.log("\n=== failing game actions (" + gameActions.size + ") ===");
  [...gameActions.entries()].sort((a, b) => b[1] - a[1]).forEach(([k, n]) => {
    console.log(String(n).padStart(7), k);
  });
});
