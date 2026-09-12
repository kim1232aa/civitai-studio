#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");
const pinCss = fs.readFileSync(path.join(root, "static/o97-dock-pin.css"), "utf8");
const shell = fs.readFileSync(path.join(root, "static/storyboard-shell.css"), "utf8");

assert.ok(js.includes("v0821o98-capsule-fit") || js.includes("v0821o101-shell") || js.includes("v0821o102-seko") || js.includes("v0821o103-wide-desk") || js.includes("v0821o104-seko-attach") || js.includes("v0821o105-adapt") || js.includes("v0821o106-drag") || js.includes("v0821o107-wires"), "js stamp");
assert.ok(html.includes("o98capsulefit") || html.includes("o101shell") || html.includes("o102seko") || html.includes("o103wide") || html.includes("o104attach") || html.includes("o105adapt") || html.includes("o106drag") || html.includes("o107wires"), "html stamp");
assert.ok(!/dockTitle"\)\.textContent = .*\(胶囊\)/.test(js), "title does not append 胶囊");
assert.ok(!/Math\.min\(420, Math\.max\(300, nw\)\)/.test(js), "420 island gone from positionDock");
assert.ok(adapt.includes("white-space: nowrap") || adapt.includes("white-space:nowrap") || shell.includes("white-space: nowrap"), "expand nowrap");
assert.ok(adapt.includes("text-overflow: ellipsis") || shell.includes("text-overflow: ellipsis"), "title ellipsis");
assert.ok(adapt.includes("collapsed #paramWarn") || adapt.includes("#paramWarn") || shell.includes("collapsed #paramWarn"), "hide catalog warn in collapsed");
assert.ok(o67.includes("Never sit beside") || o67.includes("bottom desk") || o67.includes("bottom\", \"12px\""), "pin stays off neighboring shots");
assert.ok(!/cands\.push\(\{ left: x \+ nw \+ gap/.test(o67), "collapsed pin does not prefer neighbor side");
assert.ok(pinCss.includes("white-space: nowrap") || pinCss.includes("white-space:nowrap") || shell.includes("white-space: nowrap"), "pin css nowrap");
assert.ok(html.includes(">展开<"), "expand label is one word");
console.log("PASS o98_capsule_fit.js");
