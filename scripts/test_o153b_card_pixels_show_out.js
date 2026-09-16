#!/usr/bin/env node
/** o153b: force card face pixels to /out after writeback — hard reset, late renderCards cannot leave import paint. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

// --- stamps ---
assert.ok(js.includes("v0821o153b-card-pixels-show-out"), "js stamp o153b");
assert.ok(
  html.includes("v0821o153b-card-pixels-show-out") || html.includes("o153bcardpixels"),
  "html stamp o153b"
);
assert.ok(/storyboard\.js\?v=o153bcardpixels/.test(html), "cache bust o153bcardpixels");

// --- patchShotCardMediaDom hard-reset patterns ---
const patchStart = js.indexOf("function patchShotCardMediaDom(");
assert.ok(patchStart >= 0, "patchShotCardMediaDom exists");
const patchEnd = js.indexOf("\n  function cardMediaSrcFromDom", patchStart);
assert.ok(patchEnd > patchStart, "patch body bounded");
const patchBody = js.slice(patchStart, patchEnd);

assert.ok(/backgroundImage\s*=\s*["']["']/.test(patchBody) || /backgroundImage\s*=\s*""/.test(patchBody),
  "patch clears backgroundImage");
assert.ok(/face\.innerHTML\s*=\s*["']["']/.test(patchBody), "patch clears face.innerHTML (fresh media)");
assert.ok(/removeAttribute\(\s*["']src["']\s*\)/.test(patchBody), "patch removeAttribute('src') before assign");
assert.ok(/createElement\(\s*["']img["']\s*\)/.test(patchBody), "patch creates fresh img");
assert.ok(/dataset\.faceUrl/.test(patchBody), "patch sets dataset.faceUrl");
assert.ok(/shot-empty-shell/.test(patchBody), "patch removes shot-empty-shell");

// --- cardHTML never paints importSourceUrl into face ---
const cardStart = js.indexOf("function cardHTML(n)");
const cardShot = js.indexOf('if (n.kind === "shot")', cardStart);
const cardShotEnd = js.indexOf('if (n.kind === "shot")', cardShot); // first only
const cardBody = js.slice(cardShot, cardShot + 800);
assert.ok(/displayMediaSrc\(n\.url/.test(cardBody), "cardHTML face uses n.url via displayMediaSrc");
assert.ok(!/displayMediaSrc\(\s*n\.importSourceUrl/.test(cardBody), "cardHTML must not paint importSourceUrl");
assert.ok(/NEVER importSourceUrl/.test(js), "cardHTML comment forbids importSourceUrl");

// --- renderCards post-pass patches /out ---
const renderStart = js.indexOf("function renderCards()");
const renderEnd = js.indexOf("\n  function worldBounds()", renderStart);
const renderBody = js.slice(renderStart, renderEnd);
assert.ok(/isStudioOutUrl\(u\)/.test(renderBody) || /indexOf\(["']\/out\//.test(renderBody), "renderCards checks /out via isStudioOutUrl");
assert.ok(/patchShotCardMediaDom\(n\.id/.test(renderBody), "renderCards post-pass calls patch for /out");
assert.ok(js.includes("function isStudioOutUrl"), "isStudioOutUrl helper");
assert.ok(js.includes("function studioOutPath"), "studioOutPath helper");
assert.ok(/decoding["']?\s*,\s*["']sync["']/.test(js) || /setAttribute\(\s*["']decoding["']\s*,\s*["']sync["']/.test(js), "img decoding=sync");
assert.ok(/_demotedAfterGen/.test(js), "demote 导入原图 asset after /out writeback");

// --- writebackResult schedules re-patch ---
const wbStart = js.indexOf("function writebackResult(shot, url)");
const wbEnd = js.indexOf("\n  /** o153: display src", wbStart);
const wbBody = js.slice(wbStart, wbEnd);
assert.ok(/_facePaintTs/.test(wbBody), "writeback sets _facePaintTs");
assert.ok(/patchShotCardMediaDom\(live\.id,\s*cleanUrl/.test(wbBody), "writeback patches after render");
assert.ok(
  /requestAnimationFrame/.test(wbBody) || /setTimeout\(/.test(wbBody),
  "writeback schedules re-patch (rAF or setTimeout)"
);
assert.ok(/setTimeout\([\s\S]*?,\s*0\s*\)/.test(wbBody), "writeback setTimeout(0) re-patch");
assert.ok(/setTimeout\([\s\S]*?,\s*50\s*\)/.test(wbBody), "writeback setTimeout(50) re-patch");

// --- callers after writebackResult+renderCards re-patch OR renderCards always re-patches /out ---
// renderCards always re-patches /out (asserted above). Also check key call sites re-patch after extra renderCards.
const histWb = js.indexOf("writebackResult(shot, item.url)");
assert.ok(histWb >= 0, "hist-pin writeback");
const histSlice = js.slice(histWb, histWb + 450);
assert.ok(
  /patchShotCardMediaDom\(shot\.id,\s*shot\.url/.test(histSlice) || /patchShotCardMediaDom\(n\.id/.test(renderBody),
  "hist-pin re-patches OR renderCards always patches /out"
);

// poll completion (~9521)
const pollMark = 'setMsg(prefix + "此镜完成，已写入卡片"';
let idx = 0;
let pollRePatch = 0;
while ((idx = js.indexOf(pollMark, idx)) >= 0) {
  const window = js.slice(Math.max(0, idx - 500), idx);
  if (/writebackResult\(shot,\s*url\)/.test(window) && /patchShotCardMediaDom\(shot\.id/.test(window)) {
    pollRePatch++;
  }
  idx += pollMark.length;
}
assert.ok(
  pollRePatch >= 1 || /patchShotCardMediaDom\(n\.id/.test(renderBody),
  "poll callers re-patch after writeback+renderCards OR renderCards always patches /out"
);

// resume pending callers
const resumeMarks = [
  "上游失败但本地成片已写回原卡",
  "已恢复写回原卡（服务端）",
  "已恢复写回原卡",
];
let resumeOk = 0;
for (const mark of resumeMarks) {
  let i = 0;
  while ((i = js.indexOf(mark, i)) >= 0) {
    const window = js.slice(Math.max(0, i - 600), i + 80);
    if (/writebackResult\(/.test(window) && /patchShotCardMediaDom\(shot\.id/.test(window)) {
      resumeOk++;
    }
    i += mark.length;
  }
}
assert.ok(
  resumeOk >= 1 || /patchShotCardMediaDom\(n\.id/.test(renderBody),
  "resume callers re-patch OR renderCards always patches /out"
);

console.log("PASS o153b_card_pixels_show_out");
