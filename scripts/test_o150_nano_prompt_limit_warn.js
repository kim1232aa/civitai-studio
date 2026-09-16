#!/usr/bin/env node
/** o150: Nano prompt limit — live 上限/剩余/超 N 字; ↑ blocks; never silent truncate. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const indexHtml = fs.readFileSync(path.join(root, "static/index.html"), "utf8");
const nanoPy = fs.readFileSync(path.join(root, "providers/nanogpt.py"), "utf8");
const capsPy = fs.readFileSync(path.join(root, "providers/six_catalog_caps.py"), "utf8");

// --- stamp + cache bust ---
assert.ok(source.includes("v0821o150-nano-prompt-limit-warn"), "js stamp");
assert.ok(html.includes("v0821o150-nano-prompt-limit-warn") || html.includes("v0821o151-fal-schnell-steps-honest") || html.includes("v0821o151b-fal-steps-hint-sticky") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o151-fal-schnell-steps-honest") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("o152nano"), "html stamp o150 or successor");
assert.ok(/storyboard\.js\?v=o150nano|storyboard\.js\?v=o151bsticky|storyboard\.js\?v=o152nano|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o151fal|storyboard\.js\?v=o152nano|storyboard\.js\?v=o153writeback/.test(html), "cache bust o150 or successor");
assert.ok(html.includes('id="nanoPromptCount"'), "live counter element");

// --- UI: live remaining / over-by-N; block ↑; never truncate ---
assert.ok(source.includes("NANO_PROMPT_MAX_MEASURED = 400"), "measured 400");
assert.ok(source.includes("nanoPromptCountLabel"), "count label helper");
assert.ok(source.includes("超 ") && source.includes(" 字"), "超 N 字 copy");
assert.ok(source.includes("剩余 "), "remaining copy");
assert.ok(source.includes("请缩短后再生成"), "visible block copy");
assert.ok(source.includes("never slice outbound prompt") || source.includes("Never silent-truncate") || source.includes("never silent truncate"), "documents no truncate");
assert.ok(!/payload\.prompt\s*=\s*.*\.slice\(/.test(source), "FE must not slice outbound prompt");
assert.ok(!source.includes("truncateNanoPrompt"), "no composer truncate helper");

assert.ok(!indexHtml.includes("截断到 1200"), "配方台 no truncate-to-1200");
assert.ok(!indexHtml.includes("truncateNanoPrompt"), "配方台 no truncate helper");
assert.ok(!indexHtml.includes("NANO_PROMPT_MAX = 1200"), "配方台 not invented 1200");
assert.ok(indexHtml.includes("NANO_PROMPT_MAX = 400"), "配方台 measured 400");
assert.ok(indexHtml.includes("超 ") && indexHtml.includes(" 字"), "配方台 超 N 字");

assert.ok(nanoPy.includes("NANO_PROMPT_MAX = 400"), "adapter measured 400");
assert.ok(!nanoPy.includes("NANO_PROMPT_MAX = 1200"), "adapter not invented 1200");
assert.ok(nanoPy.includes("Never silent-truncate") || nanoPy.includes("never silent-truncate") || nanoPy.includes("Never silent-truncate"), "adapter documents no truncate");
assert.ok(capsPy.includes("nano_prompt_max_from_row"), "catalog metadata helper");
assert.ok(capsPy.includes("Never invent 1200"), "overlay must not invent 1200");

// --- Python: metadata wins; measured 400; _image_body never slices ---
const py = `
from providers.nanogpt import prompt_length_error, NANO_PROMPT_MAX, _image_body
from providers.six_catalog_caps import nano_prompt_max_from_row, overlay_nano_catalog_item
assert NANO_PROMPT_MAX == 400
assert prompt_length_error("ok") is None
assert prompt_length_error("x" * 400) is None
too = prompt_length_error("y" * 401)
assert too and too["code"] == "prompt_too_long" and too["max"] == 400
assert too["over"] == 1
assert "超 1 字" in too["error"]
too1855 = prompt_length_error("z" * 1855)
assert too1855["length"] == 1855 and too1855["over"] == 1455
spec512 = {"description": "Prompts are limited to 512 characters; negative prompts have the same limit."}
assert nano_prompt_max_from_row(spec512) == 512
assert prompt_length_error("a" * 512, spec512) is None
assert prompt_length_error("a" * 513, spec512)["max"] == 512
spec800 = {"supported_parameters": {"max_chars": 800}}
assert nano_prompt_max_from_row(spec800) == 800
hidream = overlay_nano_catalog_item({"id": "hidream", "supported_parameters": {"resolutions": ["1024x1024"]}})
assert "promptMax" not in (hidream.get("capabilities") or {}), hidream
step = overlay_nano_catalog_item({
    "id": "step-image-edit-2",
    "description": "Prompts are limited to 512 characters; negative prompts have the same limit.",
})
assert step["capabilities"]["promptMax"] == 512
long_p = "q" * 401
body = _image_body({"prompt": long_p, "serviceId": "hidream", "quantity": 1}, {"id": "hidream", "supported_parameters": {"resolutions": ["1k"]}})
assert body["prompt"] == long_p, "outbound must send full prompt, never slice"
print("py-ok")
`;
const r = spawnSync("python3", ["-c", py], { cwd: root, encoding: "utf8" });
assert.equal(r.status, 0, "python o150 failed: " + (r.stderr || r.stdout));
assert.ok((r.stdout || "").includes("py-ok"), "python ok marker");

// generate() fail-closed locally for 1855
const pyGen = `
from unittest.mock import patch
from providers.nanogpt import NanoGptProvider
prov = NanoGptProvider()
with patch("providers.nanogpt.nano_key", return_value="test-key"):
    with patch("providers.nanogpt.find_spec", return_value={
        "id": "z-image-turbo-lora",
        "category": "image",
        "supported_parameters": {"resolutions": ["1k"]},
        "capabilities": {},
    }):
        with patch("providers.nanogpt.json_call", return_value=(502, {"error": "offline"})) as jc:
            code, body = prov.generate({
                "serviceId": "z-image-turbo-lora",
                "prompt": "z" * 1855,
                "resolution": "1k",
            })
            assert not jc.called, "must not POST truncated/full over-limit prompt"
            assert code == 400 and body.get("code") == "prompt_too_long", body
            assert "1855/400" in body["error"] and "超 1455 字" in body["error"]
print("gen-ok")
`;
const r2 = spawnSync("python3", ["-c", pyGen], { cwd: root, encoding: "utf8" });
assert.equal(r2.status, 0, "generate fail-closed failed: " + (r2.stderr || r2.stdout));
assert.ok((r2.stdout || "").includes("gen-ok"), "gen ok marker");

console.log("PASS o150_nano_prompt_limit_warn");
