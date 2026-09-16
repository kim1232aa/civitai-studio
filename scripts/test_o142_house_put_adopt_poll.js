#!/usr/bin/env node
/** o142: house PUT includes shot-1; adopt merge + Magao failed+saved poll. */
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o142-house-put-adopt-poll"), "js stamp");
assert.ok(html.includes("v0821o142-house-put-adopt-poll"), "html stamp");
assert.ok(html.includes("storyboard.js?v=o142house"), "cache bust");

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
