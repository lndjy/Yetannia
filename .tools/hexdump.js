const fs=require("fs");
const fd=fs.openSync(process.argv[2],"r");
const b=Buffer.alloc(160); fs.readSync(fd,b,0,160,0); fs.closeSync(fd);
for(let i=0;i<160;i+=16){
  const row=b.subarray(i,i+16);
  const hex=[...row].map(x=>x.toString(16).padStart(2,"0")).join(" ");
  const asc=[...row].map(x=>(x>=32&&x<127)?String.fromCharCode(x):".").join("");
  console.log(i.toString().padStart(4), hex, "|", asc);
}
console.log("\nas u32 LE:");
for(let i=0;i<80;i+=4) console.log(i.toString().padStart(4), b.readUInt32LE(i));
