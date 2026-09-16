#!/usr/bin/env node
/** o137: house-first smart match — no cross-house, no Krea2 on flux/sdxl, honest miss, family search key. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const Fam = require(path.join(root, "static/smart-family-match.js"));
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

// --- (b) no Krea2 when family is flux/sdxl; (c) honest miss ---
assert.equal(Fam.keepCurrent({
  currentId: "image/comfy/krea2/turbo/createImage",
  item: { id: "image/comfy/krea2/turbo/createImage", name: "Krea2" },
  op: "t2i", family: "sdxl", fits: function () { return true; }
}), false, "sdxl post must not keep Krea2");

assert.equal(Fam.keepCurrent({
  currentId: "image/comfy/krea2/turbo/createImage",
  item: { id: "image/comfy/krea2/turbo/createImage", name: "Krea2" },
  op: "t2i", family: "flux", fits: function () { return true; }
}), false, "flux post must not keep Krea2");

assert.equal(Fam.pickByFamily({
  backend: "civitai", op: "t2i", family: "sdxl",
  pool: [{ id: "image/comfy/krea2/turbo/createImage", name: "Krea2 Turbo" }],
  fits: function () { return true; },
  belongs: function (id, be) { return be === "civitai"; }
}), "image/sdcpp/sdxl/createImage", "pref sdxl even if pool only has Krea2");

assert.equal(Fam.pickByFamily({
  backend: "fal", op: "t2i", family: "sdxl",
  pool: [
    { id: "fal-ai/krea-2/turbo", name: "Krea2" },
    { id: "fal-ai/flux/schnell", name: "Flux" }
  ],
  fits: function () { return true; },
  belongs: function (id, be) { return be === "fal"; }
}), "", "fal+sdxl honest empty — never Krea2");

assert.equal(Fam.preferredId("fal", "sdxl", "t2i"), "");
assert.equal(Fam.preferredId("huggingface", "flux", "t2i").indexOf("FLUX") >= 0 || Fam.preferredId("huggingface", "flux", "t2i") === "black-forest-labs/FLUX.1-schnell", true);

// --- storyboard.js source contracts ---
assert.ok(source.includes("base-model family is the primary key"), "family-first search comment");
assert.ok(!/names\.slice\(0,\s*2\)\.join/.test(source), "LoRA-name primary search gone");
assert.ok(source.includes('cross: "0"'), "smart-match forces cross=0");
assert.ok(source.includes("NEVER return a foreign-house hit"), "pickFitFromSearch house-first");
assert.ok(source.includes("Never fall through to SMART_PREF Krea2"), "no Krea2 fallback on family posts");
assert.ok(source.includes("这家没有可匹配的"), "honest miss copy");
assert.ok(source.includes("跨家搜到"), "o93 stamp string retained");

// --- (a) cross-house rejected via pickFitFromSearch VM ---
function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "seam " + from);
  return source.slice(start, end);
}

const sandbox = {
  console,
  state: { loras: [{ name: "AsianMixXL" }], _importFamily: "sdxl", catalogById: {} },
  serviceFitsOp: function (it) { return !!(it && it.ok); },
  serviceBelongsToBackend: function (sid, be) {
    const s = String(sid || "");
    const fal = /^fal-ai\//i.test(s);
    const civ = /^(image|video)\//.test(s);
    if (be === "civitai") return civ && !fal;
    if (be === "fal") return fal;
    return !fal && !civ;
  },
  rematchCandidatePool: function () { return sandbox.state.catalogById; },
  URLSearchParams,
};
vm.createContext(sandbox);
vm.runInContext(
  section("  function smartSearchQuery(op, family) {", "  function loraSourceHouses(") +
  section("  function pickFitFromSearch(items, op, preferBe) {", "  async function smartMatchService("),
  sandbox,
  { filename: "o137-pick.vm.js" }
);

const q = sandbox.smartSearchQuery("t2i", "sdxl");
assert.ok(q.indexOf("sdxl") >= 0, "query uses family: " + q);
assert.ok(q.indexOf("AsianMix") < 0, "query must not lead with LoRA name: " + q);

const foreign = sandbox.pickFitFromSearch([
  { id: "fal-ai/krea-2/turbo", ok: true, backend: "fal" },
  { id: "image/sdcpp/sdxl/createImage", ok: true, backend: "civitai" }
], "t2i", "civitai");
assert.equal(foreign && foreign.id, "image/sdcpp/sdxl/createImage", "prefer civitai in-house");

const rejected = sandbox.pickFitFromSearch([
  { id: "fal-ai/krea-2/turbo", ok: true, backend: "fal" },
  { id: "fal-ai/flux/schnell", ok: true, backend: "fal" }
], "t2i", "civitai");
assert.equal(rejected, null, "cross-house fal hits rejected when preferBe=civitai");

console.log("PASS o137_house_first_smart_match");
