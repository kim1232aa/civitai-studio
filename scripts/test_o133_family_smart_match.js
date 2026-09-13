#!/usr/bin/env node
/** o133: Civitai 帖智能匹配按当前家+底模家族，对不上清空，不许 Krea2 顶 SDXL。 */
"use strict";
const assert = require("node:assert/strict");
const path = require("path");
const api = require(path.resolve(__dirname, "../static/smart-family-match.js"));

assert.equal(api.inferModelFamily("image/sdcpp/sdxl/createImage"), "sdxl");
assert.equal(api.inferModelFamily("image/comfy/krea2/turbo/createImage"), "krea2");
assert.equal(api.familyFromAir("urn:air:sdxl:lora:civitai:1@2"), "sdxl");
assert.equal(api.familyFromAir("urn:air:krea2:lora:civitai:2323765@3071582"), "krea2");
assert.equal(api.familyFromImport({
  serviceId: "image/sdcpp/sdxl/createImage",
  checkpointName: "Juggernaut XL",
  diffusionModel: "urn:air:sdxl:checkpoint:civitai:1@2"
}), "sdxl");

const sdxlShot = { checkpointName: "Juggernaut XL", serviceId: "image/sdcpp/sdxl/createImage" };
assert.equal(api.familyFromShot(sdxlShot), "sdxl");

assert.equal(api.keepCurrent({
  currentId: "image/comfy/krea2/turbo/createImage",
  item: { id: "image/comfy/krea2/turbo/createImage", name: "Krea2" },
  op: "t2i",
  family: "sdxl",
  fits: function () { return true; }
}), false, "krea2 must not keep against sdxl post");

assert.equal(api.keepCurrent({
  currentId: "image/sdcpp/sdxl/createImage",
  item: { id: "image/sdcpp/sdxl/createImage", name: "SDXL" },
  op: "t2i",
  family: "sdxl",
  fits: function () { return true; }
}), true);

const pool = [
  { id: "image/comfy/krea2/turbo/createImage", name: "Krea2 Turbo" },
  { id: "image/sdcpp/sdxl/createImage", name: "SDXL" },
  { id: "image/flux1/dev/createImage", name: "Flux Dev" }
];
function fits(it, op) { return op === "t2i"; }
function belongs(id, be) { return be === "civitai"; }

assert.equal(api.pickByFamily({
  backend: "civitai", op: "t2i", family: "sdxl", pool: pool, fits: fits, belongs: belongs
}), "image/sdcpp/sdxl/createImage");

assert.equal(api.preferredId("civitai", "flux", "t2i"), "image/sdcpp/flux1/createImage");
assert.equal(api.pickByFamily({
  backend: "civitai", op: "t2i", family: "flux", pool: pool.concat([{ id: "image/sdcpp/flux1/createImage", name: "Flux1" }]), fits: fits, belongs: belongs
}), "image/sdcpp/flux1/createImage");

assert.equal(api.pickByFamily({
  backend: "fal", op: "t2i", family: "sdxl", pool: [
    { id: "fal-ai/krea-2/turbo", name: "Krea 2" },
    { id: "fal-ai/flux/schnell", name: "Flux" }
  ], fits: fits, belongs: function (id, be) { return be === "fal"; }
}), "", "fal has no sdxl twin — must stay empty");

assert.equal(api.pickByFamily({
  backend: "fal", op: "t2i", family: "flux", pool: [
    { id: "fal-ai/krea-2/turbo", name: "Krea 2" },
    { id: "fal-ai/flux/schnell", name: "Flux Schnell" }
  ], fits: fits, belongs: function (id, be) { return be === "fal"; }
}), "fal-ai/flux/schnell");

assert.equal(api.familyFromImport({
  serviceId: "image/comfy/krea2/turbo/createImage",
  checkpointName: "Flux Asian Utopian",
  ecosystem: "krea2",
  diffusionModel: "urn:air:flux1:checkpoint:civitai:705606@852897"
}), "flux", "AIR flux beats leftover krea2 serviceId");

assert.equal(api.preferredId("fal", "sdxl", "t2i"), "");
assert.equal(api.preferredId("huggingface", "sdxl", "t2i"), "");
assert.equal(api.preferredId("modelscope-ai", "sdxl", "t2i"), "");
assert.equal(api.preferredId("modelscope-cn", "sdxl", "t2i"), "");
assert.equal(api.preferredId("nano-gpt", "sdxl", "t2i"), "");
assert.ok(api.preferredId("civitai", "sdxl", "t2i").indexOf("sdxl") >= 0);
assert.ok(api.preferredId("fal", "krea2", "t2i").indexOf("krea") >= 0);
assert.ok(api.preferredId("huggingface", "krea2", "t2i").indexOf("Krea") >= 0);
assert.ok(api.preferredId("nano-gpt", "krea2", "t2i").indexOf("krea") >= 0);
assert.ok(api.preferredId("modelscope-ai", "krea2", "t2i").indexOf("Krea") >= 0);
assert.ok(api.preferredId("modelscope-cn", "krea2", "t2i").indexOf("Krea") >= 0);

console.log("PASS o133_family_smart_match");
