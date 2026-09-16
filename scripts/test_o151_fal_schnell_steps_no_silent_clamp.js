#!/usr/bin/env node
/** o151: Fal schnell steps — never silent 20→12; UI #steps + hint「schnell 上限 12，已从原帖 20→12」. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const falPy = fs.readFileSync(path.join(root, "providers/fal.py"), "utf8");
const capsPy = fs.readFileSync(path.join(root, "providers/six_catalog_caps.py"), "utf8");

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o151-fal-schnell-steps-honest"), "js stamp o151");
assert.ok(
  html.includes("v0821o151-fal-schnell-steps-honest")
    || html.includes("v0821o152-nano-aspect-matches-size")
    || html.includes("o152nano"),
  "html stamp o151 or successor"
);
assert.ok(/storyboard\.js\?v=o151fal|storyboard\.js\?v=o152nano/.test(html), "cache bust o151+");

// --- FE contracts ---
assert.ok(source.includes("function falStepsMax("), "falStepsMax helper");
assert.ok(source.includes("function honestFalSchnellStepsClamp("), "honest clamp helper");
assert.ok(source.includes("schnell 上限"), "hint copy schnell 上限");
assert.ok(source.includes("已从原帖 "), "hint copy 已从原帖");
assert.ok(source.includes("→"), "hint arrow 20→12");
assert.ok(source.includes("never silent"), "documents never silent");
assert.ok(source.includes("honestFalSchnellStepsClamp()"), "clamp invoked");

// --- BE: official max stamped; reject over-max (no silent clamp) ---
assert.ok(falPy.includes("FAL_OPENAPI_STEPS_MAX"), "FAL_OPENAPI_STEPS_MAX map");
assert.ok(falPy.includes('"fal-ai/flux/schnell": 12'), "schnell max 12 from OpenAPI");
assert.ok(falPy.includes("fal_openapi_steps_max"), "steps max helper");
assert.ok(falPy.includes("拒绝静默截断"), "BE rejects silent clamp");
assert.ok(capsPy.includes("stepsMax") || falPy.includes('caps["stepsMax"]'), "catalog stamps stepsMax");

// --- Runtime: clamp helper updates #steps + hint ---
function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "seam " + from.slice(0, 40));
  return source.slice(start, end);
}
const clampSrc = section(
  "  function falStepsMax() {",
  "  function parseNanoSizeToken(token) {"
);
const sandbox = {
  console,
  Number,
  String,
  parseInt,
  Math,
  Object,
  Array,
  RegExp,
  document: { getElementById: () => null },
};
vm.createContext(sandbox);
// Provide $ / currentBackend / catalogCaps / setParamWarn / catalogItemForService
const els = {
  steps: { value: "20" },
  service: { value: "fal-ai/flux/schnell" },
  backend: { value: "fal" },
};
sandbox.$ = (id) => els[id] || null;
sandbox.currentBackend = () => "fal";
sandbox.catalogCaps = () => ({ stepsMax: 12 });
sandbox.catalogItemForService = () => ({ id: "fal-ai/flux/schnell", stepsMax: 12 });
sandbox.setParamWarn = (msg, on) => { sandbox._warn = { msg, on }; };
vm.runInContext(clampSrc + "\nthis.falStepsMax = falStepsMax;\nthis.honestFalSchnellStepsClamp = honestFalSchnellStepsClamp;\n", sandbox, { filename: "o151-clamp.vm.js" });
assert.equal(sandbox.falStepsMax(), 12, "stepsMax 12");
const hint = sandbox.honestFalSchnellStepsClamp();
assert.equal(els.steps.value, "12", "UI #steps updated to 12");
assert.ok(/schnell 上限 12/.test(hint), "hint has schnell 上限 12: " + hint);
assert.ok(/已从原帖 20→12/.test(hint), "hint has 20→12: " + hint);
assert.ok(sandbox._warn && sandbox._warn.on, "setParamWarn called");

// no-op when already ≤ max
els.steps.value = "8";
assert.equal(sandbox.honestFalSchnellStepsClamp(), "", "no clamp when ≤ max");
assert.equal(els.steps.value, "8");

// --- Python: build_fal_input keeps 12; rejects 20 ---
const py = `
from providers.fal import build_fal_input, fal_openapi_steps_max, overlay_image_fields, find_model
assert fal_openapi_steps_max("fal-ai/flux/schnell") == 12
assert fal_openapi_steps_max("fal-ai/flux/dev") is None
row = overlay_image_fields(dict(find_model("fal-ai/flux/schnell") or {"id": "fal-ai/flux/schnell"}))
assert (row.get("capabilities") or {}).get("stepsMax") == 12 or row.get("stepsMax") == 12, row
ok = build_fal_input({
    "serviceId": "fal-ai/flux/schnell",
    "prompt": "x",
    "steps": 12,
    "width": 832,
    "height": 1216,
})
assert ok.get("num_inference_steps") == 12, ok
try:
    build_fal_input({
        "serviceId": "fal-ai/flux/schnell",
        "prompt": "x",
        "steps": 20,
        "width": 832,
        "height": 1216,
    })
except ValueError as e:
    msg = str(e)
    assert "12" in msg and "20" in msg and "静默" in msg, msg
else:
    raise SystemExit("expected ValueError for steps=20")
print("py-ok")
`;
const r = spawnSync("python3", ["-c", py], { cwd: root, encoding: "utf8" });
assert.equal(r.status, 0, "python o151 failed: " + (r.stderr || r.stdout));
assert.ok((r.stdout || "").includes("py-ok"), "python ok");

console.log("PASS o151_fal_schnell_steps_no_silent_clamp");
