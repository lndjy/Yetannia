// Local NuGet v3 proxy: exposes https://api.nuget.org over plain HTTP on localhost.
// Needed because Windows schannel (and therefore .NET/curl) cannot do TLS inside the
// harness sandbox, while Node's OpenSSL stack can.
//
// Usage: node nuget-proxy.js [port]
const http = require("http");
const https = require("https");
const zlib = require("zlib");

const PORT = Number(process.argv[2] || 8899);
const UPSTREAM = "https://api.nuget.org";
const CDN = "https://globalcdn.nuget.org";
const SELF = `http://127.0.0.1:${PORT}`;

function fetchUpstream(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      { headers: { "User-Agent": "NuGet-Proxy/1.0", Accept: "*/*" } },
      (res) => {
        const { statusCode, headers } = res;
        if ([301, 302, 303, 307, 308].includes(statusCode) && headers.location) {
          res.resume();
          if (redirects >= 10) return reject(new Error("too many redirects"));
          const next = new URL(headers.location, url).toString();
          return resolve(fetchUpstream(next, redirects + 1));
        }
        resolve(res);
      }
    );
    req.on("error", reject);
    req.setTimeout(600000, () => req.destroy(new Error("upstream timeout")));
  });
}

// Rewrite absolute nuget.org URLs inside JSON/text payloads so the client keeps talking to us.
// Every "https://<host>.nuget.org" becomes "http://127.0.0.1:PORT/host/<host>".
function rewrite(body) {
  return body.replace(/https:\/\/([a-z0-9.-]+\.nuget\.org)/gi, (_m, host) => `${SELF}/host/${host}`);
}

const server = http.createServer(async (req, res) => {
  let target;
  const hostRoute = /^\/host\/([a-z0-9.-]+\.nuget\.org)(\/.*)?$/i.exec(req.url);
  if (hostRoute) target = `https://${hostRoute[1]}${hostRoute[2] || "/"}`;
  else if (req.url.startsWith("/cdn/")) target = CDN + req.url.slice(4);
  else if (req.url.startsWith("/www/")) target = "https://www.nuget.org" + req.url.slice(4);
  else target = UPSTREAM + req.url;

  try {
    const up = await fetchUpstream(target);
    const ctype = up.headers["content-type"] || "";
    const isText = /json|xml|text|javascript/i.test(ctype);
    // Some nuget.org endpoints (e.g. registration5-gz-semver2) always answer gzip.
    // Decode here so the client sees a plain body with no content-encoding header.
    const enc = (up.headers["content-encoding"] || "").toLowerCase();
    let stream = up;
    if (isText || enc) {
      if (enc === "gzip") stream = up.pipe(zlib.createGunzip());
      else if (enc === "deflate") stream = up.pipe(zlib.createInflate());
      else if (enc === "br") stream = up.pipe(zlib.createBrotliDecompress());
    }
    res.writeHead(up.statusCode, {
      "content-type": ctype || "application/octet-stream",
      "cache-control": "no-store",
    });
    if (isText) {
      const chunks = [];
      for await (const c of stream) chunks.push(c);
      let body = rewrite(Buffer.concat(chunks).toString("utf8"));
      // Resources that NuGet insists on seeing over HTTPS are simply dropped.
      if (/"@type"\s*:\s*"RepositorySignatures/i.test(body)) {
        try {
          const doc = JSON.parse(body);
          if (Array.isArray(doc.resources)) {
            const dropped = [];
            doc.resources = doc.resources.filter((r) => {
              const t = String(r["@type"] || "");
              const kill = /RepositorySignatures|PackagePublish|SymbolPackagePublish/i.test(t);
              if (kill) dropped.push(t);
              return !kill;
            });
            if (dropped.length) console.log("dropped resources:", dropped.join(", "));
            body = JSON.stringify(doc);
          }
        } catch (e) {
          console.log("index rewrite skipped:", e.message);
        }
      }
      res.end(body);
    } else {
      stream.pipe(res);
    }
  } catch (e) {
    res.writeHead(502, { "content-type": "text/plain" });
    res.end("proxy error: " + e.message);
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`nuget proxy listening on ${SELF} -> ${UPSTREAM}`);
});
