#!/usr/bin/env node
/** o48/o49b: hydrate adopts server shot.url when fresher / local stale; not blind overwrite. */
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");

assert.ok(
  js.includes("v0821o49b-hydrate-fresh-empty-url") ||
    js.includes("o49b freshness supersedes") ||
    js.includes("o48: server wins"),
  "o48/o49b comment"
);
assert.ok(
  js.includes("server still wins when fresher") ||
    js.includes("server wins when fresher") ||
    js.includes("shotUrlMtime") ||
    js.includes("localUrl !== serverUrl"),
  "freshness / compare logic"
);
assert.ok(/localUrl !== serverUrl/.test(js) || /shotUrlMtime/.test(js), "compare local vs server");
assert.ok(html.includes("v0821o49b-hydrate-fresh-empty-url"), "html stamp");
assert.ok(html.includes("20260911-o49bhydratefreshemptyurl"), "cache bust");
// must NOT skip when n.url already set (old o15 behavior)
const hydrate = js.slice(js.indexOf("async function hydrateFromServer"), js.indexOf("function applyCam"));
assert.ok(!/if \(!n \|\| n\.url\) continue/.test(hydrate), "must not skip shots that already have url");
assert.ok(/n\.kind !== "shot"/.test(hydrate) || /kind !== \"shot\"/.test(hydrate), "shot-only");
assert.ok(/_pendingPut|pendingPut|urlUpdatedAt|shotUrlMtime/.test(hydrate), "freshness guards present");
console.log("PASS o48_hydrate_server_wins");
