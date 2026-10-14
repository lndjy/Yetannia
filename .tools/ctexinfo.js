const fs=require("fs");
function hdr(p){
  const b=fs.readFileSync(p);
  const magic=b.toString("ascii",0,4);
  const version=b.readUInt32LE(4);
  const w=b.readUInt32LE(8);
  const h=b.readUInt32LE(12);
  const fmt=b.readUInt32LE(16);
  const mips=b.readUInt32LE(20);
  const flags=b.readUInt32LE(24);
  console.log(`  ${p.split(/[\\/]/).pop()}\n    magic=${magic} ver=${version} ${w}x${h} format=${fmt} mipmaps=${mips} flags=${flags} total=${b.length}`);
}
for (const p of process.argv.slice(2)) { try { hdr(p); } catch(e){ console.log("  ERR", p, e.message); } }
