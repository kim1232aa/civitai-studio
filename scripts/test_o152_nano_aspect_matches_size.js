#!/usr/bin/env node
/** o152: Nano aspect_ratio must match size / UI w×h — never invent 1:1 when size is portrait. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const nanoPy = fs.readFileSync(path.join(root, "providers/nanogpt.py"), "utf8");

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o152-nano-aspect-matches-size"), "js stamp o152");
assert.ok(html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card"), "html stamp o152");
assert.ok(/storyboard\.js\?v=o152nano|storyboard\.js\?v=o153writeback/.test(html), "cache bust o152nano");

// --- FE: pack aspect with nano resolution token ---
assert.ok(source.includes("o152: keep size token"), "nano buildGraph o152 comment");
assert.ok(source.includes("genParams.aspectRatio = aspectNow"), "always pack aspectRatio");
assert.ok(source.includes("function parseNanoSizeToken("), "parseNanoSizeToken");
assert.ok(source.includes("function syncNanoResFromSize("), "syncNanoResFromSize");
assert.ok(source.includes("syncAspectFromNanoToken"), "syncAspectFromNanoToken");
assert.ok(!/closest_aspect\(w or 1024/.test(nanoPy), "BE must not invent closest_aspect(1024)");

// --- Python: token-only 720*1280 → aspect 9:16 (not 1:1); UI aspect wins; 1k omits ---
const py = `
from providers.nanogpt import _image_body, _wh_from_size_token, closest_aspect
assert _wh_from_size_token("720*1280") == (720, 1280)
assert _wh_from_size_token("1k") == (None, None)
assert closest_aspect(768, 1344) == "9:16"
assert closest_aspect(720, 1280) == "9:16"
spec = {"id": "z-image-turbo", "supported_parameters": {"resolutions": [
    "256*256","512*512","768*768","1024*1024","1280*720","720*1280","1536*1024","1024*1536","1536*1536"
]}}
# Bug repro: resolution token only used to invent aspect_ratio=1:1 via closest_aspect(1024,1024)
body = _image_body({"prompt": "x", "serviceId": "z-image-turbo", "resolution": "720*1280"}, spec)
assert body.get("size") == "720*1280" or body.get("resolution") == "720*1280", body
assert body.get("aspect_ratio") == "9:16", body
# UI 768×1344 + aspect 9:16 + preferred portrait token
body2 = _image_body({
    "prompt": "x", "serviceId": "z-image-turbo",
    "resolution": "720*1280", "width": 768, "height": 1344, "aspectRatio": "9:16",
}, spec)
assert body2.get("aspect_ratio") == "9:16", body2
assert body2.get("size") == "720*1280"
# exact catalog WxH
body3 = _image_body({
    "prompt": "x", "serviceId": "z-image-turbo",
    "width": 720, "height": 1280,
}, spec)
assert body3.get("size") == "720*1280"
assert body3.get("aspect_ratio") == "9:16"
# non-pixel token: omit aspect (do not invent 1:1)
body4 = _image_body({"prompt": "x", "serviceId": "x", "resolution": "1k"}, {
    "id": "x", "supported_parameters": {"resolutions": ["1k", "2k"]},
})
assert body4.get("size") == "1k"
assert "aspect_ratio" not in body4, body4
print("py-ok")
`;
const r = spawnSync("python3", ["-c", py], { cwd: root, encoding: "utf8" });
assert.equal(r.status, 0, "python o152 failed: " + (r.stderr || r.stdout));
assert.ok((r.stdout || "").includes("py-ok"), "python ok");

console.log("PASS o152_nano_aspect_matches_size");
