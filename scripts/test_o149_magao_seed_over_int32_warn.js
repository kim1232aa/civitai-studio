#!/usr/bin/env node
/** o149: Magao over-int32 seed — keep real value +「超魔搭区间」; outbound omit; never silent -1 / wrap. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.js"), "utf8");
const seedPy = fs.readFileSync(path.join(root, "providers/modelscope_seed.py"), "utf8");
const msPy = fs.readFileSync(path.join(root, "providers/modelscope.py"), "utf8");

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o149b-magao-seed-warn-not-block"), "js stamp");
assert.ok(html.includes("v0821o149b-magao-seed-warn-not-block") || html.includes("v0821o150-nano-prompt-limit-warn") || html.includes("v0821o151-fal-schnell-steps-honest") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("o152nano"), "html stamp o149 or successor");
assert.ok(/storyboard\.js\?v=o149bseed|storyboard\.js\?v=o150nano|storyboard\.js\?v=o151fal|storyboard\.js\?v=o152nano/.test(html), "cache bust o149 or successor");

// --- UI must explicitly show 超魔搭区间; never silent -1 rewrite ---
assert.ok(source.includes("超魔搭区间"), "UI note 超魔搭区间");
assert.ok(source.includes("magaoSeedWarn"), "magaoSeedWarn warn-only path");
assert.ok(source.includes("MUST NOT block"), "documents warn-not-block");
assert.ok(source.includes("if (over && note && !magaoSeed) msgs.push(note)"), "Magao over not msgs.push");

assert.ok(source.includes("Never rewrite the input to -1") || source.includes("never silent -1"),
  "documents no silent -1 rewrite");
assert.ok(source.includes("MAGAO_SEED_MAX = 2147483647"), "Magao int32 max const");
assert.ok(adapt.includes("超魔搭区间"), "adapt hint mentions 超魔搭区间");

// --- Outbound Magao omit over-int32 (FE + BE) ---
assert.ok(source.includes("magaoOut && seedNum > 2147483647) delete payload.seed"),
  "FE Magao outbound deletes over-int32 seed");
assert.ok(msPy.includes("official_seed_outbound"), "modelscope._image_body uses official_seed_outbound");
assert.ok(seedPy.includes("over-int32") || seedPy.includes("o149"), "modelscope_seed o149 omit");

// --- Python: over-int32 → None (omit), in-range kept, -1 omit, no wrap ---
const py = `
from providers.modelscope_seed import official_seed_outbound, strip_unofficial_seed
assert official_seed_outbound(42) == 42
assert official_seed_outbound(2147483647) == 2147483647
assert official_seed_outbound(-1) is None
assert official_seed_outbound("random") is None
assert official_seed_outbound(2147483648) is None
assert official_seed_outbound(4294967295) is None
assert official_seed_outbound(475720515768790) is None
body = strip_unofficial_seed({"prompt": "a", "seed": 4294967295})
assert "seed" not in body
body2 = strip_unofficial_seed({"prompt": "a", "seed": 7})
assert body2.get("seed") == 7
print("py-ok")
`;
const r = spawnSync("python3", ["-c", py], { cwd: root, encoding: "utf8" });
assert.equal(r.status, 0, "python seed omit failed: " + (r.stderr || r.stdout));
assert.ok((r.stdout || "").includes("py-ok"), "python ok marker");

// --- _image_body omits over-int32 without wrapping ---
const pyBody = `
from providers.modelscope import _image_body
body = _image_body({"prompt": "x", "seed": 4294967295}, "Tongyi-MAI/Z-Image-Turbo", "modelscope-ai")
assert "seed" not in body, body
body2 = _image_body({"prompt": "x", "seed": 42}, "Tongyi-MAI/Z-Image-Turbo", "modelscope-ai")
assert body2.get("seed") == 42, body2
body3 = _image_body({"prompt": "x", "seed": -1}, "Tongyi-MAI/Z-Image-Turbo", "modelscope-ai")
assert "seed" not in body3, body3
print("body-ok")
`;
const r2 = spawnSync("python3", ["-c", pyBody], { cwd: root, encoding: "utf8" });
assert.equal(r2.status, 0, "image_body omit failed: " + (r2.stderr || r2.stdout));
assert.ok((r2.stdout || "").includes("body-ok"), "body ok marker");

console.log("PASS o149_magao_seed_over_int32_warn");
