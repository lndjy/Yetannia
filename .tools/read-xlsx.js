// Dumps a worksheet from an .xlsx as TSV, so the card tables can be diffed.
//
// No spreadsheet library is available here, so this does the minimum: unzip is done by the caller
// (PowerShell Expand-Archive), and this reads the two XML parts that matter.
//
// Usage: node .tools/read-xlsx.js <extractedDir> [sheetNumber]

const fs = require("fs");
const path = require("path");

const dir = process.argv[2];
const sheetNo = Number(process.argv[3] || 1);

function decode(s) {
  return s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&amp;/g, "&");
}

// xl/sharedStrings.xml -> [string]
function readSharedStrings() {
  const p = path.join(dir, "xl", "sharedStrings.xml");
  if (!fs.existsSync(p)) return [];
  const xml = fs.readFileSync(p, "utf8");
  const out = [];
  for (const si of xml.match(/<si>[\s\S]*?<\/si>/g) || []) {
    // An <si> can hold several <r><t> runs; concatenate them.
    const runs = si.match(/<t[^>]*>([\s\S]*?)<\/t>/g) || [];
    out.push(runs.map((r) => decode(r.replace(/<[^>]*>/g, ""))).join(""));
  }
  return out;
}

function columnOf(ref) {
  return (ref.match(/^[A-Z]+/) || [""])[0];
}

const shared = readSharedStrings();
const sheetPath = path.join(dir, "xl", "worksheets", `sheet${sheetNo}.xml`);
const sheet = fs.readFileSync(sheetPath, "utf8");

for (const row of sheet.match(/<row[^>]*>[\s\S]*?<\/row>/g) || []) {
  const cells = [];
  for (const c of row.match(/<c[^>]*\/>|<c[^>]*>[\s\S]*?<\/c>/g) || []) {
    const ref = (c.match(/r="([A-Z]+\d+)"/) || [])[1] || "";
    const type = (c.match(/t="([^"]+)"/) || [])[1] || "";
    const v = (c.match(/<v>([\s\S]*?)<\/v>/) || [])[1];
    const is = (c.match(/<is>[\s\S]*?<\/is>/) || [])[0];

    let text = "";
    if (type === "s" && v !== undefined) text = shared[Number(v)] ?? "";
    else if (is) text = decode((is.match(/<t[^>]*>([\s\S]*?)<\/t>/) || [])[1] || "");
    else if (v !== undefined) text = decode(v);

    cells.push({ col: columnOf(ref), text });
  }
  console.log(cells.map((c) => `${c.col}=${c.text.replace(/\r?\n/g, "\\n")}`).join("\t"));
}
