#!/usr/bin/env node
/** o49b: hydrate keeps local when pendingPut / newer urlUpdatedAt; adopts when stale. */
"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(ROOT, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o49b-hydrate-fresh-empty-url"), "html stamp");
assert.ok(html.includes("20260911-o49bhydratefreshemptyurl"), "cache bust");
assert.ok(source.includes("o49b freshness supersedes blind o48"), "comment supersedes o48");
assert.ok(source.includes("function shotUrlMtime"), "shotUrlMtime helper");
assert.ok(source.includes("_pendingPut"), "pendingPut marker");
assert.ok(source.includes("_urlUpdatedAt"), "urlUpdatedAt writeback");

const start = source.indexOf("  function shotUrlMtime(n) {");
const end = source.indexOf("  function applyCam()", start);
assert.ok(start >= 0 && end > start, "hydrate seam");
const hydrateSlice = source.slice(start, end);

function makeApi(serverGraph, nodes) {
  const state = { nodes: nodes.slice(), edges: [], cam: { x: 0, y: 0, s: 1 } };
  const store = { STORE: "nl-storyboard-v0821o16" };
  const ls = new Map();
  const sandbox = {
    state,
    persist() { ls.set(store.STORE, JSON.stringify({ nodes: state.nodes })); },
    applyGraph() { return false; },
    shotsHaveMedia() {
      return (state.nodes || []).some((n) => n && n.kind === "shot" && n.url);
    },
    fetch: async () => ({
      ok: true,
      json: async () => ({ graph: serverGraph }),
    }),
    Date,
    Number,
    String,
    Array,
    Object,
    JSON,
    console,
  };
  vm.createContext(sandbox);
  vm.runInContext(
    hydrateSlice +
      "\nglobalThis.hydrateFromServer = hydrateFromServer;\nglobalThis.shotUrlMtime = shotUrlMtime;",
    sandbox
  );
  return { state, hydrateFromServer: sandbox.hydrateFromServer, ls, store };
}

async function main() {
  // 1) pendingPut → keep local
  {
    const api = makeApi(
      {
        nodes: [{ id: "s1", kind: "shot", url: "/out/server.png", urlUpdatedAt: 100 }],
      },
      [{ id: "s1", kind: "shot", url: "/out/local.png", _pendingPut: true, _urlUpdatedAt: 50 }]
    );
    const changed = await api.hydrateFromServer();
    assert.equal(changed, false, "pendingPut keeps local");
    assert.equal(api.state.nodes[0].url, "/out/local.png");
  }

  // 2) local urlUpdatedAt newer → keep local
  {
    const api = makeApi(
      {
        nodes: [{ id: "s1", kind: "shot", url: "/out/server.png", _urlUpdatedAt: 100 }],
      },
      [{ id: "s1", kind: "shot", url: "/out/local.png", _urlUpdatedAt: 200 }]
    );
    const changed = await api.hydrateFromServer();
    assert.equal(changed, false, "newer local keeps");
    assert.equal(api.state.nodes[0].url, "/out/local.png");
  }

  // 3) local older / missing mtime → adopt server (server wins when fresher)
  {
    const api = makeApi(
      {
        nodes: [{ id: "s1", kind: "shot", url: "/out/server.png", _urlUpdatedAt: 300 }],
      },
      [{ id: "s1", kind: "shot", url: "/out/stale.png", _urlUpdatedAt: 10 }]
    );
    const changed = await api.hydrateFromServer();
    assert.equal(changed, true, "stale local adopts server");
    assert.equal(api.state.nodes[0].url, "/out/server.png");
  }

  // 4) local empty → adopt
  {
    const api = makeApi(
      { nodes: [{ id: "s1", kind: "shot", url: "/out/server.png" }] },
      [
        { id: "keep", kind: "shot", url: "/out/other.png" },
        { id: "s1", kind: "shot", url: "" },
      ]
    );
    const changed = await api.hydrateFromServer();
    assert.equal(changed, true, "empty local adopts");
    assert.equal(api.state.nodes[1].url, "/out/server.png");
  }

  // 5) both missing mtime, different urls → adopt server (stale LS)
  {
    const api = makeApi(
      { nodes: [{ id: "s1", kind: "shot", url: "/out/server.png" }] },
      [{ id: "s1", kind: "shot", url: "/out/old-ls.png" }]
    );
    const changed = await api.hydrateFromServer();
    assert.equal(changed, true, "no mtime → server wins when fresher/unknown");
    assert.equal(api.state.nodes[0].url, "/out/server.png");
  }

  console.log("PASS o49b_hydrate_freshness");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
