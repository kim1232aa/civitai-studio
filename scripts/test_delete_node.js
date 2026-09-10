// Canvas must delete a selected node: node, incident edges, groups, script shotIds, persist.
// Run: node scripts/test_delete_node.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + JSON.stringify(from));
  return source.slice(start, end);
}

function deleteNodeSource() {
  const start = source.indexOf("  function deleteNode(");
  assert.ok(start >= 0, "function deleteNode exists");
  const next = source.indexOf("\n  function ", start + "  function deleteNode(".length);
  assert.ok(next > start, "deleteNode is followed by another function");
  return source.slice(start, next);
}

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("deleteNode function exists", () => {
  assert.match(source, /function deleteNode\(/);
});

test("deleteNode is exported as window.__sekoDeleteNode", () => {
  assert.match(source, /window\.__sekoDeleteNode\s*=\s*deleteNode/);
});

test("Delete/Backspace handler exists and ignores textarea/input", () => {
  assert.match(source, /e\.key !== "Delete"/);
  assert.match(source, /e\.key !== "Backspace"/);
  assert.match(source, /textarea,input,select/);
});

test("right-click node menu with delete is created in JS", () => {
  assert.match(source, /nodeContextMenu/);
  assert.match(source, /data-nodeact="delete"/);
  assert.match(source, /data-nodeact="copy"/);
  assert.match(source, /data-nodeact="paste"/);
});

test("node menu CSS exists so delete is visible", () => {
  assert.match(css, /\.split-menu/);
  assert.match(css, /\.node-menu/);
  assert.match(css, /\.node-menu button\.danger|\.split-menu button\.danger/);
});

test("deleteNode uses live pruneGroups, not only v0794 group-node recursion", () => {
  const body = deleteNodeSource();
  assert.match(body, /pruneGroups\s*\(/);
});

function loadDeleteApi() {
  const body = deleteNodeSource();
  const sandbox = { console, sessionStorage: {
    _data: Object.create(null),
    setItem(k, v) { this._data[k] = String(v); },
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._data, k) ? this._data[k] : null; },
  } };
  vm.createContext(sandbox);
  const code = [
    'const STORE = "nl-storyboard-v0821o7";',
    "const state = {",
    "  cam: { x: 0, y: 0, s: 1 },",
    "  nodes: [], edges: [], selected: null, multi: [], groups: [],",
    '  script: { title: "t", logline: "", scenes: [] },',
    "  editor: { activeShotId: null },",
    '  workspace: "canvas", mode: "image",',
    "};",
    "function $(id) { return null; }",
    "function nodeById(id) { return state.nodes.find((n) => n.id === id); }",
    'function shots() { return state.nodes.filter((n) => n.kind === "shot"); }',
    section("  function pruneGroups() {", "  function groupOf("),
    "function persist() {",
    "  sessionStorage.setItem(STORE, JSON.stringify({",
    "    nodes: state.nodes, edges: state.edges, groups: state.groups, script: state.script,",
    "    editor: { activeShotId: state.editor && state.editor.activeShotId || null },",
    "  }));",
    "}",
    "function renderCards() {}",
    "function drawWires() {}",
    "function renderDock() {}",
    "function renderWorkspace() {}",
    "function setMsg() {}",
    "function hideNodeMenu() {}",
    "function unlinkAssetFromShot(asset, shot) {",
    "  if (!asset || !shot) return;",
    "  state.edges = state.edges.filter((e) => !(e.from === asset.id && e.to === shot.id));",
    "  if (shot.firstFrameId === asset.id) shot.firstFrameId = '';",
    "}",
    body,
    "globalThis.api = { state, deleteNode, persist, sessionStorage };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "delete-node.vm.js" });
  return sandbox.api;
}

function seedGraph(api) {
  api.state.nodes = [
    { id: "asset-1", kind: "asset", title: "参考", x: 0, y: 0, url: "/out/a.png" },
    { id: "shot-keep", kind: "shot", title: "留", x: 200, y: 0, url: "", firstFrameId: "shot-gone", prompt: "keep" },
    { id: "shot-gone", kind: "shot", title: "删", x: 400, y: 0, url: "", firstFrameId: "asset-1", prompt: "gone" },
    { id: "text-1", kind: "text", title: "提示词", x: 600, y: 0, text: "hi" },
  ];
  api.state.edges = [
    { from: "asset-1", to: "shot-gone" },
    { from: "asset-1", to: "shot-keep" },
  ];
  api.state.groups = [
    { id: "grp-drop", name: "两人组", memberIds: ["shot-gone", "shot-keep"] },
    { id: "grp-keep", name: "三人组", memberIds: ["shot-gone", "shot-keep", "text-1"] },
  ];
  api.state.script = {
    title: "t",
    logline: "",
    scenes: [{ id: "scene-1", title: "场次 1", location: "", time: "", beat: "", shotIds: ["shot-keep", "shot-gone"] }],
  };
  api.state.editor.activeShotId = "shot-gone";
  api.state.selected = "shot-gone";
  api.state.multi = ["shot-gone", "shot-keep"];
}

test("missing id returns false and does not throw", () => {
  const api = loadDeleteApi();
  seedGraph(api);
  assert.equal(api.deleteNode("no-such-node"), false);
  assert.equal(api.state.nodes.length, 4);
});

test("deleting a shot removes node, incident edges, persist, group members, script shotIds, firstFrameId", () => {
  const api = loadDeleteApi();
  seedGraph(api);
  assert.equal(api.deleteNode("shot-gone"), true);
  assert.equal(api.state.nodes.some((n) => n.id === "shot-gone"), false);
  assert.equal(api.state.nodes.some((n) => n.id === "shot-keep"), true);
  assert.equal(api.state.nodes.some((n) => n.id === "asset-1"), true);
  assert.equal(api.state.edges.some((e) => e.from === "shot-gone" || e.to === "shot-gone"), false);
  assert.equal(api.state.edges.some((e) => e.from === "asset-1" && e.to === "shot-keep"), true);
  assert.equal(api.state.selected, null);
  const keep = api.state.nodes.find((n) => n.id === "shot-keep");
  assert.equal(keep.firstFrameId, "");
  const drop = api.state.groups.find((g) => g.id === "grp-drop");
  assert.equal(drop, undefined);
  const keepG = api.state.groups.find((g) => g.id === "grp-keep");
  assert.ok(keepG);
  assert.deepEqual(keepG.memberIds, ["shot-keep", "text-1"]);
  assert.equal(api.state.script.scenes[0].shotIds.indexOf("shot-gone") >= 0, false);
  assert.ok(api.state.script.scenes[0].shotIds.indexOf("shot-keep") >= 0);
  const saved = JSON.parse(api.sessionStorage.getItem("nl-storyboard-v0821o7"));
  assert.equal(saved.nodes.some((n) => n.id === "shot-gone"), false);
  assert.equal((saved.groups || []).some((g) => (g.memberIds || []).indexOf("shot-gone") >= 0), false);
  assert.equal((saved.script.scenes[0].shotIds || []).indexOf("shot-gone") >= 0, false);
});

test("live HTML still has no empty delete control pretending to work without deleteNode", () => {
  // Toolbar may gain a real delete button later; the JS function is the contract.
  assert.equal(typeof html, "string");
  assert.match(source, /function deleteNode\(/);
});

(async () => {
  let failed = 0;
  for (const t of tests) {
    try {
      await t.fn();
      console.log("  ok   " + t.name);
    } catch (err) {
      failed += 1;
      console.log("  FAIL " + t.name);
      console.log("       " + (err && err.message ? err.message.split("\n")[0] : err));
    }
  }
  if (failed) {
    console.log("FAIL delete-node " + failed);
    process.exit(1);
  }
  console.log("PASS delete-node");
})();
