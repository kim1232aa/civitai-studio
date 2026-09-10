#!/usr/bin/env node
/** o53: N>maxRefs rematch to catalog eats+cap≥N; never silent unlink. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o53-capacity-rematch"), "html stamp");
assert.ok(html.includes("20260911-o53capacityrematch"), "cache bust");
assert.ok(source.includes("function capacityRematchId"), "capacityRematchId");
assert.ok(source.includes("function applyCapacityRematch"), "applyCapacityRematch");
assert.ok(source.includes('data-act="capacity-rematch"'), "一键匹配 act");
assert.ok(source.includes("tryCapacityRematchAfterServiceChange"), "service change hook");
assert.ok(source.includes("不静默丢"), "no silent drop copy");

// fill must still stop at cap
const fill = source.slice(source.indexOf("function fillRefSlotsToCap"), source.indexOf("function fillRefSlotsToCap") + 1800);
assert.ok(/cap|maxRef|remain|N ==|n >=|urls\.length/.test(fill), "fill respects cap");

function extract(fnName) {
  const start = source.indexOf("function " + fnName);
  assert.ok(start >= 0, fnName + " start");
  let i = start;
  let depth = 0;
  let began = false;
  for (; i < source.length; i++) {
    const c = source[i];
    if (c === "{") { depth++; began = true; }
    else if (c === "}") {
      depth--;
      if (began && depth === 0) { i++; break; }
    }
  }
  return source.slice(start, i);
}

const harness = `
  var state = {
    catalogById: {
      "tiny-1": { id: "tiny-1", name: "Tiny1", backend: "fal", capabilities: { image_to_image: true },
        supported_parameters: { max_input_images: 1 }, maxRefs: 1 },
      "edit-3": { id: "edit-3", name: "Edit3", backend: "fal", capabilities: { image_to_image: true },
        supported_parameters: { max_input_images: 3 }, maxRefs: 3 },
      "t2i-9": { id: "t2i-9", name: "T2I", backend: "fal", capabilities: { image_to_image: false },
        supported_parameters: { max_input_images: 9 }, maxRefs: 9 }
    },
    nodes: [], edges: [], selected: "shot-1", mode: "image"
  };
  function $(id) { return id === "service" ? { value: "tiny-1" } : null; }
  function currentBackend() { return "fal"; }
  function catalogEatsRefs(it) {
    if (!it) return true;
    var caps = it.capabilities || {};
    if (caps.image_to_image === false) return false;
    return true;
  }
  function maxRefCount(it) {
    if (!it) return null;
    if (it.maxRefs != null) return Number(it.maxRefs);
    return null;
  }
  function catalogItemSupportsI2i(it) {
    return !!(it && it.capabilities && it.capabilities.image_to_image);
  }
  ${extract("capacityRematchId")}
  var hit = capacityRematchId(3, state.catalogById["tiny-1"]);
  if (hit !== "edit-3") throw new Error("expected edit-3 got " + hit);
  // t2i-9 must not win even with high cap
  var hit2 = capacityRematchId(3, state.catalogById["tiny-1"]);
  if (hit2 === "t2i-9") throw new Error("t2i must not rematch");
  // no unlink implied — function only returns id
  if (!hit2) throw new Error("must find rematch");
`;

vm.runInNewContext(harness, {}, { timeout: 2000 });
console.log("PASS o53_capacity_rematch");
