// Assemble cards.md from head + (per character: heading + roster table + analysis) + tail.
const fs = require("fs");
const path = require("path");
const OUT = "D:\\桌面\\sts2mod\\.tools\\lore-research";
const R = (f) => fs.readFileSync(path.join(OUT, f), "utf8");

const CHARS = [
  ["IRONCLAD", "铁甲战士"],
  ["SILENT", "静默猎手"],
  ["DEFECT", "故障机器人"],
  ["NECROBINDER", "亡灵契约师"],
  ["REGENT", "储君"],
];

const parts = [R("_h-head.md").trimEnd()];
let i = 1;
for (const [ck, cn] of CHARS) {
  const n = ck === "IRONCLAD" ? 90 : 91;
  const sec = [];
  sec.push(`\n---\n`);
  sec.push(`## ${i}. ${ck} ${cn}\n`);
  sec.push(`### ${i}.1 卡牌总表（${n} 张，按本地化 key 排序）\n`);
  sec.push(R(`_t-${ck}.md`).trimEnd());
  sec.push(R(`_a-${ck}.md`).trimEnd());
  parts.push(sec.join("\n"));
  i++;
}
parts.push(R("_z-rest.md").trimEnd());

const md = parts.join("\n") + "\n";
fs.writeFileSync(path.join(OUT, "cards.md"), md, "utf8");
console.log(`cards.md written: ${md.length} chars, ${md.split("\n").length} lines`);
