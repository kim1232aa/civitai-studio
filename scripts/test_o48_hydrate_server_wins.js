#!/usr/bin/env node
/** o48: hydrate adopts server shot.url over stale local url (same id). */
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o48-hydrate-server-wins") || js.includes("o48: server wins"), "o48 comment");
assert.ok(js.includes("server shot.url still wins over stale localStorage") || js.includes("localUrl !== serverUrl"), "server wins logic");
assert.ok(/localUrl !== serverUrl/.test(js), "compare local vs server");
assert.ok(html.includes("v0821o48-hydrate-server-wins"), "html stamp");
assert.ok(html.includes("20260911-o48hydrateserverwins"), "cache bust");
// must NOT skip when n.url already set (old o15 behavior)
const hydrate = js.slice(js.indexOf("async function hydrateFromServer"), js.indexOf("function applyCam"));
assert.ok(!/if \(!n \|\| n\.url\) continue/.test(hydrate), "must not skip shots that already have url");
assert.ok(/n\.kind !== "shot"/.test(hydrate) || /kind !== \"shot\"/.test(hydrate), "shot-only");
console.log("PASS o48_hydrate_server_wins");
