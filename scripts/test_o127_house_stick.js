import { chromium } from "playwright";

const houses = ["civitai", "fal", "huggingface", "modelscope-ai", "modelscope-cn", "nano-gpt"];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const posts = [];
page.on("request", (req) => {
  if (req.method() === "POST" && /\/api\/generate$/.test(req.url())) {
    let j = {};
    try { j = JSON.parse(req.postData() || "{}"); } catch (_) {}
    posts.push({ be: j.backend, sid: j.serviceId, promptLen: (j.prompt || "").length });
  }
});
await page.goto("http://127.0.0.1:8080/storyboard?t=" + Date.now(), { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
await page.locator(".card.shot").first().click({ position: { x: 40, y: 30 } });
await page.waitForTimeout(400);

const result = {};
for (const be of houses) {
  await page.selectOption("#backend", be);
  await page.waitForTimeout(1800);
  const live = await page.evaluate(() => ({
    ui: (document.getElementById("backend") || {}).value,
    shot: (() => {
      const id = window.state && window.state.selected;
      const n = (window.state && window.state.nodes || []).find((x) => x && x.id === id);
      return n && (n.backend || (n.composer && n.composer.backend));
    })(),
    service: (document.getElementById("service") || {}).value || "",
    opts: [...(document.getElementById("backend") || {}).options || []].map((o) => o.value),
  }));
  result[be] = live;
  console.log("STICK", be, JSON.stringify(live));
  if (live.ui !== be) {
    console.error("dropdown reverted", be, live.ui);
    process.exit(1);
  }
  if (!live.opts.includes("nano-gpt")) {
    console.error("nano-gpt missing from house list");
    process.exit(1);
  }
}

// outbound check: pin huggingface then click ↑ (may 400; we only assert POST backend)
await page.selectOption("#backend", "huggingface");
await page.waitForTimeout(2200);
await page.evaluate(() => {
  const p = document.getElementById("prompt");
  if (p && (!p.value || p.value.length < 20)) p.value = "A quiet mountain lake at dawn, mist over still water, cinematic light";
  const s = document.getElementById("send");
  if (s) s.click();
});
await page.waitForTimeout(2500);

await browser.close();
const fail = houses.filter((be) => !result[be] || result[be].ui !== be);
console.log("POSTS", JSON.stringify(posts));
if (fail.length) { console.error("FAIL", fail); process.exit(1); }
if (posts.length && posts[posts.length - 1].be !== "huggingface") {
  console.error("outbound backend mismatch", posts[posts.length - 1]);
  process.exit(1);
}
console.log("OK house stick");
