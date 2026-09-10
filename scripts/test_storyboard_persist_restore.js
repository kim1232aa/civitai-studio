// Executable persist→clear-session→restore + server writeback hydrate harness.
// Run: node scripts/test_storyboard_persist_restore.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o15-server-writeback"), "html stamp o15");
assert.ok(html.includes("storyboard.js?v=20260910-r15srvwb"), "cache bust o15");
assert.ok(source.includes('const STORE = "nl-storyboard-v0821o15"'), "STORE o15");
assert.ok(source.includes('"nl-storyboard-v0821o14"'), "STORE_OLDS keeps o14");
assert.ok(source.includes("function persistServer"), "persistServer");
assert.ok(source.includes("function hydrateFromServer"), "hydrateFromServer");
assert.ok(source.includes("/api/storyboard-graph"), "storyboard-graph path");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + from);
  return source.slice(start, end);
}

class FakeStorage {
  constructor(opts) {
    this.map = new Map();
    this.throwOnSet = !!(opts && opts.throwOnSet);
  }
  getItem(k) { return this.map.has(k) ? this.map.get(k) : null; }
  setItem(k, v) {
    if (this.throwOnSet) {
      const e = new Error("quota");
      e.name = "QuotaExceededError";
      e.code = 22;
      throw e;
    }
    this.map.set(k, String(v));
  }
  removeItem(k) { this.map.delete(k); }
  clear() { this.map.clear(); }
}

class Element {
  constructor(tag, attrs) {
    this.tagName = String(tag || "div").toUpperCase();
    this.attrs = attrs || {};
    this.children = [];
    this.value = this.attrs.value || "";
    this.title = "";
    this.textContent = "";
    this.className = "";
  }
  appendChild(c) { this.children.push(c); return c; }
}

function harness(opts) {
  const elements = {};
  for (const id of [
    "backend", "service", "duration", "aspect", "res", "width", "height",
    "steps", "cfg", "sampler", "scheduler", "seed", "nanoRes", "negative", "prompt", "msg",
  ]) {
    elements[id] = new Element(id === "prompt" || id === "negative" || id === "msg" ? "div" : "input", { id });
  }
  const localStorage = new FakeStorage({ throwOnSet: !!(opts && opts.quotaLocal) });
  const sessionStorage = new FakeStorage();
  const serverStore = { graph: (opts && opts.serverGraph) || null };
  const puts = [];
  const sandbox = {
    console,
    localStorage,
    sessionStorage,
    document: {
      getElementById: (id) => elements[id] || null,
      createElement: (tag) => new Element(tag),
    },
    fetch: async (url, init) => {
      const u = String(url || "");
      if (u.indexOf("/api/storyboard-graph") >= 0) {
        const method = String((init && init.method) || "GET").toUpperCase();
        if (method === "PUT") {
          const body = JSON.parse(init.body);
          serverStore.graph = body;
          puts.push(body);
          return { ok: true, status: 200, json: async () => ({ graph: body }) };
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ graph: serverStore.graph }),
        };
      }
      return { ok: false, status: 404, json: async () => ({ error: "not found" }) };
    },
  };
  vm.createContext(sandbox);
  const code = [
    "const $ = (id) => document.getElementById(id);",
    section("  const STORE =", "  const CIVITAI_PREF_SERVICE ="),
    "  const ROBOT_DEMO_IDS = {};",
    "  const ROBOT_DEMO_TITLES = {};",
    "  let _composerShotId = null;",
    "  const state = {",
    "    cam: { x: 0, y: 0, s: 0.5 }, nodes: [], edges: [], mode: 'image',",
    "    railTab: 'assets', groups: [], workspace: 'canvas',",
    "    script: { title: '未命名故事', logline: '', scenes: [] },",
    "    editor: { activeShotId: null, playIndex: 0 },",
    "    loras: [], history: [], selected: null, multi: [],",
    "  };",
    "  function uid(p) { return (p || 'id') + '-x'; }",
    "  function nodeById(id) { return state.nodes.find((n) => n.id === id); }",
    "  function saveDisplayedComposer() {}",
    "  function syncAspectFromSize() {}",
    "  function ensureSelectOpt(el, value) { if (el) el.value = value; }",
    "  function isClassicRobotDemo() { return false; }",
    "  function removeUnpromotedFromShot() { return false; }",
    "  function isVideoUrl(u) { return /\\.mp4(\\?|$)/i.test(String(u || '')); }",
    "  function mediaKindOf(u) { return isVideoUrl(u) ? 'video' : 'image'; }",
    "  function isJunkRailItem() { return false; }",
    "  function pushHistoryItem(url, title) {",
    "    if (!url) return;",
    "    state.history = [{ url, title, kind: mediaKindOf(url) }].concat(state.history || []).slice(0, 24);",
    "  }",
    "  function renderRail() {}",
    "  function renderCards() {}",
    "  function drawWires() {}",
    "  const __msgs = [];",
    "  function setMsg(t, cls) { __msgs.push({ t: String(t || ''), cls: cls || '' }); }",
    section("  function isQuotaErr(e) {", "  function applyCam() {"),
    section("  function writebackResult(shot, url) {", "    function pickUrl(data) {"),
    "  globalThis.api = { state, STORE, persist, restore, writebackResult, mergePreferUrl, isQuotaErr, persistServer, hydrateFromServer, applyGraph, __msgs, localStorage, sessionStorage, __puts: null, __server: null };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "storyboard-persist-restore.vm.js" });
  sandbox.api.__puts = puts;
  sandbox.api.__server = serverStore;
  return sandbox.api;
}

function test_persist_clear_session_restore_keeps_shot_url() {
  const api = harness();
  const shot = { id: "shot-1", kind: "shot", title: "分镜1", url: "", x: 0, y: 0 };
  api.state.nodes = [shot];
  api.writebackResult(shot, "/out/proof-o15.png");
  assert.equal(api.state.nodes[0].url, "/out/proof-o15.png", "writeback sets live.url");
  const rawLocal = api.localStorage.getItem(api.STORE);
  assert.ok(rawLocal && rawLocal.includes("/out/proof-o15.png"), "persisted into localStorage");
  assert.ok(api.sessionStorage.getItem(api.STORE), "also mirrored to sessionStorage");

  // Hard-refresh simulation: session gone; in-memory graph wiped; restore from localStorage.
  api.sessionStorage.clear();
  api.state.nodes = [];
  api.state.edges = [];
  const ok = api.restore();
  assert.equal(ok, true, "restore returns true");
  assert.equal(api.state.nodes.length, 1, "restored one node");
  assert.equal(api.state.nodes[0].url, "/out/proof-o15.png", "shot.url survives clear-session restore");
}

function test_merge_prefer_url_session_fills_blank_local() {
  const api = harness();
  const localGraph = {
    cam: { x: 1, y: 2, s: 0.5 },
    nodes: [{ id: "shot-1", kind: "shot", title: "分镜1", url: "" }],
    edges: [],
    mode: "image",
  };
  const sessionGraph = {
    cam: { x: 9, y: 9, s: 0.5 },
    nodes: [{ id: "shot-1", kind: "shot", title: "分镜1", url: "/out/session-newer.png" }],
    edges: [],
    mode: "image",
  };
  api.localStorage.setItem(api.STORE, JSON.stringify(localGraph));
  api.sessionStorage.setItem(api.STORE, JSON.stringify(sessionGraph));
  api.state.nodes = [];
  assert.equal(api.restore(), true);
  assert.equal(api.state.nodes[0].url, "/out/session-newer.png", "blank local must not clobber session url");
}

function test_quota_exceeded_surfaces_warn() {
  const api = harness({ quotaLocal: true });
  api.state.nodes = [{ id: "shot-1", kind: "shot", title: "分镜1", url: "/out/q.png" }];
  api.persist();
  assert.ok(api.__msgs.some((m) => m.cls === "warn" && /本地缓存已满/.test(m.t)), "QuotaExceeded warns via setMsg");
  // session mirror still attempted
  assert.ok(api.sessionStorage.getItem(api.STORE), "sessionStorage still written when local quota fails");
}

function test_mergePreferUrl_unit() {
  const api = harness();
  const a = JSON.stringify({ nodes: [{ id: "s1", url: "" }] });
  const b = JSON.stringify({ nodes: [{ id: "s1", url: "/out/x.png" }] });
  const merged = JSON.parse(api.mergePreferUrl(a, b));
  assert.equal(merged.nodes[0].url, "/out/x.png");
  assert.equal(api.mergePreferUrl(null, b), b);
  assert.equal(api.mergePreferUrl(a, null), a);
}

async function test_writeback_puts_server_and_clean_profile_hydrate() {
  const api = harness();
  const shot = { id: "shot-op", kind: "shot", title: "分镜1", url: "", x: 10, y: 20 };
  api.state.nodes = [shot];
  api.writebackResult(shot, "/out/12100372-20260910081835126_0.jpg");
  // allow microtask for fetch PUT
  await Promise.resolve();
  await new Promise((r) => setTimeout(r, 0));
  assert.ok(api.__puts.length >= 1, "writeback PUT /api/storyboard-graph");
  assert.equal(api.__server.graph.nodes[0].url, "/out/12100372-20260910081835126_0.jpg");

  // Clean profile: wipe local/session/memory (UI审查员 different desktop)
  api.localStorage.clear();
  api.sessionStorage.clear();
  api.state.nodes = [{ id: "shot-1", kind: "shot", title: "分镜1", url: "", x: 560, y: 80 }]; // loadDemo
  api.state.edges = [];
  const changed = await api.hydrateFromServer();
  assert.equal(changed, true, "hydrate adopts server graph when no local media");
  assert.equal(api.state.nodes[0].id, "shot-op", "server shot id adopted");
  assert.equal(api.state.nodes[0].url, "/out/12100372-20260910081835126_0.jpg", "card url survives clean-profile hydrate");
  assert.ok(api.localStorage.getItem(api.STORE), "hydrate mirrors into localStorage");
}

test_mergePreferUrl_unit();
test_persist_clear_session_restore_keeps_shot_url();
test_merge_prefer_url_session_fills_blank_local();
test_quota_exceeded_surfaces_warn();
test_writeback_puts_server_and_clean_profile_hydrate().then(() => {
  console.log("ok: storyboard persist/restore executable checks passed");
}).catch((e) => {
  console.error(e);
  process.exit(1);
});
