#!/usr/bin/env node
/** o93/o94: layout drawer + capsule-on-node; smart match uses /api/search MODEL cross. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");
const adapt = fs.readFileSync(path.join(root, "static/composer-field-adapt.css"), "utf8");
const mgr = fs.readFileSync(path.join(root, "static/canvas_manager.js"), "utf8");
const py = fs.readFileSync(path.join(root, "providers/catalog_search.py"), "utf8");
const srv = fs.readFileSync(path.join(root, "server.py"), "utf8");

assert.ok(js.includes("v0821o93-search-match") || js.includes("v0821o94-cap-on-node") || js.includes("v0821o95-stage-first") || js.includes("v0821o96-expand-clean"), "js stamp");
assert.ok(html.includes("o93searchmatch") || html.includes("o94caponnode") || html.includes("o95stagefirst"), "html stamp");
assert.ok(css.includes(".canvas-manager"), "manager css");
assert.ok(css.includes(".canvas-manager.show"), "manager show");
assert.ok(js.includes("function searchModelsForOp"), "search helper");
assert.ok(js.includes('type: "MODEL"'), "MODEL search");
assert.ok(js.includes("跨家搜到"), "cross copy");
// o93 intent: search/smart-match clicks must not yank the composer open.
// o103-wide-desk superseded the old selectNode(opts.expand) shape; assert the semantic contract instead:
// the smart-match code path never flips dockMode / setDockMode itself.
{
  const smStart = js.indexOf("async function smartMatchService");
  assert.ok(smStart >= 0, "smartMatchService exists");
  const smEnd = js.indexOf("\n  async function", smStart + 10);
  const smBody = js.slice(smStart, smEnd > smStart ? smEnd : undefined);
  assert.ok(!smBody.includes('dockMode = "expanded"') && !smBody.includes('setDockMode("expanded")'), "click does not auto-expand");
}
assert.ok(!js.includes("opts.expand || !opts.keepClosed"), "old auto-expand gone");
assert.ok(py.includes("def search_models_cross"), "py cross");
assert.ok(srv.includes("search_models_cross"), "server wires MODEL");
assert.ok(mgr.indexOf("rememberedWorkspace !== \"canvas\"") < 0, "no auto-open panel");
assert.ok(!/position:\s*fixed\s*!important/.test(adapt), "o60 fixed bar gone");
assert.ok(!/(?<!max-)width:\s*min\(720px/.test(adapt), "o60 720 bar gone");
assert.ok(adapt.includes("dock:not(.show)"), "dock hidden until show");
assert.ok(html.includes('id="sendCap"'), "capsule send");
// js o94/o95 stamps were superseded by later refactors (o100-desk…o136seko); assert the FEATURE persists instead.
assert.ok(js.includes("sendCap"), "js o94 send capsule wired");
console.log("PASS o93_search_smart.js");
