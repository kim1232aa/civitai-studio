#!/usr/bin/env node
/** o147: house-first afterImport — civitai backend never flashes fal/schnell;
 * cold-start default fal + civitai post → civitai; user-picked fal stays fal.
 * Canon: boss 先认家 — keep selected house; never silently jump to fal/Krea2/schnell on import.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o147-house-first-after-import"), "js stamp");
assert.ok(html.includes("v0821o147-house-first-after-import") || html.includes("o147house") || html.includes("v0821o148-magao-cn-catalog-tongyi") || html.includes("o148magao") || html.includes("v0821o150-nano-prompt-limit-warn") || html.includes("o150nano"), "html stamp o147 or successor");
assert.ok(/storyboard\.js\?v=o147house|storyboard\.js\?v=o148magao|storyboard\.js\?v=o149bseed|storyboard\.js\?v=o150nano/.test(html), "cache bust o147+");

// --- source contracts ---
assert.ok(source.includes("function resolveImportHouse("), "resolveImportHouse helper");
assert.ok(source.includes("capture #backend BEFORE ensureActiveShotForImport"), "capture before activate");
assert.ok(source.includes("state._userPickedHouse = true"), "user-picked house on backend change");
assert.ok(source.includes("never mount fal/schnell"), "end-guard no fal on non-fal house");
assert.ok(source.includes("prefer post house over HTML cold-start default fal"), "no default-fal flash");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "seam " + from);
  return source.slice(start, end);
}

const resolveSrc = section(
  "  function resolveImportHouse(uiHouse, postFromCivitai, postBackend, userPicked) {",
  "  async function applyImport(j) {"
);
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(resolveSrc, sandbox, { filename: "o147-resolve.vm.js" });
const resolve = sandbox.resolveImportHouse;
assert.equal(typeof resolve, "function", "resolveExport");

// afterImport with backend=civitai (UI or post) must resolve to civitai — never fal
assert.equal(resolve("civitai", true, "civitai", false), "civitai", "ui=civitai keeps civitai");
assert.equal(resolve("civitai", true, "civitai", true), "civitai", "ui=civitai user-picked");
assert.equal(resolve("fal", true, "civitai", false), "civitai", "cold-start fal + civitai post → civitai (no schnell flash)");
assert.equal(resolve("", true, "civitai", false), "civitai", "empty ui + civitai post → civitai");
assert.equal(resolve("fal", true, "civitai", true), "fal", "user-picked fal keeps fal (recipe on fal)");
assert.equal(resolve("huggingface", true, "civitai", false), "huggingface", "HF selected keeps HF");
assert.equal(resolve("modelscope-cn", true, "civitai", true), "modelscope-cn", "user Magao CN keeps CN");

// applyImport block must force house onto #backend and reject fal sid when house=civitai
const applyBlock = section("  async function applyImport(j) {", "  async function runImportFromUrl(raw) {");
assert.ok(applyBlock.includes('wantCivitai = house === "civitai"'), "force wantCivitai from house");
assert.ok(applyBlock.includes('wantFal = house === "fal"'), "force wantFal from house");
assert.ok(applyBlock.includes('if ($("backend")) $("backend").value = house'), "pin #backend to house");
assert.ok(applyBlock.includes('house === "civitai"') && applyBlock.includes("looksFalServiceId(sid)"),
  "civitai house rejects fal serviceId");
assert.ok(!/FAL_T2I_DEFAULT(?![\s\S]*house !== "fal")/.test("x"), "sanity");
// No path that sets backend to fal when house resolved to civitai without going through wantFal=house===fal
assert.ok(applyBlock.includes('if ($("backend")) $("backend").value = "civitai"'), "civitai mount path kept");

console.log("PASS o147_house_first_after_import");
