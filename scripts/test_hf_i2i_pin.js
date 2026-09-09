// HuggingFace 图生图 must pin a real i2i model, not t2i Krea-2-Turbo.
// Run: node scripts/test_hf_i2i_pin.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + JSON.stringify(from));
  return source.slice(start, end);
}

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("HF i2i pin id is Qwen-Image-Edit, distinct from t2i turbo", () => {
  assert.match(source, /HF_LORA_PREF_SERVICE\s*=\s*"krea\/Krea-2-Turbo"/);
  assert.match(source, /HF_I2I_PREF_SERVICE\s*=\s*"Qwen\/Qwen-Image-Edit"/);
});

test("catalogItemSupportsI2i exists", () => {
  assert.match(source, /function catalogItemSupportsI2i\(/);
});

function loadPinApi() {
  const sandbox = { console };
  vm.createContext(sandbox);
  const code = [
    "function isHfRepo(s) { return /^[A-Za-z0-9_.-]+\\/[A-Za-z0-9_.-]+$/.test(String(s || '').trim()); }",
    section("  const HF_LORA_PREF_SERVICE =", "  const COMFY_PARAM_IDS ="),
    section("  function looksCivitaiServiceId(", "  function ensureHfLoraServiceSelected("),
    "globalThis.api = { HF_LORA_PREF_SERVICE, pinHfLoraServiceId };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "hf-i2i-pin.vm.js" });
  return sandbox.api;
}

test("empty HF t2i still pins Krea-2-Turbo", () => {
  const api = loadPinApi();
  assert.equal(api.pinHfLoraServiceId("", "t2i"), "krea/Krea-2-Turbo");
  assert.equal(api.pinHfLoraServiceId(""), "krea/Krea-2-Turbo");
});

test("empty HF i2i pins Qwen-Image-Edit, never Krea-2-Turbo", () => {
  const api = loadPinApi();
  assert.equal(api.pinHfLoraServiceId("", "i2i"), "Qwen/Qwen-Image-Edit");
});

test("HF t2i default is rewritten to i2i pin when op is i2i", () => {
  const api = loadPinApi();
  assert.equal(api.pinHfLoraServiceId("krea/Krea-2-Turbo", "i2i"), "Qwen/Qwen-Image-Edit");
});

test("Fal/Civitai sibling on HF i2i becomes Qwen-Image-Edit, not turbo", () => {
  const api = loadPinApi();
  assert.equal(api.pinHfLoraServiceId("fal-ai/krea-2/turbo/lora", "i2i"), "Qwen/Qwen-Image-Edit");
  assert.equal(api.pinHfLoraServiceId("image/comfy/krea2/turbo/createImage", "i2i"), "Qwen/Qwen-Image-Edit");
});

test("user-picked Hub id is not silently swapped", () => {
  const api = loadPinApi();
  assert.equal(api.pinHfLoraServiceId("Qwen/Qwen-Image-Edit", "i2i"), "Qwen/Qwen-Image-Edit");
  assert.equal(api.pinHfLoraServiceId("black-forest-labs/FLUX.1-Kontext-dev", "i2i"), "black-forest-labs/FLUX.1-Kontext-dev");
  assert.equal(api.pinHfLoraServiceId("Tongyi-MAI/Z-Image-Turbo", "t2i"), "Tongyi-MAI/Z-Image-Turbo");
});

function loadCatalogApi() {
  const sandbox = {
    console,
    currentBackend() { return "huggingface"; },
    state: { mode: "image", catalogById: {} },
  };
  vm.createContext(sandbox);
  const code = [
    section("  function catalogEatsRefs(", "  function editSiblingHint("),
    "globalThis.api = { catalogEatsRefs };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "hf-i2i-catalog.vm.js" });
  return sandbox.api;
}

test("catalogEatsRefs: HF Qwen-Image-Edit eats refs; Hub Krea turbo does not", () => {
  const api = loadCatalogApi();
  const qwen = {
    id: "Qwen/Qwen-Image-Edit",
    backend: "huggingface",
    task: "image-to-image",
    tags: ["i2i"],
    needsSource: true,
  };
  const kreaHub = {
    id: "krea/Krea-2-Turbo",
    backend: "huggingface",
    task: "text-to-image",
    tags: ["t2i"],
    capabilities: { image_to_image: false },
  };
  const kreaBare = {
    id: "krea/Krea-2-Turbo",
    backend: "huggingface",
    task: "text-to-image",
    tags: ["t2i"],
  };
  assert.equal(api.catalogEatsRefs(qwen), true);
  assert.equal(api.catalogEatsRefs(kreaHub), false);
  assert.equal(api.catalogEatsRefs(kreaBare), false);
});

test("buildGraph empty HuggingFace i2i uses HF_I2I_PREF_SERVICE and pin(op)", () => {
  const start = source.indexOf("  function buildGraph(shot) {");
  const end = source.indexOf("  async function runShotStep(", start);
  assert.ok(start >= 0 && end > start, "buildGraph exists");
  const build = source.slice(start, end);
  assert.match(build, /HF_I2I_PREF_SERVICE/);
  assert.match(build, /pinHfLoraServiceId\(serviceId,\s*op\)/);
});

(async () => {
  let failed = 0;
  for (const t of tests) {
    try {
      await t.fn();
      console.log("  ok   " + t.name);
    } catch (err) {
      failed += 1;
      console.log("  FAIL " + t.name);
      console.log("       " + (err && err.message ? err.message.split("\n")[0] : err));
    }
  }
  if (failed) {
    console.log("FAIL hf-i2i-pin " + failed);
    process.exit(1);
  }
  console.log("PASS hf-i2i-pin");
})();
