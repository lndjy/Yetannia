// One-off: print the CardLoc title strings of every card file so renames can be scripted exactly.
const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, '..', 'Yetannia', 'Code', 'Cards');
const re = /new CardLoc\(\s*\n?\s*(?:\$?)"([^"]*)"/g;

for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.cs')).sort()) {
  const text = fs.readFileSync(path.join(dir, file), 'utf8');
  const names = [];
  let m;
  while ((m = re.exec(text))) names.push(m[1]);
  if (names.length) console.log(file.padEnd(34) + JSON.stringify(names));
}
