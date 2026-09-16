#!/usr/bin/env node
/** o145: residual fake smart-match — no SMART_PREF on import posts, no recipe Krea auto-pick after import,
 * ensureHf/Ms skip SDXL miss, buildGraph no invent Krea, cache bust o145.
 * Canon: verifier D1–D4 / boss 帖子智能匹配（家优先·底模家族·明说·不许 Krea2 默认）. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const recipe = fs.readFileSync(path.join(root, "static/index.html"), "utf8");
const Fam = require(path.join(root, "static/smart-family-match.js"));

// --- cache bust ---
assert.ok(/storyboard\.js\?v=o14[5-8]/.test(html), "storyboard.js cache bust o145+");

// --- source contracts (canvas) ---
assert.ok(source.includes("import posts (checkpoint/diffusion on shot) never fall through"), "no SMART_PREF on import");
assert.ok(source.includes('if (!hasImportModel)'), "SMART_PREF gated by !hasImportModel");
assert.ok(source.includes("never re-pin Krea-2-Turbo after SDXL"), "ensureHf guard");
assert.ok(source.includes("never re-pin krea/Krea-2-Turbo after SDXL"), "ensureMs guard");
assert.ok(source.includes("SDXL/Pony/SD15 import miss must not invent Krea-2-Turbo on generate"), "buildGraph no invent");
assert.ok(source.includes("不会默认填入 Krea2）"), "↑ hard gate after import miss");

// ensureHf/Ms early-return for sdxl present in both
function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "seam " + from);
  return source.slice(start, end);
}
const ensureHf = section("  function ensureHfLoraServiceSelected() {", "  function hfLoraFixtureImport() {");
assert.ok(ensureHf.indexOf('state._importFamily === "sdxl"') >= 0, "ensureHf sdxl guard");
const ensureMs = section("  function ensureMsLoraServiceSelected() {", "  function msLoraFixtureImport() {");
assert.ok(ensureMs.indexOf('state._importFamily === "sdxl"') >= 0, "ensureMs sdxl guard");

// --- recipe desk contracts ---
assert.ok(recipe.includes("pickDefault: !userPickedId && !selectionLocked() && !lastImport"), "loadCatalog no pickDefault after import");
assert.ok(recipe.includes("if (typeof lastImport !== 'undefined' && lastImport) pickDefault = false"), "renderServiceList lastImport guard");
assert.ok(recipe.includes("non-import Nano t2i default = Z-Image, not Krea2"), "nano t2i not Krea");
assert.ok(/'nano-gpt':\['z-image-turbo-lora','z-image-turbo'/.test(recipe), "nano prefs Z-Image first");
assert.ok(!/'nano-gpt':\['wavespeed-ai\/krea-v2\/turbo-lora'/.test(recipe), "nano prefs no longer Krea-first");

// --- VM: smartSearchQuery still family-first; pickFitFromSearch house-first (o137 retained) ---
const sandbox = {
  console,
  state: { loras: [], _importFamily: "sdxl", catalogById: {} },
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
  { filename: "o145-pick.vm.js" }
);
const q = sandbox.smartSearchQuery("t2i", "sdxl");
assert.ok(q.indexOf("sdxl") >= 0, "query uses family");
assert.equal(sandbox.pickFitFromSearch([
  { id: "fal-ai/krea-2/turbo", ok: true, backend: "fal" }
], "t2i", "civitai"), null, "cross-house rejected");

// Family pick: fal+sdxl still honest empty
assert.equal(Fam.pickByFamily({
  backend: "fal", op: "t2i", family: "sdxl",
  pool: [{ id: "fal-ai/krea-2/turbo", name: "Krea2" }],
  fits: function () { return true; },
  belongs: function (id, be) { return be === "fal"; }
}), "", "fal+sdxl honest empty");

console.log("PASS o145_smart_match_no_fake");
