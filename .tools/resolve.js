const https=require("https");
const url=process.argv[2];
https.get(url,{headers:{"User-Agent":"Mozilla/5.0"}},r=>{
  console.log("status",r.statusCode);
  console.log("location",r.headers.location||"(none)");
  r.resume();
}).on("error",e=>console.log("ERR",e.message));
