// Live canvas: 6 houses × 文生图 / 图生图 / 图生视频. Never persist graph.
import { chromium } from "playwright";
import fs from "node:fs";

const BASE = process.env.STUDIO_URL || "http://127.0.0.1:8080";
const SHOTS = [
  { id: "shot-civitai", be: "civitai" },
  { id: "shot-fal", be: "fal" },
  { id: "shot-mscn", be: "modelscope-cn" },
  { id: "shot-nano", be: "nano-gpt" },
  { id: "shot-hf", be: "huggingface" },
  { id: "shot-msai", be: "modelscope-ai" },
];

function classify(service) {
  const s = String(service || "").toLowerCase();
  if (
    s.includes("image-to-video") || s.includes("imagetovideo") ||
    s.includes("reference-to-video") || s.includes("start-end") ||
    s.includes("ti2v") || s.includes("/i2v") || /(?:^|[-_/])i2v(?:$|[-_/])/.test(s) ||
    s.includes("flf2v") || s.includes("firstlastframetovideo")
  ) return "i2v";
  if (
    s.includes("editimage") || s.includes("/edit") || s.includes("-edit") ||
    s.includes("image-to-image") || s.includes("kontext") || s.includes("createvariant")
  ) return "i2i";
  return "t2i";
}

function okOp(shot, snap, op) {
  if (!snap.service || classify(snap.service) !== op) return false;
  if (op !== "i2v" && snap.be !== shot.be) return false;
  if (shot.be === "civitai" && /^fal-ai\//i.test(snap.service)) return false;
  if (op === "i2i" && (snap.msg || "").indexOf("图生图") < 0) return false;
  if (op === "i2v" && (snap.msg || "").indexOf("图生视频") < 0) return false;
  return true;
}

async function waitService(page, pred, timeout = 25000) {
  const start = Date.now();
  let last = "";
  while (Date.now() - start < timeout) {
    const snap = await page.evaluate(() => ({
      be: (document.getElementById("backend") || {}).value || "",
      service: (document.getElementById("service") || {}).value || "",
      msg: (document.getElementById("msg") || {}).textContent || "",
      mode: document.getElementById("modeVid")?.classList.contains("on") ? "video"
        : document.getElementById("modeImg")?.classList.contains("on") ? "image" : "",
    }));
    last = JSON.stringify(snap);
    if (pred(snap)) return snap;
    await page.waitForTimeout(250);
  }
  throw new Error("timeout waiting service: " + last);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.route("**/api/graph", async (route) => {
    if (route.request().method() === "PUT") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "{\"ok\":true}" });
      return;
    }
    await route.continue();
  });
  await page.goto(BASE + "/?probe=1", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector(".card.shot", { timeout: 20000 });
  await page.waitForFunction(() => window.__sbProbe && typeof window.__sbProbe.selectShot === "function", { timeout: 15000 });
  await page.waitForTimeout(800);

  const report = [];
  for (const shot of SHOTS) {
    const row = { id: shot.id, be: shot.be, t2i: null, i2i: null, i2v: null, msgs: {}, ok: false, err: "" };
    try {
      await page.evaluate((id) => window.__sbProbe.selectShot(id), shot.id);
      await page.waitForTimeout(300);
      const t2i = await waitService(page, (s) => okOp(shot, s, "t2i"), 90000);
      row.t2i = t2i.service;
      row.msgs.t2i = t2i.msg;

      await page.evaluate(() => window.__sbProbe.attachQaRef("/out/house-civitai.jpg"));
      const i2i = await waitService(page, (s) => okOp(shot, s, "i2i"), 90000);
      row.i2i = i2i.service;
      row.msgs.i2i = i2i.msg;

      await page.evaluate(() => window.__sbProbe.setMode("video"));
      const i2v = await waitService(page, (s) => okOp(shot, s, "i2v"), 90000);
      row.i2v = i2v.service;
      row.msgs.i2v = i2v.msg;

      await page.evaluate(() => window.__sbProbe.setMode("image"));
      await page.evaluate(() => window.__sbProbe.clearQaRef());
      await waitService(page, (s) => okOp(shot, s, "t2i"), 90000);
      row.ok = true;
    } catch (err) {
      row.err = String(err && err.message ? err.message : err);
    }
    report.push(row);
    console.log((row.ok ? "PASS" : "FAIL") + " " + shot.id + " t2i=" + row.t2i + " i2i=" + row.i2i + " i2v=" + row.i2v + (row.err ? " :: " + row.err : ""));
  }

  await browser.close();
  const out = "/tmp/o80-smart-match.json";
  fs.writeFileSync(out, JSON.stringify(report, null, 2));
  const failed = report.filter((r) => !r.ok);
  if (failed.length) {
    console.error("FAIL " + failed.length + "/6");
    process.exit(1);
  }
  console.log("PASS o80_live_smart_match 6/6");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
