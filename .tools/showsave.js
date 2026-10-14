const fs=require("fs");
const j=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const keys=Object.keys(j);
console.log("top-level keys:", keys.join(", "));
const s=JSON.stringify(j);
const idx=s.indexOf("Yetannia");
console.log("\ncontext around Yetannia:\n", s.slice(Math.max(0,idx-600), idx+300));
