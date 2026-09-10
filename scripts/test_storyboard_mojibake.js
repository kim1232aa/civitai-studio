// Restore must repair UTF-8 text that was persisted after a pre-charset load.
// Run: node scripts/test_storyboard_mojibake.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + JSON.stringify(from));
  return source.slice(start, end);
}

function mojibake(text) {
  return Buffer.from(text, "utf8").toString("latin1");
}

function cp1252Mojibake(text) {
  const bytes = Buffer.from(text, "utf8");
  const chars = {
    0x80: "€", 0x82: "‚", 0x83: "ƒ", 0x84: "„", 0x85: "…", 0x86: "†", 0x87: "‡",
    0x88: "ˆ", 0x89: "‰", 0x8a: "Š", 0x8b: "‹", 0x8c: "Œ", 0x8e: "Ž",
    0x91: "‘", 0x92: "’", 0x93: "“", 0x94: "”", 0x95: "•", 0x96: "–", 0x97: "—",
    0x98: "˜", 0x99: "™", 0x9a: "š", 0x9b: "›", 0x9c: "œ", 0x9e: "ž", 0x9f: "Ÿ",
  };
  return Array.from(bytes, (byte) => chars[byte] || String.fromCharCode(byte)).join("");
}

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("persisted titles, prompts, assets, and script text are repaired", () => {
  const sandbox = { console, TextDecoder };
  vm.createContext(sandbox);
  const code = [
    section("  const CP1252_BYTES =", "  /** Seko-aligned empty canvas"),
    "globalThis.api = { repairPersistedText };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "storyboard-mojibake.vm.js" });

  const bad = mojibake("分镜1");
  const badCp1252 = cp1252Mojibake("资产");
  const payload = {
    nodes: [
      { id: "shot-1", kind: "shot", title: bad, prompt: bad + " prompt", negativePrompt: bad },
      { id: "asset-1", kind: "asset", title: badCp1252, url: "/out/asset.png" },
    ],
    edges: [{ from: "asset-1", to: "shot-1" }],
    groups: [{ id: "group-1", memberIds: ["asset-1", "shot-1"] }],
    script: {
      title: bad,
      logline: bad,
      scenes: [{ id: "scene-1", title: bad, location: bad, shotIds: ["shot-1"] }],
    },
  };

  assert.equal(sandbox.api.repairPersistedText(payload), true);
  assert.equal(payload.nodes[0].title, "分镜1");
  assert.equal(payload.nodes[0].prompt, "分镜1 prompt");
  assert.equal(payload.nodes[0].negativePrompt, "分镜1");
  assert.equal(payload.nodes[1].title, "资产");
  assert.equal(payload.script.title, "分镜1");
  assert.equal(payload.script.scenes[0].location, "分镜1");
  assert.equal(payload.nodes[0].id, "shot-1");
  assert.equal(payload.nodes[1].url, "/out/asset.png");
  assert.deepEqual(payload.groups[0].memberIds, ["asset-1", "shot-1"]);
});

test("loadDemo starts with a readable default title", () => {
  const sandbox = { state: { nodes: [], edges: [] }, uid() { return "unused"; } };
  vm.createContext(sandbox);
  vm.runInContext([
    section("  function loadDemo()", "  function persist()"),
    "globalThis.api = { state, loadDemo };",
  ].join("\n"), sandbox, { filename: "storyboard-load-demo.vm.js" });
  sandbox.api.loadDemo();
  assert.equal(sandbox.api.state.nodes[0].title, "分镜1");
});

test("restore repairs legacy storage and writes the repaired payload to STORE", () => {
  class FakeStorage {
    constructor() { this.data = new Map(); }
    getItem(key) { return this.data.has(key) ? this.data.get(key) : null; }
    setItem(key, value) { this.data.set(key, String(value)); }
  }

  const bad = mojibake("分镜1");
  const oldKey = "nl-storyboard-v0821o6b";
  const localStorage = new FakeStorage();
  localStorage.setItem(oldKey, JSON.stringify({
    nodes: [
      { id: "shot-1", kind: "shot", title: bad, prompt: bad, url: "" },
      { id: "asset-1", kind: "asset", title: bad, url: "/out/keep.png" },
    ],
    edges: [{ from: "asset-1", to: "shot-1" }],
    groups: [{ id: "group-1", memberIds: ["asset-1", "shot-1"] }],
    script: { title: bad, logline: bad, scenes: [] },
  }));

  const sandbox = {
    console,
    TextDecoder,
    localStorage,
    sessionStorage: new FakeStorage(),
    state: {
      cam: { x: 0, y: 0, s: 1 },
      nodes: [],
      edges: [],
      mode: "image",
      railTab: "assets",
      workspace: "canvas",
      script: { title: "未命名故事", logline: "", scenes: [] },
      editor: {},
      groups: [],
      loras: [],
    },
    $(/* id */) { return null; },
    syncAspectFromSize() {},
    ensureSelectOpt() {},
    isClassicRobotDemo() { return false; },
    removeUnpromotedFromShot() {},
    persistCount: 0,
  };
  vm.createContext(sandbox);
  const code = [
    'const STORE = "nl-storyboard-v0821o7";',
    'const STORE_OLDS = ["nl-storyboard-v0821o6b"];',
    section("  const CP1252_BYTES =", "  /** Seko-aligned empty canvas"),
    'function persist() { persistCount += 1; localStorage.setItem(STORE, JSON.stringify({ nodes: state.nodes, groups: state.groups, script: state.script })); }',
    section("  function restore()", "  function applyCam()"),
    "globalThis.api = { state, restore, localStorage };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "storyboard-restore.vm.js" });

  assert.equal(sandbox.api.restore(), true);
  assert.equal(sandbox.api.state.nodes[0].title, "分镜1");
  assert.equal(sandbox.api.state.nodes[1].title, "分镜1");
  assert.equal(sandbox.api.state.script.title, "分镜1");
  assert.equal(sandbox.persistCount, 1);
  const saved = JSON.parse(sandbox.api.localStorage.getItem("nl-storyboard-v0821o7"));
  assert.equal(saved.nodes[0].title, "分镜1");
  assert.equal(saved.nodes[1].url, "/out/keep.png");
  assert.deepEqual(saved.groups[0].memberIds, ["asset-1", "shot-1"]);
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
    console.log("FAIL storyboard-mojibake " + failed);
    process.exit(1);
  }
  console.log("PASS storyboard-mojibake");
})();
