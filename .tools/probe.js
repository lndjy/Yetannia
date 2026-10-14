const fs=require("fs");
const fd=fs.openSync(process.argv[2],"r");
const dirOff=Number(process.argv[3]);
const b=Buffer.alloc(200); fs.readSync(fd,b,0,200,dirOff); fs.closeSync(fd);
for(let i=0;i<200;i+=16){
  const row=b.subarray(i,i+16);
  console.log((dirOff+i).toString().padStart(12), [...row].map(x=>x.toString(16).padStart(2,"0")).join(" "), "|", [...row].map(x=>(x>=32&&x<127)?String.fromCharCode(x):".").join(""));
}
