const fs=require('fs');
function pngSize(p){const b=fs.readFileSync(p);if(b.slice(0,8).toString('hex')!=='89504e470d0a1a0a')return 'not-png';return b.readUInt32BE(16)+'x'+b.readUInt32BE(20)+' color='+b[25];}
const files=process.argv.slice(2);
for(const f of files){try{console.log(pngSize(f).padEnd(22),f);}catch(e){console.log('ERR'.padEnd(22),f,e.message);}}
