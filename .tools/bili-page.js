// Fetches a bilibili video page with browser-like headers and extracts the embedded
// __INITIAL_STATE__ / og: meta information (title, description). The public APIs 412 without
// signed headers, but the watch page itself is usually served.
// Usage: node bili-page.js <BVxxxx>
const https = require("https");

const bvid = process.argv[2];
if (!bvid) {
  console.error("usage: node bili-page.js <BVxxxx>");
  process.exit(2);
}

function fetchText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(
        url,
        {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            Referer: "https://www.bilibili.com/",
          },
        },
        (res) => {
          if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location) {
            res.resume();
            return resolve(fetchText(new URL(res.headers.location, url).toString()));
          }
          let body = "";
          res.setEncoding("utf8");
          res.on("data", (c) => (body += c));
          res.on("end", () => resolve({ status: res.statusCode, body }));
        }
      )
      .on("error", reject);
  });
}

function meta(html, prop) {
  const re = new RegExp(`<meta[^>]+(?:property|name)="${prop}"[^>]+content="([^"]*)"`, "i");
  const m = html.match(re);
  return m ? m[1] : null;
}

(async () => {
  try {
    const { status, body } = await fetchText(`https://www.bilibili.com/video/${bvid}/`);
    console.log("HTTP", status, "bytes", body.length);
    console.log("og:title      :", meta(body, "og:title"));
    console.log("og:description:", meta(body, "og:description"));
    console.log("keywords      :", meta(body, "keywords"));

    const state = body.match(/window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]*?\});\s*\(function/);
    if (state) {
      try {
        const s = JSON.parse(state[1].replace(/undefined/g, "null"));
        console.log("\nvideoData.title:", s.videoData && s.videoData.title);
        console.log("videoData.desc :", s.videoData && s.videoData.desc);
        console.log("videoData.duration:", s.videoData && s.videoData.duration);
        console.log("videoData.pages:", JSON.stringify((s.videoData && s.videoData.pages || []).map(p => p.part)));
      } catch (e) {
        console.log("state parse failed:", e.message);
      }
    } else {
      console.log("\nno __INITIAL_STATE__ found");
    }
  } catch (e) {
    console.log("ERROR:", e.message);
  }
})();
