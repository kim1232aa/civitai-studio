#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const pin = fs.readFileSync(path.join(root, "static/o97-dock-pin.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/o97-dock-pin.css"), "utf8");
assert.ok(pin.includes("v0821o97-dock-pin"), "stamp");
assert.ok(pin.includes("胶囊"), "strips 胶囊");
assert.ok(pin.includes("nh < 220") || pin.includes("preferSide"), "short card goes right");
assert.ok(html.includes("o97-dock-pin.js"), "html loads pin");
assert.ok(html.includes("o97-dock-pin.css"), "html loads css");
assert.ok(css.includes("max-width: 280px"), "collapsed max 280");
console.log("PASS o97_dock_pin.js");
