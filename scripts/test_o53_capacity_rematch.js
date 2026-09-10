#!/usr/bin/env node
/** o53/o53b: N>maxRefs rematch; Fal empty fields eats=false; /image-to-image sibling; link refuse over-cap. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o53-capacity-rematch"), "html stamp");
assert.ok(html.includes("20260911-o53bcapacityrematch") || html.includes("o53capacityrematch"), "cache bust");
assert.ok(source.includes("function capacityRematchId"), "capacityRematchId");
assert.ok(source.includes('data-act="capacity-rematch"'), "一键匹配");
assert.ok(source.includes("Fal t2i with empty imageFields"), "fal eats=false");
assert.ok(source.includes('"/image-to-image"'), "image-to-image sibling");
assert.ok(source.includes("拒新连线（不砍旧线）"), "link gate");

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

const harness = `
  var state = {
    catalogById: {
      "fal-ai/flux-lora": { id: "fal-ai/flux-lora", name: "Flux LoRA", backend: "fal",
        capabilities: { image_to_image: false }, imageFields: [], maxRefs: 1 },
      "fal-ai/flux-lora/image-to-image": { id: "fal-ai/flux-lora/image-to-image", name: "Flux LoRA i2i", backend: "fal",
        capabilities: { image_to_image: true }, imageFields: ["image_url"], maxRefs: 1 },
      "fal-ai/flux-2/edit": { id: "fal-ai/flux-2/edit", name: "Flux2 Edit", backend: "fal",
        capabilities: { image_to_image: true }, imageFields: ["image_urls"], maxRefs: 4 },
      "nano-gpt/x": { id: "nano-gpt/x", name: "Nano", backend: "nano-gpt",
        capabilities: { image_to_image: true }, imageFields: ["input_references"], maxRefs: 5 }
    },
    nodes: [], edges: [], selected: "shot-1", mode: "image"
  };
  function $(id) { return id === "service" ? { value: "fal-ai/flux-lora" } : null; }
  function currentBackend() { return "fal"; }
  function maxRefCount(it) { return it && it.maxRefs != null ? Number(it.maxRefs) : null; }
  function catalogItemSupportsI2i(it) { return !!(it && it.capabilities && it.capabilities.image_to_image); }
  ${extract("catalogEatsRefs")}
  ${extract("editSiblingId")}
  ${extract("capacityRematchId")}

  if (catalogEatsRefs(state.catalogById["fal-ai/flux-lora"]) !== false) throw new Error("flux-lora must not eat");
  if (catalogEatsRefs(state.catalogById["fal-ai/flux-lora/image-to-image"]) !== true) throw new Error("i2i must eat");
  var sib = editSiblingId(state.catalogById["fal-ai/flux-lora"]);
  if (sib !== "fal-ai/flux-lora/image-to-image") throw new Error("sibling want image-to-image got " + sib);
  var m1 = capacityRematchId(1, state.catalogById["fal-ai/flux-lora"]);
  if (m1 !== "fal-ai/flux-lora/image-to-image") throw new Error("N=1 rematch got " + m1);
  var m3 = capacityRematchId(3, state.catalogById["fal-ai/flux-lora"]);
  if (m3 !== "fal-ai/flux-2/edit") throw new Error("N=3 rematch got " + m3);
  if (m3 === "nano-gpt/x") throw new Error("must not cross backend");
`;
vm.runInNewContext(harness, {}, { timeout: 3000 });
console.log("PASS o53_capacity_rematch");
