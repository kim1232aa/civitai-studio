#!/usr/bin/env node
/** o148: Magao CN — no Krea-2-Turbo invent default; catalog tip Tongyi; house-first afterImport CN.
 * Canon: boss 先认家 — modelscope-cn never falls to Fal/Krea; unmatched stays empty.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const Fam = require(path.join(root, "static/smart-family-match.js"));

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o148-magao-cn-catalog-tongyi"), "js stamp");
assert.ok(html.includes("v0821o148-magao-cn-catalog-tongyi") || html.includes("o148magao") || html.includes("v0821o150-nano-prompt-limit-warn") || html.includes("v0821o151-fal-schnell-steps-honest") || html.includes("v0821o151b-fal-steps-hint-sticky") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("o150nano"), "html stamp o148 or successor");
assert.ok(/storyboard\.js\?v=o148magao|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o149bseed|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o150nano|storyboard\.js\?v=o151bsticky|storyboard\.js\?v=o152nano|storyboard\.js\?v=o153writeback/.test(html), "cache bust o148 or successor");

// --- no Krea invent as Magao SMART_PREF / pin default ---
assert.ok(source.includes('const MS_T2I_PREF_SERVICE = "Tongyi-MAI/Z-Image-Turbo"'), "Tongyi pref const");
assert.ok(source.includes("FORBIDDEN default was Krea-2-Turbo"), "forbidden Krea note");
assert.ok(source.includes("never invent Krea as Magao default"), "promote note");
// SMART_PREF modelscope-cn t2i must lead with Tongyi and must NOT list Krea first
const cnPref = source.match(/"modelscope-cn":\s*\{[\s\S]*?t2i:\s*\[([^\]]+)\]/);
assert.ok(cnPref, "modelscope-cn SMART_PREF block");
assert.ok(cnPref[1].includes("Tongyi-MAI/Z-Image-Turbo"), "CN SMART_PREF has Tongyi");
assert.ok(!/^\s*"krea\/Krea-2-Turbo"/.test(cnPref[1].trim()) && !cnPref[1].trim().startsWith('"krea/Krea-2-Turbo"'),
  "CN SMART_PREF must not start with Krea");
assert.ok(!cnPref[1].includes("krea/Krea-2-Turbo"), "CN SMART_PREF must not invent Krea at all");

const aiPref = source.match(/"modelscope-ai":\s*\{[\s\S]*?t2i:\s*\[([^\]]+)\]/);
assert.ok(aiPref && aiPref[1].includes("Tongyi-MAI/Z-Image-Turbo") && !aiPref[1].includes("krea/Krea-2-Turbo"),
  "AI SMART_PREF Tongyi only");

// pinMs must refuse inventing Krea when empty
function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "seam " + from);
  return source.slice(start, end);
}
const pinSrc = section("  function pinMsLoraServiceId(sid, op) {", "  function msLoraOptionLabel(");
assert.ok(pinSrc.includes('return ""'), "pinMs empty → \"\"");
assert.ok(pinSrc.includes("never invent Krea-2-Turbo"), "pinMs no invent note");

const ensSrc = section("  function ensureMsLoraServiceSelected() {", "  function msLoraFixtureImport() {");
assert.ok(ensSrc.includes("do not invent Krea"), "ensureMs no invent");
assert.ok(ensSrc.includes("if (!want)"), "ensureMs early empty");

// resolveImportHouse still keeps Magao CN (o147 retained)
const resolveSrc = section(
  "  function resolveImportHouse(uiHouse, postFromCivitai, postBackend, userPicked) {",
  "  async function applyImport(j) {"
);
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(resolveSrc, sandbox, { filename: "o148-resolve.vm.js" });
assert.equal(sandbox.resolveImportHouse("modelscope-cn", true, "civitai", true), "modelscope-cn");
assert.equal(sandbox.resolveImportHouse("modelscope-cn", false, "", false), "modelscope-cn");

// Family: zimage → Tongyi on Magao CN (import mounts once catalog has model)
assert.equal(Fam.preferredId("modelscope-cn", "zimage", "t2i"), "Tongyi-MAI/Z-Image-Turbo");
assert.equal(Fam.preferredId("modelscope-ai", "zimage", "t2i"), "Tongyi-MAI/Z-Image-Turbo");
assert.equal(
  Fam.pickByFamily({
    backend: "modelscope-cn",
    op: "t2i",
    family: "zimage",
    pool: [
      { id: "krea/Krea-2-Turbo", name: "Krea", task: "text-to-image", tags: ["t2i"], backend: "modelscope-cn" },
      { id: "Tongyi-MAI/Z-Image-Turbo", name: "Z-Image", task: "text-to-image", tags: ["t2i", "zimage"], backend: "modelscope-cn" },
    ],
    fits: function () { return true; },
    belongs: function (id, be) { return be === "modelscope-cn"; },
  }),
  "Tongyi-MAI/Z-Image-Turbo",
  "zimage pick Tongyi not Krea"
);
// o137/o148 house-first: preferred Tongyi may mount even if cold pool only has Krea pin —
// that invents the correct CN twin, never invents Krea as the answer.
assert.equal(
  Fam.pickByFamily({
    backend: "modelscope-cn",
    op: "t2i",
    family: "zimage",
    pool: [{ id: "krea/Krea-2-Turbo", name: "Krea", task: "text-to-image", tags: ["t2i"], backend: "modelscope-cn" }],
    fits: function () { return true; },
    belongs: function (id, be) { return be === "modelscope-cn"; },
  }),
  "Tongyi-MAI/Z-Image-Turbo",
  "zimage + Krea-only pool → house Tongyi (not Krea)"
);
assert.notEqual(
  Fam.pickByFamily({
    backend: "modelscope-cn",
    op: "t2i",
    family: "zimage",
    pool: [{ id: "krea/Krea-2-Turbo", name: "Krea", task: "text-to-image", tags: ["t2i"], backend: "modelscope-cn" }],
    fits: function () { return true; },
    belongs: function (id, be) { return be === "modelscope-cn"; },
  }),
  "krea/Krea-2-Turbo",
  "must never pick Krea for zimage"
);

// applyImport Magao path must not tell user to pick Krea
const applyBlock = section("  async function applyImport(j) {", "  async function runImportFromUrl(raw) {");
assert.ok(applyBlock.includes("不会默认 Krea") || applyBlock.includes("Tongyi-MAI/Z-Image-Turbo 或本家模型"),
  "reject Fal/Civitai message points to Tongyi not Krea");

console.log("PASS o148_magao_cn_no_krea_default");
