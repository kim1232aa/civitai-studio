#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8");
const o67 = fs.readFileSync(path.join(root, "static/o67-human-copy.js"), "utf8");
assert.ok(js.includes("v0821o96-expand-clean") || js.includes("v0821o100-desk"), "stamp");
assert.ok(js.includes("area.bottom") && js.includes("hitsCard") || js.includes("top = y + nh + gap") || js.includes("bottom desk"), "expanded desk or below");
assert.ok(adapt.includes("dock.show #sendCap") || adapt.includes(".dock.show.expanded #sendCap"), "send in header");
assert.ok(adapt.includes("dock.show.expanded #send") || adapt.includes("dock.expanded #send"), "bar send hidden");
assert.ok(!/position:\s*sticky\s*!important/.test(adapt), "sticky send gone");
assert.ok(o67.includes('el.id === "loraQLbl"'), "o67 does not clone LoRA hint onto label");
console.log("PASS o96_expand_clean.js");
