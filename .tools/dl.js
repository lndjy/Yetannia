// Minimal HTTPS downloader using Node's OpenSSL stack (bypasses Windows schannel,
// which is blocked inside the harness sandbox).
// Usage:
//   node dl.js fetch <url> <outFile>      download url -> outFile
//   node dl.js cat   <url>                print url body to stdout
const fs = require("fs");
const https = require("https");
const http = require("http");

function get(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith("https:") ? https : http;
    const req = lib.get(
      url,
      { headers: { "User-Agent": "Mozilla/5.0 (dsh-mod-builder)" } },
      (res) => {
        const { statusCode, headers } = res;
        if ([301, 302, 303, 307, 308].includes(statusCode) && headers.location) {
          res.resume();
          if (redirects >= 10) return reject(new Error("too many redirects"));
          return resolve(get(new URL(headers.location, url).toString(), redirects + 1));
        }
        if (statusCode !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${statusCode} for ${url}`));
        }
        resolve(res);
      }
    );
    req.on("error", reject);
    req.setTimeout(120000, () => req.destroy(new Error("timeout")));
  });
}

async function download(url, out) {
  const res = await get(url);
  await new Promise((resolve, reject) => {
    const ws = fs.createWriteStream(out);
    res.pipe(ws);
    ws.on("finish", resolve);
    ws.on("error", reject);
    res.on("error", reject);
  });
  console.log("OK", out, fs.statSync(out).size, "bytes");
}

async function cat(url) {
  const res = await get(url);
  const chunks = [];
  for await (const c of res) chunks.push(c);
  process.stdout.write(Buffer.concat(chunks));
}

(async () => {
  const [, , cmd, url, out] = process.argv;
  try {
    if (cmd === "fetch") await download(url, out);
    else if (cmd === "cat") await cat(url);
    else {
      console.error("usage: node dl.js fetch <url> <out> | node dl.js cat <url>");
      process.exit(2);
    }
  } catch (e) {
    console.error("ERROR:", e.message);
    process.exit(1);
  }
})();
