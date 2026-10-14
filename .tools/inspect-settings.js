const fs=require("fs");
const j=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
console.log("mod_settings keys:", Object.keys(j.mod_settings||{}).join(", "));
const list=(j.mod_settings&&j.mod_settings.mod_list)||[];
console.log("mod_list length:", list.length);
console.log("first entry:", JSON.stringify(list[0]));
