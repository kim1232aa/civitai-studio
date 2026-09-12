#!/usr/bin/env node
/** o91: Seko tools on select, capsule composer, no 1x1 gallery. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/o76-dock-right.css"), "utf8");

assert.ok(js.includes("v0821o91-seko-tools"), "js stamp");
assert.ok(html.includes("o91sekotools") || html.includes("v0821o91-seko-tools"), "html stamp");
assert.ok(html.includes("九宫格"), "nine grid");
assert.ok(html.includes("故事推演"), "story");
assert.ok(html.includes("局部摘取"), "crop");
assert.ok(html.includes("空白节点"), "blank node");
assert.ok(html.includes("上传本地文件"), "upload");
assert.ok(html.includes('href="/index.html"'), "配方台 not deleted");
assert.ok(js.includes("function nineGridFromShot"), "nine fn");
assert.ok(js.includes("function storyAdvanceFromShot"), "story fn");
assert.ok(js.includes("function addBlankShot"), "add blank");
assert.ok(js.includes("data-editor-track"), "editor tracks");
assert.ok(js.includes("配音"), "voice track copy in js");
assert.ok(!css.includes("right: 16px !important"), "capsule not right inspector");
assert.ok(js.includes("不会自动生成"), "story does not auto generate");
console.log("PASS o91_seko_tools.js");
