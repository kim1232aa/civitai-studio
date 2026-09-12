#!/usr/bin/env node
/** o92: 打光/换机位/超清/消除/文生视频/尾帧 — rematch, no auto generate. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

assert.ok(js.includes("v0821o92-seko-fill"), "js stamp");
assert.ok(html.includes("o92sekofill") || html.includes("v0821o92-seko-fill"), "html stamp");
assert.ok(html.includes("打光"), "light tool");
assert.ok(html.includes("换机位"), "camera tool");
assert.ok(html.includes("超清"), "upscale tool");
assert.ok(html.includes("消除"), "erase tool");
assert.ok(html.includes("文生视频"), "t2v tool");
assert.ok(html.includes("尾帧"), "last frame tool");
assert.ok(html.includes('id="btnSkill"'), "skill visible");
assert.ok(!html.includes('id="btnSkill" title="快捷指令" hidden'), "skill not hidden");
assert.ok(js.includes("function catalogItemSupportsT2v"), "t2v detector");
assert.ok(js.includes("function catalogItemSupportsUpscale"), "upscale detector");
assert.ok(js.includes("function catalogItemSupportsInpaint"), "inpaint detector");
assert.ok(js.includes("function spawnLinkedShot"), "spawn helper");
assert.ok(js.includes("function lastFrameAsset"), "last frame");
assert.ok(js.includes("LIGHT_PRESETS"), "light presets");
assert.ok(js.includes("CAMERA_PRESETS"), "camera presets");
assert.ok(js.includes('t2v: ["video/wan/v2.2/fal/text-to-video"'), "civitai t2v pref");
assert.ok(js.includes('t2v: ["fal-ai/kling-video/v3/pro/text-to-video"'), "fal t2v pref");
assert.ok(js.includes("fal-ai/esrgan"), "fal upscale pref");
assert.ok(js.includes("fal-ai/bria/eraser"), "fal erase pref");
assert.ok(js.includes('opVid === "t2v"'), "t2v send path");
assert.ok(js.includes("不会自动生成"), "no auto gen copy");
assert.ok(!/function (?:lightFromShot|upscaleFromShot|t2vFromShot|finishErase)[\s\S]{0,1200}fetch\("\/api\/generate"/.test(js), "tools must not POST generate");
assert.ok(js.includes("if (!shot || !frameAsset(shot)"), "video no-frame/no-shot is t2v");
assert.ok(js.includes("payload.lastFrame"), "pack last frame");
assert.ok(js.includes("payload.mask_url"), "pack mask");
assert.ok(css.includes("light-pop"), "light pop css");
assert.ok(css.includes("erase-cv"), "erase canvas css");
assert.ok(html.includes('href="/index.html"'), "配方台 stays");
console.log("PASS o92_seko_fill.js");
