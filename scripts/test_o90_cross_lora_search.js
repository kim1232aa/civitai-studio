#!/usr/bin/env node
/** o90: storyboard cross-house LoRA search + add-then-rematch. String contract only. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o90-cross-lora-search") || html.includes("o90crosslora"), "html stamp o90");
assert.ok(html.includes("v0821o54b-lora-roster-rematch") || html.includes("o54blorarosterrematch"), "html keeps o54b stamp");
assert.ok(source.includes("v0821o90-cross-lora-search"), "js stamp o90");
assert.ok(source.includes("&cross=1"), "search fans out with cross=1");
assert.ok(source.includes("loraHouseLabel"), "house badge helper");
assert.ok(source.includes("class=\"lora-src\"") || source.includes("lora-src"), "source badge in hits");
assert.ok(source.includes("data-src="), "hit carries source");

const addStart = source.indexOf("async function addLora");
const addEnd = source.indexOf("async function resolveOneLora", addStart);
assert.ok(addStart >= 0 && addEnd > addStart, "addLora block");
const addBlock = source.slice(addStart, addEnd);
assert.ok(!/当前模型不支持 LoRA，没加进来/.test(addBlock), "addLora no longer rejects unsupported");
assert.ok(addBlock.includes("applyLoraCapabilityRematch"), "add then rematch");
assert.ok(addBlock.includes("needRematch"), "needRematch flag");
assert.ok((addBlock.match(/strength: null/g) || []).length === 0, "addLora itself does not hardcode strength");

const slStart = source.indexOf("async function searchLoras");
const slEnd = source.indexOf("function bindLoraUi()", slStart);
assert.ok(slStart >= 0 && slEnd > slStart, "searchLoras block");
const searchBlock = source.slice(slStart, slEnd);
assert.ok(!searchBlock.includes("strength: 0.8"), "searchLoras no 0.8");
assert.ok((searchBlock.match(/strength: null/g) || []).length >= 4, "searchLoras add paths use strength: null");
assert.ok(searchBlock.includes("data-src"), "click uses source");

const syncStart = source.indexOf("function syncLoraUi");
const syncEnd = source.indexOf("function setLoraNote", syncStart);
const syncBlock = source.slice(syncStart, syncEnd);
assert.ok(!/loraQ"\)\.disabled = true/.test(syncBlock), "search stays enabled when unsupported");
assert.ok(syncBlock.includes("lora-capability-rematch"), "一键匹配 still present");

console.log("PASS o90_cross_lora_search.js");
