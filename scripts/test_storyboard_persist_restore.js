// Executable persist→clear-session→restore harness (runs production storyboard.js seams).
// Run: node scripts/test_storyboard_persist_restore.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o14-writeback-persist-restore"), "html stamp o14");
assert.ok(html.includes("storyboard.js?v=20260910-r14wbpersist"), "cache bust o14");
assert.ok(source.includes('const STORE = "nl-storyboard-v0821o14"'), "STORE o14");
assert.ok(source.includes('"nl-storyboard-v0821o13"'), "STORE_OLDS keeps o13");

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
  const msgs = [];
  const sandbox = {
    console,
    localStorage,
    sessionStorage,
    document: {
      getElementById: (id) => elements[id] || null,
      createElement: (tag) => new Element(tag),
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
    "  globalThis.api = { state, STORE, persist, restore, writebackResult, mergePreferUrl, isQuotaErr, __msgs, localStorage, sessionStorage };",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "storyboard-persist-restore.vm.js" });
  return sandbox.api;
}

function test_persist_clear_session_restore_keeps_shot_url() {
  const api = harness();
  const shot = { id: "shot-1", kind: "shot", title: "分镜1", url: "", x: 0, y: 0 };
  api.state.nodes = [shot];
  api.writebackResult(shot, "/out/proof-o14.png");
  assert.equal(api.state.nodes[0].url, "/out/proof-o14.png", "writeback sets live.url");
  const rawLocal = api.localStorage.getItem(api.STORE);
  assert.ok(rawLocal && rawLocal.includes("/out/proof-o14.png"), "persisted into localStorage");
  assert.ok(api.sessionStorage.getItem(api.STORE), "also mirrored to sessionStorage");

  // Hard-refresh simulation: session gone; in-memory graph wiped; restore from localStorage.
  api.sessionStorage.clear();
  api.state.nodes = [];
  api.state.edges = [];
  const ok = api.restore();
  assert.equal(ok, true, "restore returns true");
  assert.equal(api.state.nodes.length, 1, "restored one node");
  assert.equal(api.state.nodes[0].url, "/out/proof-o14.png", "shot.url survives clear-session restore");
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

test_mergePreferUrl_unit();
test_persist_clear_session_restore_keeps_shot_url();
test_merge_prefer_url_session_fills_blank_local();
test_quota_exceeded_surfaces_warn();
console.log("ok: storyboard persist/restore executable checks passed");
