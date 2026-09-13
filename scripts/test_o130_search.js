import { chromium } from "playwright";
import fs from "fs";

const out = "/workspace/civitai-studio/docs/review-shots";
fs.mkdirSync(out, { recursive: true });
const houses = ["civitai", "fal", "huggingface", "modelscope-ai", "modelscope-cn", "nano-gpt"];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://127.0.0.1:8080/storyboard?t=" + Date.now(), { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
await page.locator(".card.shot").first().click({ position: { x: 40, y: 30 } });
await page.waitForTimeout(500);

const report = {};
for (const be of houses) {
  await page.evaluate((be) => {
    const sel = document.getElementById("backend");
    sel.value = be;
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  }, be);
  await page.waitForTimeout(1600);
  const snap = await page.evaluate(() => {
    const filt = document.getElementById("serviceFilter");
    const lora = document.getElementById("loraQ");
    const r = (el) => {
      if (!el) return { ok: false };
      const s = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return { ok: s.display !== "none" && s.visibility !== "hidden" && b.width > 40 && b.height > 12, w: Math.round(b.width), ph: el.placeholder || "" };
    };
    return {
      ui: (document.getElementById("backend") || {}).value,
      model: r(filt),
      lora: r(lora),
    };
  });
  report[be] = snap;
  console.log("HOUSE", be, JSON.stringify(snap));
  if (snap.ui !== be) { console.error("reverted", be); process.exit(1); }
  if (!snap.model.ok) { console.error("model search hidden", be); process.exit(1); }
  if (!snap.lora.ok) { console.error("lora search hidden", be); process.exit(1); }
}

await page.evaluate(() => {
  const sel = document.getElementById("backend");
  sel.value = "fal";
  sel.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(1800);
await page.fill("#serviceFilter", "krea");
await page.waitForTimeout(800);
const falHits = await page.evaluate(() => [...document.getElementById("service").options].map((o) => o.value).filter(Boolean).slice(0, 8));
console.log("FAL krea hits", falHits);
await page.screenshot({ path: out + "/o130-model-lora-search.png" });
await browser.close();
if (!falHits.some((id) => /krea/i.test(id))) {
  console.error("fal model search did not match krea");
  process.exit(1);
}
console.log("OK model+lora search");
fs.writeFileSync("/tmp/o130-search.json", JSON.stringify(report, null, 2));
