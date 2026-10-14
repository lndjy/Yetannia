const fs=require("fs");
const j=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
if (j.code!==0) { console.log("API code", j.code, j.message); process.exit(0); }
const d=j.data;
console.log("title:", d.title);
console.log("owner:", d.owner.name);
console.log("duration(s):", d.duration);
console.log("desc:\n", d.desc);
console.log("cid:", d.cid);
