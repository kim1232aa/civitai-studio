#!/usr/bin/env node
/** o133: Civitai post family match — keep only same-house + same family.
 * Run: node scripts/test_o133_family_smart_match.js
 * Not a page-↑ acceptance.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

function extract(fnName) {
  const start = source.indexOf("function " + fnName);
  assert.ok(start >= 0, "missing " + fnName + " — family match not merged into storyboard.js");
  let i = start, depth = 0, began = false;
  for (; i < source.length; i++) {
    if (source[i] === "{") { depth++; began = true; }
    else if (source[i] === "}") { depth--; if (began && depth === 0) { i++; break; } }
  }
  return source.slice(start, i);
}

const sandbox = { console };
vm.createContext(sandbox);
vm.runInContext(
  [
    extract("inferModelFamily"),
    extract("itemMatchesFamily"),
  ].join("\n"),
  sandbox
);

const infer = sandbox.inferModelFamily;
const match = sandbox.itemMatchesFamily;

assert.equal(infer("image/sdcpp/sdxl/createImage"), "sdxl");
assert.equal(infer("Pony Diffusion XL"), "pony");
assert.equal(infer("image/comfy/krea2/turbo/createImage"), "krea");
assert.equal(infer("image/sdcpp/flux1/createImage"), "flux");
assert.equal(infer("black-forest-labs/FLUX.1-schnell"), "flux");
assert.equal(infer(""), "");

assert.equal(match({ id: "image/comfy/krea2/turbo/createImage" }, "sdxl"), false);
assert.equal(match({ id: "image/sdcpp/sdxl/createImage" }, "sdxl"), true);
assert.equal(match({ id: "image/comfy/krea2/turbo/createImage" }, ""), true);
assert.equal(match({ id: "image/sdcpp/sdxl/createImage" }, "krea"), false);

assert.ok(!source.includes("跨家搜到") || source.includes("v0821o133-family-match") || source.includes("function inferModelFamily"),
  "family helper must land in storyboard.js before claiming match work");

console.log("PASS o133_family_smart_match");
