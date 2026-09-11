#!/usr/bin/env node
/** o58 T7: Composer fields + per-house LoRA hints from catalog item.
 * No invented 5/12/16. Unknown cap does not hide. Empty backend ≠ nano-gpt.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const hintsSrc = fs.readFileSync(path.join(root, "static/lora-capability-hints.js"), "utf8");
const adaptSrc = fs.readFileSync(path.join(root, "static/composer-field-adapt.js"), "utf8");

assert.ok(!/NANO_LORA_HINTS\s*\.concat/.test(hintsSrc), "no NANO.concat fallback");
assert.ok(!/hintsFor\([\"']nano-gpt[\"']\)\s*\.concat/.test(hintsSrc), "no concat nano onto others");
assert.ok(hintsSrc.includes("z-image-turbo-lora"), "nano hint includes z-image-turbo-lora");
assert.ok(hintsSrc.includes("black-forest-labs/FLUX.1-dev"), "hf hub mid");
assert.ok(hintsSrc.includes("Tongyi-MAI/Z-Image-Turbo"), "modelscope hub");
assert.ok(hintsSrc.includes("image/comfy/krea2/turbo/createImage"), "civitai catalog id");

const sandbox = { console, globalThis: {} };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.runInNewContext(hintsSrc, sandbox, { timeout: 2000 });
vm.runInNewContext(adaptSrc, sandbox, { timeout: 2000 });

const H = sandbox.LoraCapabilityHints;
const A = sandbox.ComposerFieldAdapt;
assert.ok(H && A, "globals");

assert.equal(H.hintsFor("").length, 0);
assert.equal(H.hintsFor("   ").length, 0);
assert.ok(!H.hintsFor("").includes("flux-lora"), "empty backend must not default to nano-gpt");

const houses = ["civitai", "fal", "huggingface", "modelscope-ai", "modelscope-cn", "nano-gpt"];
for (const be of houses) {
  const hints = H.hintsFor(be);
  assert.ok(Array.isArray(hints) && hints.length, be + " has own table");
  if (be === "huggingface") {
    for (const id of hints) {
      assert.ok(!id.startsWith("fal-ai/"), "HF must not hint fal-ai/* got " + id);
    }
    assert.equal(H.isForbiddenCrossHint("huggingface", "fal-ai/flux-lora"), true);
    assert.equal(H.pickHintFromPool("huggingface", [
      { id: "fal-ai/flux-lora", supportsLora: true },
      { id: "black-forest-labs/FLUX.1-dev", supportsLora: true }
    ]), "black-forest-labs/FLUX.1-dev");
  }
}

const items = {
  civitai: {
    id: "image/comfy/krea2/turbo/createImage",
    capabilities: { supportsLora: true, loraShape: "air", durationEnum: ["5", "10"] }
  },
  fal: {
    id: "fal-ai/flux-lora",
    capabilities: { supportsLora: true, loraShape: "path", maxRefs: 4 }
  },
  huggingface: {
    id: "black-forest-labs/FLUX.1-dev",
    capabilities: { supportsLora: false, loraShape: "path", loraChannel: "openai" }
  },
  "modelscope-ai": {
    id: "Qwen/Qwen-Image",
    capabilities: { supportsLora: true, loraShape: "hub_repo" }
  },
  "modelscope-cn": {
    id: "Qwen/Qwen-Image",
    capabilities: { supportsLora: true, loraShape: "hub_repo" }
  },
  "nano-gpt": {
    id: "z-image-turbo-lora",
    capabilities: { supportsLora: true, loraShape: "path", loraConfidence: "heuristic", resolutionTokens: ["768x1024"] }
  }
};

for (const be of houses) {
  const ctx = { backend: be, item: items[be] };
  const caps = A.itemCaps(ctx);
  assert.equal(caps.loraShape, items[be].capabilities.loraShape, be + " loraShape");
  const lora = A.loraUiState(ctx);
  assert.equal(lora.showBox, true, be + " LoRA box stays visible");
  const strip = A.fieldSupportStripText(ctx);
  assert.ok(!strip.includes("5/12/16") || (Array.isArray(items[be].capabilities.durationEnum) && items[be].capabilities.durationEnum.join("/") === "5/10"), be + " no invented duration " + strip);
}

const civ = A.itemCaps({ backend: "civitai", item: items.civitai });
assert.deepEqual(civ.durationEnum, ["5", "10"]);
const falNoEnum = A.itemCaps({ backend: "fal", item: { id: "fal-ai/flux/schnell", capabilities: {} } });
assert.equal(falNoEnum.durationEnum, null);

const unknown = A.loraUiState({ backend: "civitai", item: { id: "mystery" } });
assert.equal(unknown.support, "unknown");
assert.equal(unknown.enabled, true);
assert.equal(unknown.showBox, true);

const seedSupport = A.resolveFieldSupport("seed", { backend: "huggingface", item: items.huggingface });
assert.notEqual(seedSupport, "unsupported");

const nanoRes = A.resolveFieldSupport("nanoRes", { backend: "nano-gpt", item: items["nano-gpt"] });
assert.equal(nanoRes, "supported");

console.log("PASS o58_composer_caps");
