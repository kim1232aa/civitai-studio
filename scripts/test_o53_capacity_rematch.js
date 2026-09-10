#!/usr/bin/env node
/** o53d: rematch from _catalogRoster even when catalogById only has flux-lora. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o53d-capacity-rematch-roster"), "html stamp");
assert.ok(html.includes("o53dcapacityrematchroster"), "cache bust");
assert.ok(source.includes("rematchCandidatePool"), "pool");
assert.ok(source.includes("state._catalogRoster"), "roster");
assert.ok(source.includes('act.dataset.act === "capacity-rematch"'), "click");
assert.ok(source.includes("正在拉取官方目录匹配") || source.includes("不静默丢线"), "visible fail");

function extract(fnName) {
  const start = source.indexOf("function " + fnName);
  assert.ok(start >= 0, fnName);
  let i = start, depth = 0, began = false;
  for (; i < source.length; i++) {
    if (source[i] === "{") { depth++; began = true; }
    else if (source[i] === "}") { depth--; if (began && depth === 0) { i++; break; } }
  }
  return source.slice(start, i);
}

// Also need rematchCandidatePool + FAL hints const before capacityRematchId
const poolStart = source.indexOf("function rematchCandidatePool");
const rematchEnd = source.indexOf("function applyCapacityRematchFromWant");
assert.ok(poolStart >= 0 && rematchEnd > poolStart, "pool..rematch");
const helpers = source.slice(source.indexOf("const FAL_CAPACITY_HINTS"), rematchEnd);

const harness = `
  var state = {
    catalogById: {
      "fal-ai/flux-lora": { id: "fal-ai/flux-lora", name: "Flux LoRA", backend: "fal",
        capabilities: { image_to_image: false }, imageFields: [], maxRefs: 1 }
    },
    catalog: [],
    _serviceItems: [],
    _catalogRoster: [
      { id: "fal-ai/flux-lora", name: "Flux LoRA", backend: "fal",
        capabilities: { image_to_image: false }, imageFields: [], maxRefs: 1 },
      { id: "fal-ai/flux-2/edit", name: "FLUX 2 Edit", backend: "fal",
        capabilities: { image_to_image: true }, imageFields: ["image_urls"], maxRefs: 4 }
    ],
    nodes: [], edges: [], selected: "shot-1", mode: "image"
  };
  function $(id) { return id === "service" ? { value: "fal-ai/flux-lora" } : (id === "backend" ? { value: "fal" } : null); }
  function currentBackend() { return "fal"; }
  function maxRefCount(it) { return it && it.maxRefs != null ? Number(it.maxRefs) : null; }
  function catalogItemSupportsI2i(it) { return !!(it && it.capabilities && it.capabilities.image_to_image); }
  ${extract("catalogEatsRefs")}
  ${helpers}
  ${extract("capacityRematchId")}

  if (Object.keys(state.catalogById).length !== 1) throw new Error("catalogById must only flux-lora");
  var m3 = capacityRematchId(3, state.catalogById["fal-ai/flux-lora"]);
  if (m3 !== "fal-ai/flux-2/edit") throw new Error("roster rematch got " + m3);
`;
vm.runInNewContext(harness, {}, { timeout: 3000 });
console.log("PASS o53_capacity_rematch");
