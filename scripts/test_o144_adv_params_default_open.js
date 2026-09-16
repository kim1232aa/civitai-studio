#!/usr/bin/env node
/** o144: advanced params default expanded — advParams must not be hidden on load. */
"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");

assert.ok(html.includes('id="advToggle"'), "advToggle present");
assert.ok(
  html.includes('aria-expanded="true" aria-controls="advParams">高级参数 ▴'),
  "advToggle aria-expanded=true and ▴"
);

const advMatch = html.match(/<div[^>]*id="advParams"[^>]*>/);
assert.ok(advMatch, "advParams element");
assert.ok(!/\bhidden\b/.test(advMatch[0]), "advParams must not have hidden on load");

const comfyMatch = html.match(/<span[^>]*id="comfyParams"[^>]*>/);
assert.ok(comfyMatch, "comfyParams element");
assert.ok(!/class="[^"]*\bhidden\b/.test(comfyMatch[0]), "comfyParams must not start with hidden class");

assert.ok(/storyboard\.js\?v=o14[45]/.test(html), "cache bust storyboard.js o144+/o145");
assert.ok(js.includes("v0821o144-adv-default-open"), "js stamp");
assert.ok(js.includes("syncAdvParamsOpen"), "boot sync helper");
assert.ok(/p0\.hidden\s*=\s*false/.test(js), "boot forces open");

console.log("ok o144_adv_params_default_open");
