import { chromium } from "playwright";
import fs from "fs";

const out = "/workspace/civitai-studio/docs/review-shots";
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://127.0.0.1:8080/storyboard?t=" + Date.now(), { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
await page.locator(".card.shot").first().click({ position: { x: 40, y: 30 } });
await page.waitForTimeout(600);
const vis = await page.evaluate(() => {
  const r = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, ok: false, why: "missing" };
    const s = getComputedStyle(el);
    const b = el.getBoundingClientRect();
    const ok = s.display !== "none" && s.visibility !== "hidden" && b.width > 8 && b.height > 8;
    return { sel, ok, w: Math.round(b.width), h: Math.round(b.height), display: s.display };
  };
  return {
    download: r("#btnDownload"),
    nine: r("#btnNine"),
    light: r("#btnLight"),
    group: r("#btnGroup"),
    filter: r("#serviceFilter"),
    lora: r("#loraQ"),
    more: r('#shotBar [data-shot-act="more"]'),
    acts: r(".node-acts"),
    tip: r("#canvasTip"),
  };
});
console.log(JSON.stringify(vis, null, 2));
await page.screenshot({ path: out + "/o131-unhide.png" });
await browser.close();
const need = ["download", "nine", "light", "filter", "lora", "more"];
const fail = need.filter((k) => !vis[k] || !vis[k].ok);
if (!vis.acts || vis.acts.display === "none") fail.push("acts");
if (fail.length) {
  console.error("STILL HIDDEN", fail);
  process.exit(1);
}
console.log("OK unhide");
