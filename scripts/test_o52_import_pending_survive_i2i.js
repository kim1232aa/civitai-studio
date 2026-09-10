#!/usr/bin/env node
/** o52: loadCatalog re-injects _pendingService from official roster after i2i filter. */
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");
assert.ok(html.includes("v0821o52-import-pending-survive-i2i"), "html stamp");
assert.ok(html.includes("20260911-o52importpendingsurvivei2i"), "cache bust");
assert.ok(js.includes("v0821o52-import-pending-survive-i2i") || js.includes("o52: import _pendingService"), "js tip");
const load = js.slice(js.indexOf("function loadCatalog"), js.indexOf("function loadCatalog") + 4500);
assert.ok(load.includes("filterCatalogForMode"), "filters");
assert.ok(load.includes("state._pendingService"), "pending");
assert.ok(load.includes("roster.find"), "reinject from roster");
assert.ok(load.includes("never invent") || load.includes("official roster"), "roster-only reinject");
const fi = load.indexOf("filterCatalogForMode");
const ri = load.indexOf("roster.find");
assert.ok(fi >= 0 && ri > fi, "filter then reinject");
console.log("PASS o52_import_pending_survive_i2i");
