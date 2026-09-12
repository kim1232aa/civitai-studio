#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");
const mgr = fs.readFileSync(path.join(root, "static/canvas_manager.js"), "utf8");

assert.ok(js.includes("v0821o95-stage-first") || js.includes("v0821o96-expand-clean") || js.includes("v0821o101-shell"), "stamp");
assert.ok(html.includes("o95stagefirst"), "html stamp");
assert.ok(adapt.includes("dock.show.collapsed #prompt"), "collapsed keeps prompt");
assert.ok(!adapt.includes("height: 52px !important"), "old 52px capsule gone");
assert.ok(adapt.includes("collapsed #backend"), "capsule shows house");
assert.ok(css.includes("right: 16px"), "project drawer right");
assert.ok(!o67.includes('title.textContent = "未命名画布"') || o67.includes("Keep the live project name"), "o67 does not wipe qa- title");
assert.ok(js.includes("fromShots") || js.includes('title: (s.title || "成片")'), "rail lists shot results");
assert.ok(html.includes(">摘取<") && html.includes(">九宫<"), "short tool labels");
assert.ok(mgr.includes("点「入库」收入本项目") || mgr.includes("点入库后出现在这里"), "honest empty assets");
console.log("PASS o95_stage_first.js");
