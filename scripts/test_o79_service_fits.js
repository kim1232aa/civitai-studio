// o79: serviceFitsOp t2i ≠ i2i-only ≠ i2v
// Run: node scripts/test_o79_service_fits.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + JSON.stringify(from));
  return source.slice(start, end);
}

const sandbox = {
  console,
  URLSearchParams,
  fetch: async () => ({ ok: true, json: async () => ({ items: [] }) }),
  state: { mode: "image", catalogById: {}, catalog: [], _catalogRoster: [], _serviceItems: [], edges: [], nodes: [], selected: "shot-1" },
  currentBackend() { return "huggingface"; },
  $() { return { value: "huggingface" }; },
  catalogImageFields() { return []; },
  SINGULAR_FIRST_FIELDS: [],
};

vm.createContext(sandbox);
vm.runInContext(
  [
    "function catalogImageFields(){ return []; }",
    section("  function catalogItemSupportsI2v(", "    // Provider defaults"),
  ].join("\n"),
  sandbox,
  { filename: "o79-service-fits.vm.js" }
);

assert.equal(typeof sandbox.serviceFitsOp, "function", "serviceFitsOp");

const createImage = { id: "image/comfy/krea2/turbo/createImage", operation: "createImage", category: "image", backend: "civitai" };
const editImage = { id: "image/flux2/klein/editImage/9b", operation: "editImage", category: "image", backend: "civitai" };
const qwen = { id: "Qwen/Qwen-Image-Edit", task: "image-to-image", tags: ["i2i"], backend: "huggingface", needsSource: true, category: "image" };
const krea = { id: "krea/Krea-2-Turbo", task: "text-to-image", tags: ["t2i"], backend: "modelscope-ai", category: "image" };
const wan = { id: "Wan-AI/Wan2.2-TI2V-5B", task: "image-to-video", tags: ["i2v", "ti2v"], category: "video", needsFirstFrame: true, backend: "huggingface" };

assert.equal(sandbox.serviceFitsOp(createImage, "t2i"), true);
assert.equal(sandbox.serviceFitsOp(createImage, "i2i"), false);
assert.equal(sandbox.serviceFitsOp(createImage, "i2v"), false);

assert.equal(sandbox.serviceFitsOp(editImage, "i2i"), true);
assert.equal(sandbox.serviceFitsOp(editImage, "t2i"), false);
assert.equal(sandbox.serviceFitsOp(editImage, "i2v"), false);

assert.equal(sandbox.serviceFitsOp(qwen, "i2i"), true);
assert.equal(sandbox.serviceFitsOp(qwen, "t2i"), false);

assert.equal(sandbox.serviceFitsOp(krea, "t2i"), true);
assert.equal(sandbox.serviceFitsOp(krea, "i2i"), false);

assert.equal(sandbox.serviceFitsOp(wan, "i2v"), true);
assert.equal(sandbox.serviceFitsOp(wan, "i2i"), false);
assert.equal(sandbox.serviceFitsOp(wan, "t2i"), false);

assert.ok(!/catalogEatsRefs/.test(section("  function serviceFitsOp(", "  function pickSmartServiceId(")), "serviceFitsOp must not call catalogEatsRefs");

console.log("PASS o79_service_fits");
