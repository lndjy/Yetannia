const fs=require("fs");
const f=process.argv[2];
const j=JSON.parse(fs.readFileSync(f,"utf8"));
for (const k of process.argv.slice(3)) console.log(k, "=", JSON.stringify(j[k]));
