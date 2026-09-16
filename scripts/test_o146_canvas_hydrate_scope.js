#!/usr/bin/env node
/** o146: canvas-scoped boards must not applyGraph(house) — Magao dirty revive guard. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o146-canvas-hydrate-scope"), "js stamp");
assert.ok(html.includes("v0821o146-canvas-hydrate-scope") || html.includes("o146canvas") || html.includes("v0821o147-house-first-after-import") || html.includes("o147house") || html.includes("v0821o148-magao-cn-catalog-tongyi") || html.includes("o148magao") || html.includes("v0821o150-nano-prompt-limit-warn") || html.includes("v0821o151-fal-schnell-steps-honest") || html.includes("v0821o151b-fal-steps-hint-sticky") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o152-nano-aspect-matches-size") || html.includes("v0821o153-result-writeback-original-card") || html.includes("v0821o153-result-writeback-original-card") || html.includes("o150nano"), "html stamp o146 or successor");
assert.ok(/storyboard\.js\?v=o146canvas|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o147house|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o148magao|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o149bseed|storyboard\.js\?v=o153writeback|storyboard\.js\?v=o150nano|storyboard\.js\?v=o151bsticky|storyboard\.js\?v=o152nano|storyboard\.js\?v=o153writeback/.test(html), "cache bust o146+");
assert.ok(js.includes("canvasScoped"), "canvasScoped guard");
assert.ok(js.includes("never replace the whole board with"), "comment explains Magao revive");

const start = js.indexOf("  function shotUrlMtime(n) {");
const end = js.indexOf("  function applyCam()", start);
assert.ok(start >= 0 && end > start, "hydrate seam");
const hydrateSlice = js.slice(start, end);

function makeApi(opts) {
  const {
    serverGraph,
    nodes,
    canvasAdopted = false,
    mainHouse = false,
  } = opts;
  const state = { nodes: nodes.map((n) => Object.assign({}, n)), edges: [], cam: { x: 0, y: 0, s: 1 } };
  let applied = null;
  const sandbox = {
    state,
    _canvasAdopted: canvasAdopted,
    shotUrlMtime: undefined, // filled by slice
    isMainHouseGraph() { return mainHouse; },
    persist() {},
    applyGraph(p) {
      applied = p;
      state.nodes = (p.nodes || []).map((n) => Object.assign({}, n));
      return true;
    },
    shotsHaveMedia() {
      return (state.nodes || []).some((n) => n && n.kind === "shot" && String(n.url || "").trim());
    },
    shots() {
      return (state.nodes || []).filter((n) => n && n.kind === "shot");
    },
    fetch: async () => ({
      ok: true,
      json: async () => ({ graph: serverGraph }),
    }),
    Date, Number, String, Array, Object, JSON, console,
  };
  vm.createContext(sandbox);
  vm.runInContext(
    hydrateSlice + "\nglobalThis.hydrateFromServer = hydrateFromServer;",
    sandbox
  );
  return {
    state,
    hydrateFromServer: sandbox.hydrateFromServer,
    getApplied: () => applied,
  };
}

const HOUSE = {
  nodes: [
    { id: "shot-1", kind: "shot", url: "/out/modelscope-ai_magao.png" },
    { id: "shot-mqcgmv", kind: "shot", url: "" },
    { id: "shot-6jd6vf", kind: "shot", url: "" },
    { id: "fillref-x", kind: "character", url: "/out/fill.png" },
  ],
};

async function main() {
  // 1) blank burn canvas adopted → must NOT applyGraph(house)
  {
    const api = makeApi({
      serverGraph: HOUSE,
      nodes: [{ id: "shot-kfhg25", kind: "shot", url: "", title: "分镜1" }],
      canvasAdopted: true,
      mainHouse: false,
    });
    const changed = await api.hydrateFromServer();
    assert.equal(api.getApplied(), null, "blank scoped: no applyGraph");
    assert.equal(api.state.nodes.length, 1, "blank scoped: keep 1 shot");
    assert.equal(api.state.nodes[0].id, "shot-kfhg25");
    assert.equal(changed, false, "blank scoped: no change");
  }

  // 2) burn canvas with media, house has more shots → must NOT replace board
  {
    const api = makeApi({
      serverGraph: HOUSE,
      nodes: [{ id: "shot-kfhg25", kind: "shot", url: "/out/12100372-burn.jpg", _urlUpdatedAt: 999 }],
      canvasAdopted: true,
      mainHouse: false,
    });
    const changed = await api.hydrateFromServer();
    assert.equal(api.getApplied(), null, "media scoped: no applyGraph");
    assert.equal(api.state.nodes[0].id, "shot-kfhg25");
    assert.equal(api.state.nodes[0].url, "/out/12100372-burn.jpg");
    assert.equal(changed, false);
  }

  // 3) main house blank (not canvas-scoped / or mainHouse) → still allow full hydrate
  {
    const api = makeApi({
      serverGraph: HOUSE,
      nodes: [{ id: "shot-1", kind: "shot", url: "" }],
      canvasAdopted: true,
      mainHouse: true,
    });
    const changed = await api.hydrateFromServer();
    assert.ok(api.getApplied(), "main house blank: applyGraph allowed");
    assert.equal(api.state.nodes[0].url, "/out/modelscope-ai_magao.png");
    assert.equal(changed, true);
  }

  // 4) not yet adopted (boot) blank → house hydrate still allowed (clean profile)
  {
    const api = makeApi({
      serverGraph: HOUSE,
      nodes: [{ id: "shot-tmp", kind: "shot", url: "" }],
      canvasAdopted: false,
      mainHouse: false,
    });
    const changed = await api.hydrateFromServer();
    assert.ok(api.getApplied(), "pre-adopt blank: applyGraph allowed");
    assert.equal(changed, true);
  }

  // 5) scoped: same-id URL merge still works (empty local adopts server for that id only)
  {
    const api = makeApi({
      serverGraph: {
        nodes: [
          { id: "shot-kfhg25", kind: "shot", url: "/out/from-house-same-id.jpg", _urlUpdatedAt: 500 },
          { id: "shot-1", kind: "shot", url: "/out/magao.png" },
        ],
      },
      nodes: [{ id: "shot-kfhg25", kind: "shot", url: "" }],
      canvasAdopted: true,
      mainHouse: false,
    });
    const changed = await api.hydrateFromServer();
    assert.equal(api.getApplied(), null, "scoped merge: no full replace");
    assert.equal(api.state.nodes.length, 1, "scoped merge: no Magao shot injected");
    assert.equal(api.state.nodes[0].url, "/out/from-house-same-id.jpg", "scoped merge: same id URL");
    assert.equal(changed, true);
  }

  console.log("PASS o146_canvas_hydrate_scope");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
