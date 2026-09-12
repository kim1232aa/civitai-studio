#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8");
const pinCss = fs.readFileSync(path.join(root, "static/o97-dock-pin.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");
const ui = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");
const mgr = fs.readFileSync(path.join(root, "static/canvas_manager.js"), "utf8");
const shell = fs.readFileSync(path.join(root, "static/storyboard-shell.css"), "utf8");

assert.ok(js.includes("v0821o99-capsule-row") || js.includes("v0821o101-shell") || js.includes("v0821o100-desk") || js.includes("v0821o102-seko") || js.includes("v0821o103-wide-desk") || js.includes("v0821o104-seko-attach") || js.includes("v0821o105-adapt") || js.includes("v0821o106-drag") || js.includes("v0821o107-wires") || js.includes("v0821o108-unhide") || js.includes("v0821o109-room"), "js stamp");
assert.ok(html.includes("o99capsulerow") || html.includes("o101shell") || html.includes("o102seko") || html.includes("o103wide") || html.includes("o104attach") || html.includes("o105adapt") || html.includes("o106drag") || html.includes("o107wires") || html.includes("o108unhide") || html.includes("o109room"), "html stamp");
assert.ok(js.includes('classList.contains("tools")'), "canvasArea only tools as left wall");
assert.ok(js.includes("area.bottom - top"), "expanded height uses remaining viewport");
assert.ok(!pinCss.includes(".dock.show.collapsed .bar"), "pin css no longer hides collapsed bar");
assert.ok(adapt.includes("collapsed #backend") || shell.includes("collapsed #backend"), "capsule shows house");
assert.ok(ui.includes(".port.in"), "ports are visible dots");
assert.ok(!/slice\(0,\s*8\)/.test(mgr) || !mgr.includes("${name} · ${short}"), "project title has no hash suffix");
assert.ok(o67.includes("v0821o99-capsule-row") || o67.includes("v0821o100-desk") || o67.includes("v0821o101-shell") || o67.includes("v0821o102-seko") || o67.includes("v0821o103-wide-desk") || o67.includes("v0821o104-seko-attach") || o67.includes("v0821o105-adapt") || o67.includes("v0821o106-drag") || o67.includes("v0821o107-wires") || o67.includes("v0821o108-unhide") || o67.includes("v0821o109-room"), "o67 stamp");
console.log("PASS o99_capsule_row.js");
