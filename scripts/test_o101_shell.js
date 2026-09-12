#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const shell = fs.readFileSync(path.join(root, "static/storyboard-shell.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");

assert.ok(js.includes("v0821o101-shell") || js.includes("v0821o102-seko") || js.includes("v0821o103-wide-desk") || js.includes("v0821o104-seko-attach") || js.includes("v0821o105-adapt") || js.includes("v0821o106-drag") || js.includes("v0821o107-wires") || js.includes("v0821o108-unhide") || js.includes("v0821o109-room") || js.includes("v0821o110-ws") || js.includes("v0821o112-attach"), "js stamp");
assert.ok(html.includes("o101shell") || html.includes("o102seko") || html.includes("o103wide") || html.includes("o104attach") || html.includes("o105adapt") || html.includes("o106drag") || html.includes("o107wires") || html.includes("o108unhide") || html.includes("o109room") || html.includes("o110ws") || html.includes("o112attach"), "html stamp");
assert.ok(html.includes("storyboard-shell.css"), "shell css linked");
assert.ok(shell.includes("bottom: 12px") || shell.includes("480px"), "composer capsule or desk");
assert.ok(shell.includes(".rail"), "rail parked");
assert.ok(o67.includes("bottom\", \"12px\"") || o67.includes("v0821o102-seko") || o67.includes("v0821o103-wide-desk") || o67.includes("v0821o104-seko-attach") || o67.includes("v0821o105-adapt") || o67.includes("v0821o106-drag") || o67.includes("v0821o107-wires") || o67.includes("v0821o108-unhide") || o67.includes("v0821o109-room") || o67.includes("v0821o110-ws") || o67.includes("v0821o112-attach"), "pin is desk or seko capsule");
assert.ok(!/top = y \+ Math.max\(36, nh - 108\)/.test(js), "no on-card overlay");
assert.ok(js.includes("bottom desk") || js.includes("fallback bottom desk"), "positionDock has desk fallback");
assert.ok(html.includes(">文本<") && html.includes(">图片<") && html.includes(">视频<") && html.includes(">音频<"), "short mode pills");
assert.ok(html.includes(">展开<"), "expand is one word");
assert.ok(js.includes('data-node-act="more"'), "extra tools live on the card");
assert.ok(shell.includes(".tools.has-shot .node-only"), "left rail parks node-only pile");
assert.ok(shell.includes(".chip img") || shell.includes(".chip img,"), "ref chips stay small");
console.log("PASS o101_shell.js");
