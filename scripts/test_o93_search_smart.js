#!/usr/bin/env node
/** o93: layout drawer + smart match uses /api/search MODEL cross. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");
const mgr = fs.readFileSync(path.join(root, "static/canvas_manager.js"), "utf8");
const py = fs.readFileSync(path.join(root, "providers/catalog_search.py"), "utf8");
const srv = fs.readFileSync(path.join(root, "server.py"), "utf8");

assert.ok(js.includes("v0821o93-search-match"), "js stamp");
assert.ok(html.includes("o93searchmatch"), "html stamp");
assert.ok(css.includes(".canvas-manager"), "manager css");
assert.ok(css.includes(".canvas-manager.show"), "manager show");
assert.ok(css.includes("max-height: 96px") || css.includes("max-height:96px"), "collapsed capsule");
assert.ok(js.includes("function searchModelsForOp"), "search helper");
assert.ok(js.includes('type: "MODEL"'), "MODEL search");
assert.ok(js.includes("cross: cross ? \"1\" : \"0\""), "cross flag");
assert.ok(js.includes("跨家搜到"), "cross copy");
assert.ok(js.includes('else if (opts.expand)'), "click does not auto-expand");
assert.ok(!js.includes("opts.expand || !opts.keepClosed"), "old auto-expand gone");
assert.ok(!/always 锚底/.test(js), "no bottom-anchor dock");
assert.ok(py.includes("def search_models_cross"), "py cross");
assert.ok(py.includes("def search_models_one"), "py one");
assert.ok(srv.includes("search_models_cross"), "server wires MODEL");
assert.ok(!mgr.includes("target.classList.add(\"show\")") || mgr.indexOf("rememberedWorkspace !== \"canvas\"") < 0, "no auto-open panel");
assert.ok(!/cm-tabs[\s\S]{0,80}剧本策划/.test(mgr), "no duplicate workspace tabs in panel");
console.log("PASS o93_search_smart.js");
