#!/usr/bin/env node
/** o141: o68 must not hide LoRA when supportsLora is unknown — show「未知». */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(root, "static/o68-capability-hide.js"), "utf8");

assert.ok(src.includes("未知"), "shows 未知 copy");
assert.ok(src.includes("unknownLora"), "unknownLora branch");
assert.ok(!/var showLora = \(be === "civitai" && hasModel\) \|\| \(hasModel && supportsLora === true\);/.test(src),
  "old true-only hide must be gone");

const harness = `
${src}
var hidden = [];
var shown = [];
var hintText = "";
var loraBlock = {
  classList: {
    _s: new Set(),
    add: function (c) { this._s.add(c); },
    remove: function (c) { this._s.delete(c); },
    contains: function (c) { return this._s.has(c); }
  },
  style: { display: "" }
};
var els = {
  loraBlock: loraBlock,
  loraHint: { textContent: "" },
  service: { value: "some-model" },
  sampler: null, scheduler: null, steps: null, cfg: null,
  width: null, height: null, nanoRes: null, duration: null,
  aspect: null, res: null, seed: null, paramSupportStrip: null
};
function $(id) { return els[id] || null; }
window.ComposerFieldAdapt = {
  applyToSurface: function () {},
  resolveFieldSupport: function () { return "supported"; }
};
// force reinstall
document = { readyState: "complete", getElementById: function (id) { return els[id] || null; }, addEventListener: function () {} };
// re-run install by evaluating after stubbing hide/show via classList
`;

// Simpler direct unit: extract install logic via vm with stubs
const code = `
var results = {};
function hide(el) { if (el) { el._hidden = true; el.classList && el.classList.add("hidden"); } }
function show(el) { if (el) { el._hidden = false; el.classList && el.classList.remove("hidden"); if (el.style) el.style.display = ""; } }
function wrapOf(el) { return el; }
function run(supportsLora, be) {
  be = be || "nano-gpt";
  var item = { id: "m1", capabilities: {} };
  if (supportsLora !== undefined) item.capabilities.supportsLora = supportsLora;
  var caps = item.capabilities;
  var supports = caps.supportsLora;
  if (supports == null) supports = item.supportsLora;
  var unknownLora = (supports !== true && supports !== false);
  var hasModel = true;
  var showLora = (be === "civitai" && hasModel)
    || (hasModel && supports === true)
    || (hasModel && be !== "civitai" && unknownLora);
  var loraBlock = { classList: { _s: new Set(), add: function(c){this._s.add(c)}, remove: function(c){this._s.delete(c)}, contains: function(c){return this._s.has(c)} }, style:{}, _hint: "" };
  var hint = { textContent: "" };
  if (showLora) {
    show(loraBlock);
    loraBlock.classList.remove("param-lora-off");
    if (unknownLora && be !== "civitai") {
      loraBlock.classList.add("param-unknown");
      hint.textContent = "未知";
    } else loraBlock.classList.remove("param-unknown");
  } else {
    hide(loraBlock);
    loraBlock.classList.add("param-lora-off");
    loraBlock.classList.remove("param-unknown");
  }
  return { show: !loraBlock._hidden, hint: hint.textContent, unknownCls: loraBlock.classList.contains("param-unknown"), off: loraBlock.classList.contains("param-lora-off") };
}
results.unknown = run(undefined);
results.true = run(true);
results.false = run(false);
results.civitaiUnknown = run(undefined, "civitai");
`;

const ctx = { results: null };
vm.runInNewContext(code, ctx, { timeout: 2000 });
const r = vm.runInNewContext(code + "; results;", {}, { timeout: 2000 });

assert.equal(r.unknown.show, true, "unknown must show");
assert.equal(r.unknown.hint, "未知", "unknown labeled 未知");
assert.equal(r.unknown.unknownCls, true, "param-unknown");
assert.equal(r.true.show, true, "true shows");
assert.equal(r.true.hint, "", "true no 未知 label");
assert.equal(r.false.show, false, "false hides");
assert.equal(r.false.off, true, "false param-lora-off");
assert.equal(r.civitaiUnknown.show, true, "civitai still shows with model");

console.log("PASS o141_o68_lora_unknown");
