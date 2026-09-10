#!/usr/bin/env node
/** o54b: LoRA rematch pulls full /api/catalog roster (like o53d); never invent ids; never silent-drop chips. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o54b-lora-roster-rematch"), "html stamp o54b");
assert.ok(html.includes("o54blorarosterrematch"), "cache bust o54b");
assert.ok(source.includes("v0821o54b-lora-roster-rematch"), "js stamp");
assert.ok(source.includes("loraCapabilityRematchId"), "rematch id");
assert.ok(source.includes("applyLoraCapabilityRematch"), "apply");
assert.ok(source.includes("tryLoraCapabilityRematchAfterServiceChange"), "try after change");
assert.ok(source.includes("正在拉取官方目录匹配 LoRA"), "roster fetch msg");
assert.ok(source.includes("state._catalogRoster"), "roster fill");
assert.ok(source.includes("fillCatalogRosterFromApi") || source.includes("_catalogRoster = roster"), "roster assign");
assert.ok(source.includes('data-act="lora-capability-rematch"') || source.includes("lora-capability-rematch"), "click act");
assert.ok(source.includes("lora-unsupported"), "unsupported class");
assert.ok(source.includes("一键匹配"), "CTA copy");
assert.ok(source.includes("o54b: imported LoRA chips"), "import auto-rematch");
assert.ok(source.includes("NANO_LORA_HINTS") || source.includes("flux-2-dev-lora"), "nano hints");
assert.ok(source.includes("fal-ai/flux-lora/image-to-image"), "fal hints");

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

const poolStart = source.indexOf("function rematchCandidatePool");
const rematchEnd = source.indexOf("function applyCapacityRematchFromWant");
assert.ok(poolStart >= 0 && rematchEnd > poolStart, "pool..rematch");
const helpers = source.slice(poolStart, rematchEnd);

const loraIdFn = extract("loraCapabilityRematchId");
const catalogSupports = extract("catalogItemSupportsLora");
const falTakes = extract("falEndpointTakesLora");

const harness = `
  var state = {
    catalogById: {
      "nano-banana": { id: "nano-banana", name: "Banana", backend: "nano-gpt", supportsLora: false }
    },
    catalog: [],
    _serviceItems: [],
    _catalogRoster: [
      { id: "nano-banana", name: "Banana", backend: "nano-gpt", supportsLora: false },
      { id: "flux-lora", name: "Flux LoRA", backend: "nano-gpt", supportsLora: true },
      { id: "other-model", name: "Other", backend: "nano-gpt", supportsLora: true }
    ],
    loras: [{ name: "chip1", path: "https://example.com/a.safetensors", air: "civitai:1@1" }],
    nodes: [], edges: [], selected: "shot-1", mode: "image"
  };
  var FAL_FLUX_LORA_SERVICE = "fal-ai/flux-lora";
  var FAL_LORA_PREF_SERVICE = "fal-ai/krea-2/turbo/lora";
  function $(id) { return id === "service" ? { value: "nano-banana" } : (id === "backend" ? { value: "nano-gpt" } : null); }
  function currentBackend() { return "nano-gpt"; }
  function isNanogptBe() { return true; }
  function catalogCaps() { return { supportsLora: false }; }
  function catalogItemForService() { return state.catalogById["nano-banana"]; }
  ${falTakes}
  ${catalogSupports}
  ${helpers}
  ${loraIdFn}

  var chipsBefore = state.loras.length;
  var want = loraCapabilityRematchId(state.catalogById["nano-banana"]);
  if (want !== "flux-lora") throw new Error("expected flux-lora rematch, got " + want);
  if (state.loras.length !== chipsBefore) throw new Error("chips silently dropped");
  // never invent out-of-pool
  state._catalogRoster = [{ id: "nano-banana", name: "Banana", backend: "nano-gpt", supportsLora: false }];
  var empty = loraCapabilityRematchId(state.catalogById["nano-banana"]);
  if (empty) throw new Error("invented id " + empty);
`;
vm.runInNewContext(harness, {}, { timeout: 3000 });
console.log("PASS o54b_lora_roster_rematch");
