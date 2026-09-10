// o41: fillRefSlotsToCap uses real /out/fill-cap-{i}.jpg; never phantom o40-fill
// Run: node scripts/test_o41_fill_real_fixtures.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const server = fs.readFileSync(path.join(root, "server.py"), "utf8");

assert.ok(html.includes("v0821o45-magao-edit2509-refs3"), "html stamp o41");
assert.ok(html.includes("storyboard.js?v=20260910-o45magaoedit2509refs3"), "cache bust o41");
assert.ok(source.includes("v0821o41:"), "js header o41");
assert.ok(source.includes("/out/fill-cap-"), "fill-cap urls");
assert.ok(!source.includes("/out/o40-fill-"), "no phantom o40-fill");
assert.ok(server.includes("def ensure_fill_cap_fixtures"), "server ensure helper");
assert.ok(server.includes("ensure_fill_cap_fixtures()"), "server boot calls ensure");
assert.ok(server.includes("fal-refs-fill-9"), "copies from fal-refs-fill-9");

for (let i = 1; i <= 9; i++) {
  const fp = path.join(root, "out", "fill-cap-" + i + ".jpg");
  assert.ok(fs.existsSync(fp), "fixture missing: " + fp);
  assert.ok(fs.statSync(fp).size > 0, "fixture empty: " + fp);
}

// Reuse o40 behavioral harness via require of sibling assertions by spawning logic:
require("./test_o40_fill_exact_cap.js");

console.log("PASS o41 fill-real-fixtures");
