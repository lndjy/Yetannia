// Enables/disables a mod entry inside a Slay the Spire 2 settings.save.
// Usage: node set-mod-enabled.js <settings.save> <modId> <true|false>
const fs = require("fs");

const [, , file, modId, valueArg] = process.argv;
if (!file || !modId || valueArg === undefined) {
  console.error("usage: node set-mod-enabled.js <settings.save> <modId> <true|false>");
  process.exit(2);
}
const want = valueArg === "true";

const raw = fs.readFileSync(file, "utf8");
const json = JSON.parse(raw);

const list = (json.mod_settings && json.mod_settings.mod_list) || [];
const entry = list.find((m) => m.id === modId);
if (!entry) {
  console.error(`mod '${modId}' not found in ${file}`);
  process.exit(1);
}

if (entry.is_enabled === want) {
  console.log(`'${modId}' is already is_enabled=${want}; nothing to do`);
  process.exit(0);
}

fs.writeFileSync(file + ".bak", raw);
entry.is_enabled = want;
fs.writeFileSync(file, JSON.stringify(json));
console.log(`'${modId}': is_enabled ${!want} -> ${want} (backup at ${file}.bak)`);
