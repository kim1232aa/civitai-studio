// Run scripts/test_storyboard_ui.js against the live storyboard page via playwright.
// Usage: PW_VERSION_OVERRIDE=1.56.1 node /mnt/agents/work/run_ui_eval.mjs [url] [WxH]
import { chromium } from "playwright";
import { readFileSync } from "fs";

const url = process.argv[2] || "http://127.0.0.1:18832/storyboard.html";
const [W, H] = (process.argv[3] || "1440x900").split("x").map(Number);
const snippet = readFileSync(new URL("./test_storyboard_ui.js", import.meta.url), "utf8");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on("console", (m) => { if (m.type() === "error") console.log("[console.error]", m.text().slice(0, 200)); });
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForSelector(".stamp", { state: "attached", timeout: 15000 });
await page.waitForTimeout(800);
try {
  const res = await page.evaluate(snippet);
  console.log("PASS", JSON.stringify(res));
} catch (e) {
  console.log("FAIL", String(e).slice(0, 500));
  process.exitCode = 1;
}
await browser.close();
