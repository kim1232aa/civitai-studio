#!/usr/bin/env node
/** o163: LoRA/params follow per-endpoint official schema — no house-wide strip. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const o61 = fs.readFileSync(path.join(root, "static/o61-group-hide.js"), "utf8");
const o68 = fs.readFileSync(path.join(root, "static/o68-capability-hide.js"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.js"), "utf8");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

assert.ok(!/if \(be !== "civitai"\) \{\s*hide\(wrapOf\(ctx\.\$\("sampler"\)\)/.test(o61),
  "o61 must not hide sampler/scheduler for every non-civitai house");
assert.ok(!/if \(be !== "civitai"\) \{\s*hide\(wrapOf\(ctx\.\$\("sampler"\)\)/.test(o68),
  "o68 must not hide sampler/scheduler for every non-civitai house");

const pack = js.slice(js.indexOf("function packComfyParamsForPayload"), js.indexOf("async function loadComfyDefaults"));
assert.ok(!/else if \(be !== "civitai"\) \{\s*delete p\.sampler/.test(pack),
  "pack must not strip steps/cfg/sampler for every non-civitai house");
assert.ok(!/delete p\.steps;\s*delete p\.cfg;\s*delete p\.cfgScale;\s*delete p\.width/.test(pack),
  "pack must not house-strip Fal steps/cfg/size");
assert.ok(pack.includes("dropOfficialNo"), "pack omits only official_fields===false");
assert.ok(pack.includes("nano-gpt") && pack.includes("resolution"), "nano token packed");

assert.ok(adapt.includes('width: ["width", "image_size"]'), "width maps to image_size");
assert.ok(adapt.includes('height: ["height", "image_size"]'), "height maps to image_size");
assert.ok(!/showComfyGroup = !textish && !nano/.test(adapt),
  "adapt must not hide whole #comfyParams because nano-gpt");
assert.ok(!/showComfy = !textish && !nano/.test(o61),
  "o61 must not hide whole #comfyParams because nano-gpt");
assert.ok(o61.includes("unknownLora"), "o61 shows LoRA when supportsLora unknown");
assert.ok(!/hasModel && supportsLora === true\);/.test(o61.replace(/\s+/g, " ")),
  "o61 must not require supportsLora===true to show LoRA");

const load = js.slice(js.indexOf("async function loadComfyDefaults"), js.indexOf("function packLoraRow"));
assert.ok(!/if \(\$\("steps"\) && !\$\("steps"\)\.value\) \$\("steps"\)\.value = 8/.test(load),
  "must not invent steps=8 on catch for every house");
assert.ok(load.includes('currentBackend() === "civitai"'),
  "Civitai /api/defaults only fill empty steps/cfg on civitai");

const ctx = {
  window: {},
  console,
};
vm.runInNewContext(adapt, ctx, { timeout: 2000 });
const api = ctx.window.ComposerFieldAdapt;
assert.ok(api && typeof api.officialFieldAllowed === "function", "officialFieldAllowed");

const kreaTurbo = {
  supported_parameters: {
    official_fields: ["prompt", "num_images", "image_size", "seed", "acceleration"]
  }
};
assert.equal(api.officialFieldAllowed(kreaTurbo, "steps"), false, "krea turbo: no steps");
assert.equal(api.officialFieldAllowed(kreaTurbo, "cfg"), false, "krea turbo: no cfg");
assert.equal(api.officialFieldAllowed(kreaTurbo, "width"), true, "krea turbo: image_size → width");
assert.equal(api.officialFieldAllowed(kreaTurbo, "sampler"), false, "krea turbo: no sampler");

const zBase = {
  supported_parameters: {
    official_fields: ["prompt", "num_inference_steps", "guidance_scale", "negative_prompt", "loras", "image_size"]
  }
};
assert.equal(api.officialFieldAllowed(zBase, "steps"), true, "z-image base: steps");
assert.equal(api.officialFieldAllowed(zBase, "cfg"), true, "z-image base: cfg");
assert.equal(api.officialFieldAllowed({ supported_parameters: {} }, "steps"), null, "no table → do not block");

console.log("PASS o163_no_house_cut");
