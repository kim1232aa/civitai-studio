// Contract test for window.storyboardGraph on static/storyboard.js.
// Run: NODE_PATH=/home/ubuntu/.codeman/app/node_modules node scripts/test_storyboard_graph_bridge.js
"use strict";

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const ROOT = path.resolve(__dirname, "..");
const HTML = fs.readFileSync(path.join(ROOT, "static", "storyboard.html"), "utf8");
const SCRIPT = fs.readFileSync(path.join(ROOT, "static", "storyboard.js"), "utf8");

function emptyJson(payload) {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  };
}

function boot() {
  const html = HTML.replace(/<script[\s\S]*?<\/script>/gi, "");
  const dom = new JSDOM(html, {
    url: "http://127.0.0.1:18831/storyboard.html",
    pretendToBeVisual: true,
    runScripts: "outside-only",
  });
  const { window } = dom;
  const g = window;
  g.fetch = async (url) => {
    const href = String(url);
    if (href.includes("/api/catalog")) return emptyJson({ items: [] });
    if (href.includes("/api/capabilities")) return emptyJson({ capabilities: [] });
    if (href.includes("/api/providers")) return emptyJson({ items: [] });
    if (href.includes("/api/defaults")) return emptyJson({ defaults: {}, samplers: [], schedulers: [] });
    if (href.includes("/api/outs")) return emptyJson({ items: [] });
    return emptyJson({});
  };
  if (typeof g.requestAnimationFrame !== "function") {
    g.requestAnimationFrame = (fn) => setTimeout(() => fn(Date.now()), 0);
  }
  if (typeof g.cancelAnimationFrame !== "function") {
    g.cancelAnimationFrame = (id) => clearTimeout(id);
  }
  g.eval(SCRIPT);
  return window;
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

(async () => {
  const window = boot();
  const graph = window.storyboardGraph;
  const state = window.__sekoState;
  assert(graph && typeof graph.get === "function" && typeof graph.set === "function" && typeof graph.clear === "function", "window.storyboardGraph missing get/set/clear");
  assert(state && Array.isArray(state.nodes) && Array.isArray(state.edges) && state.cam, "__sekoState not exported");

  const events = [];
  window.document.addEventListener("storyboard:graph-change", (ev) => {
    events.push(ev.type);
  });

  const seedNodes = [
    { id: "asset-1", kind: "image", title: "资产A", x: 10, y: 20, url: "/out/a.png" },
    { id: "shot-1", kind: "shot", title: "分镜1", x: 400, y: 80, url: "", prompt: "夜间实验室" },
  ];
  const seedEdges = [{ from: "asset-1", to: "shot-1" }];
  const seedViewport = { x: 12, y: 34, zoom: 0.5 };

  const setResult = graph.set({
    nodes: seedNodes,
    edges: seedEdges,
    viewport: seedViewport,
  });
  console.log("set returns graph:", JSON.stringify({
    nodes: setResult.nodes.map((n) => n.id),
    edges: setResult.edges,
    viewport: setResult.viewport,
  }));
  assert(setResult.nodes.length === 2, "set did not install nodes");
  assert(setResult.edges.length === 1 && setResult.edges[0].from === "asset-1", "set did not install edges");
  assert(setResult.viewport.x === 12 && setResult.viewport.y === 34 && setResult.viewport.zoom === 0.5, "set did not map zoom onto viewport");
  assert(state.cam.s === 0.5 && state.cam.x === 12 && state.cam.y === 34, "set did not map viewport.zoom onto cam.s");
  assert(events.length >= 1 && events[events.length - 1] === "storyboard:graph-change", "set/persist did not dispatch storyboard:graph-change");
  const cards = window.document.querySelectorAll("#world .card");
  console.log("render after set:", cards.length, Array.from(cards).map((el) => el.getAttribute("data-id")));
  assert(cards.length === 2, "set did not rerender cards");
  assert(window.document.getElementById("world").innerHTML.includes("分镜1"), "set render missed shot title");

  seedNodes[0].title = "被改掉";
  seedEdges[0].from = "mutated";
  seedViewport.zoom = 9;
  assert(state.nodes[0].title === "资产A", "set leaked caller node reference");
  assert(state.edges[0].from === "asset-1", "set leaked caller edge reference");
  assert(state.cam.s === 0.5, "set leaked caller viewport reference");

  const got = graph.get();
  got.nodes[0].title = "get泄漏";
  got.edges[0].to = "leak";
  got.viewport.zoom = 99;
  assert(state.nodes[0].title === "资产A", "get leaked live node reference");
  assert(state.edges[0].to === "shot-1", "get leaked live edge reference");
  assert(state.cam.s === 0.5, "get leaked live viewport/cam");
  assert(got.viewport.zoom === 99 && !("s" in got.viewport), "get viewport must use zoom, not cam.s");
  console.log("get/set deep-copy isolation:", true);

  const beforeMissing = events.length;
  const missing = graph.set({});
  console.log("set missing fields:", JSON.stringify(missing));
  assert(Array.isArray(missing.nodes) && missing.nodes.length === 0, "missing nodes must fall back to []");
  assert(Array.isArray(missing.edges) && missing.edges.length === 0, "missing edges must fall back to []");
  assert(missing.viewport.x === 0 && missing.viewport.y === 0 && missing.viewport.zoom === 1, "missing viewport must default to {x:0,y:0,zoom:1}");
  assert(state.nodes.length === 0 && state.edges.length === 0, "missing-field set did not replace live graph");
  assert(state.cam.x === 0 && state.cam.y === 0 && state.cam.s === 1, "missing viewport did not reset cam");
  assert(events.length > beforeMissing, "missing-field set did not persist/dispatch");
  assert(!window.document.getElementById("world").innerHTML.includes("分镜1"), "missing-field set left old cards");

  graph.set({
    nodes: [{ id: "keep", kind: "shot", title: "要清掉", x: 1, y: 2, url: "", prompt: "" }],
    edges: [{ from: "keep", to: "keep" }],
    viewport: { x: 8, y: 9, zoom: 1.2 },
  });
  const beforeClear = events.length;
  const cleared = graph.clear();
  console.log("clear:", JSON.stringify(cleared));
  assert(cleared.nodes.length === 0 && cleared.edges.length === 0, "clear must empty graph");
  assert(cleared.viewport.x === 0 && cleared.viewport.y === 0 && cleared.viewport.zoom === 1, "clear viewport must be {x:0,y:0,zoom:1}");
  assert(state.cam.s === 1 && state.nodes.length === 0, "clear did not replace live state");
  assert(events.length > beforeClear, "clear did not persist/dispatch");

  const stored = JSON.parse(window.localStorage.getItem("nl-storyboard-v0794") || "null");
  console.log("persist store after clear:", JSON.stringify({
    nodes: stored && stored.nodes,
    edges: stored && stored.edges,
    cam: stored && stored.cam,
  }));
  assert(stored && Array.isArray(stored.nodes) && stored.nodes.length === 0, "persist did not write empty nodes");
  assert(stored.cam && stored.cam.s === 1, "persist still writes internal cam.s");

  const source = SCRIPT;
  if (/DEMO_BOT|CHAR_LIB|loadDemo|fallbackRealThumb/.test(source)) throw new Error("seed/robot content found in storyboard.js");
  console.log("no robot/demo/seed content");
  console.log("graph-change count:", events.length);
  console.log("OK storyboard-graph-bridge");
})().catch((error) => {
  console.error("FAIL", error);
  process.exit(1);
});
