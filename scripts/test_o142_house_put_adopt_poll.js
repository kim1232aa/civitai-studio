#!/usr/bin/env node
/** o142: house PUT includes shot-1; adopt merge + Magao failed+saved poll. */
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o142-house-put-adopt-poll"), "js stamp");
// html stamp/cache may advance (o143+); o142 contracts live in storyboard.js
assert.ok(
  html.includes("v0821o142-house-put-adopt-poll") || html.includes("v0821o143-magao-burn-ui") || html.includes("v0821o144-adv-default-open") || html.includes("v0821o145-smart-match") || html.includes("v0821o146-canvas-hydrate-scope") || html.includes("v0821o147-house-first-after-import") || html.includes("v0821o148-magao-cn-catalog-tongyi") || html.includes("v0821o149b-magao-seed-warn-not-block") || html.includes("v0821o150-nano-prompt-limit-warn"),
  "html stamp o142 or successor"
);
assert.ok(
  /storyboard\.js\?v=o142house|storyboard\.js\?v=o143burn|storyboard\.js\?v=o144adv|storyboard\.js\?v=o145match|storyboard\.js\?v=o146canvas|storyboard\.js\?v=o147house|storyboard\.js\?v=o148magao|storyboard\.js\?v=o149bseed|storyboard\.js\?v=o150nano/.test(html),
  "cache bust o142 or successor"
);

const house = js.slice(js.indexOf("function isMainHouseGraph"), js.indexOf("function persistActiveCanvasSoon"));
assert.ok(house.includes('shot-1'), "house includes shot-1");
assert.ok(house.includes("shot-civitai"), "house keeps shot-civitai");

assert.ok(js.includes("function mergeAdoptShotUrls"), "adopt merge helper");
assert.ok(js.includes("mergeAdoptShotUrls(nodes)"), "adopt uses merge");

const pollStart = js.indexOf("Enter poll unless we already have saved[]");
const pollEnd = js.indexOf("const savedUrl = pickSavedUrl(j);", pollStart);
const poll = js.slice(pollStart, pollEnd);
assert.ok(poll.includes("failSaved"), "poll failSaved");
assert.ok(poll.includes("pickSavedUrl(st)"), "poll checks saved on failed");
assert.ok(poll.includes("pendingWriteback"), "poll checks pendingWriteback");
assert.ok(/if \(failSaved\)[\s\S]*break/.test(poll), "failSaved breaks instead of only throw");

assert.ok(js.includes("writebackShot"), "probe writebackShot");
console.log("PASS o142_house_put_adopt_poll");
