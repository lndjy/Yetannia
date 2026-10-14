// Fetches bilibili video metadata + subtitle list with a browser-like UA/Referer
// (the plain API 412s without them).
// Usage: node bili.js <bvid>
const https = require("https");

const bvid = process.argv[2];
if (!bvid) {
  console.error("usage: node bili.js <bvid>");
  process.exit(2);
}

function getJSON(url, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    https
      .get(
        url,
        {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            Referer: `https://www.bilibili.com/video/${bvid}`,
            Origin: "https://www.bilibili.com",
            Accept: "application/json, text/plain, */*",
            ...extraHeaders,
          },
        },
        (res) => {
          let body = "";
          res.on("data", (c) => (body += c));
          res.on("end", () => {
            if (res.statusCode !== 200) {
              reject(new Error(`HTTP ${res.statusCode}: ${body.slice(0, 200)}`));
              return;
            }
            try {
              resolve(JSON.parse(body));
            } catch (e) {
              reject(new Error(`bad JSON: ${body.slice(0, 200)}`));
            }
          });
        }
      )
      .on("error", reject);
  });
}

(async () => {
  try {
    const view = await getJSON(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
    if (view.code !== 0) {
      console.log("view API failed:", view.code, view.message);
      return;
    }
    const d = view.data;
    console.log("TITLE:", d.title);
    console.log("UP:", d.owner.name);
    console.log("DURATION(s):", d.duration);
    console.log("PUBDATE:", new Date(d.pubdate * 1000).toISOString());
    console.log("AID:", d.aid, "CID:", d.cid);
    console.log("DESC:\n" + d.desc);

    // Subtitle list (may be empty without login).
    try {
      const player = await getJSON(
        `https://api.bilibili.com/x/player/wbi/v2?aid=${d.aid}&cid=${d.cid}&bvid=${bvid}`
      );
      const subs = (player.data && player.data.subtitle && player.data.subtitle.subtitles) || [];
      console.log("\nSUBTITLES:", subs.length);
      for (const s of subs) {
        console.log("  ", s.lan, s.lan_doc, s.subtitle_url);
      }
    } catch (e) {
      console.log("\nSUBTITLE LOOKUP FAILED:", e.message);
    }
  } catch (e) {
    console.log("ERROR:", e.message);
  }
})();
