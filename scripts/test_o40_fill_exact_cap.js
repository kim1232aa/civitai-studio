// o40: 灌满 + gate same outbound口径; Nano maxRefs=5 never 6/5 when 成片 present
// Run: node scripts/test_o40_fill_exact_cap.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(html.includes("v0821o45-magao-edit2509-refs3"), "html stamp o41");
assert.ok(html.includes("storyboard.js?v=20260910-o45magaoedit2509refs3"), "cache bust o41");
assert.ok(source.includes("v0821o41:"), "js header o41");
assert.ok(source.includes("v0821o40:"), "js header o40 lineage");
assert.ok(source.includes("function fillRefSlotsToCap"), "fillRefSlotsToCap");
assert.ok(source.includes("/out/fill-cap-"), "fill uses /out/fill-cap- fixtures");
assert.ok(!source.includes("/out/o40-fill-"), "must not invent phantom o40-fill URLs");
assert.ok(source.includes("countRefUrls(null, n).length"), "UI numerator outbound");
assert.ok(!/const refCount = displayRefUrls\(n\)\.length/.test(source), "UI must not use displayRefUrls for N/cap");

function extractHelpers() {
  const start = source.indexOf("const PROVIDER_REF_CAPS = {");
  const end = source.indexOf("\n  function setShotBusy", start);
  assert.ok(start >= 0 && end > start, "helper block seam");
  // displayRefUrls / shotResultImageUrl live earlier — inject stubs that match production口径
  const early = `
    function shotResultImageUrl(shot) {
      if (!shot || !shot.url) return "";
      const u = String(shot.url);
      if (isVideoUrl(u)) return "";
      return u;
    }
    function displayRefUrls(shot) {
      const urls = countRefUrls(null, shot).slice();
      const own = shotResultImageUrl(shot);
      if (own && urls.indexOf(own) < 0) urls.push(own);
      return urls;
    }
  `;
  return early + source.slice(start, end);
}

class FakeEl {
  constructor(id) { this.id = id; this.value = ""; this.options = []; this.attrs = {}; }
  getAttribute(k) { return this.attrs[k] || null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
}

function harness(backend) {
  const els = { backend: new FakeEl("backend"), service: new FakeEl("service"), msg: new FakeEl("msg") };
  els.backend.value = backend || "nano-gpt";
  const state = { mode: "image", nodes: [], edges: [], selected: "shot-1", catalogById: {}, dockMode: "expanded", loras: [] };
  const box = {
    state,
    $: (id) => els[id] || null,
    connectedAssets(id) {
      return state.edges.filter((e) => e.to === id).map((e) => state.nodes.find((n) => n.id === e.from)).filter(Boolean);
    },
    connectedNodes(id) { return box.connectedAssets(id); },
    frameAsset() { return null; },
    isVideoUrl(u) { return /\\.(mp4|webm|mov)(\\?|$)/i.test(String(u || "")); },
    catalogItemForService() {
      const sid = els.service.value;
      return sid && state.catalogById[sid] ? state.catalogById[sid] : null;
    },
    currentBackend() { return els.backend.value; },
    nodeById(id) { return state.nodes.find((n) => n.id === id) || null; },
    assets() { return state.nodes.filter((n) => n.kind === "character" || n.kind === "asset"); },
    uid(prefix) { return prefix + "-" + Math.random().toString(36).slice(2, 8); },
    linkAssetToShot(asset, shot) {
      if (!state.edges.some((e) => e.from === asset.id && e.to === shot.id)) {
        state.edges.push({ from: asset.id, to: shot.id });
      }
    },
    ensureSelectOpt() {},
    renderDock() {},
    syncParamSurface() {},
    setMsg() {},
    Event: function Event() {},
    document: { createElement: () => ({ value: "", textContent: "" }) },
  };
  const script = new vm.Script(`(function(){
    const state = this.state;
    const $ = this.$;
    const connectedAssets = this.connectedAssets.bind(this);
    const connectedNodes = this.connectedNodes.bind(this);
    const frameAsset = this.frameAsset;
    const isVideoUrl = this.isVideoUrl;
    const catalogItemForService = this.catalogItemForService.bind(this);
    const currentBackend = this.currentBackend.bind(this);
    const nodeById = this.nodeById.bind(this);
    const assets = this.assets.bind(this);
    const uid = this.uid.bind(this);
    const linkAssetToShot = this.linkAssetToShot.bind(this);
    const ensureSelectOpt = this.ensureSelectOpt;
    const renderDock = this.renderDock;
    const syncParamSurface = this.syncParamSurface;
    const setMsg = this.setMsg;
    const Event = this.Event;
    const document = this.document;
    ${extractHelpers()}
    return { resolveRefCaps, maxRefCount, countRefUrls, displayRefUrls, fillRefSlotsToCap, attachExtraImages, catalogEatsRefs };
  })`);
  const api = script.runInContext(vm.createContext({ console })).call(box);
  return { api, state, els };
}

// Nano maxRefs=5 + completed-shot 成片 → 灌满 stops at outbound 5; display may be 6 but UI N uses outbound
{
  const { api, state, els } = harness("nano-gpt");
  els.service.value = "openai/gpt-image-2.5/flare/edit";
  state.catalogById["openai/gpt-image-2.5/flare/edit"] = {
    id: "openai/gpt-image-2.5/flare/edit",
    name: "Flare Edit",
    backend: "nano-gpt",
    capabilities: { maxRefs: 5, image_to_image: true, refImagesField: "input_references" },
  };
  const shot = { id: "shot-1", kind: "shot", x: 0, y: 0, url: "https://ex/completed-shot.png" };
  state.nodes.push(shot);
  assert.equal(api.maxRefCount(state.catalogById["openai/gpt-image-2.5/flare/edit"]), 5);
  assert.equal(api.countRefUrls(null, shot).length, 0, "outbound excludes 成片");
  assert.equal(api.displayRefUrls(shot).length, 1, "display includes 成片");
  const added = api.fillRefSlotsToCap(shot);
  const fillUrls = api.countRefUrls(null, shot);
  assert.ok(fillUrls.every((u) => /^\/out\/fill-cap-\d+\.jpg$/.test(u)), "all fill urls are real fill-cap jpg, got " + JSON.stringify(fillUrls));
  const sendN = fillUrls.length;
  const dispN = api.displayRefUrls(shot).length;
  assert.equal(sendN, 5, "outbound exactly 5 after 灌满, got " + sendN);
  assert.ok(sendN <= 5, "never outbound > cap");
  assert.ok(added === 5, "added 5 fixtures, got " + added);
  // UI 口径 = outbound: would show 5/5 not 6/5
  assert.equal(sendN, 5, "UI numerator outbound == 5 → no 超出");
  // 成片 still visible in display helper but must not be in outbound bag
  assert.ok(dispN === 6, "display helper still sees 成片+5 (chip visual)");
  const payload = api.attachExtraImages({}, shot);
  assert.equal(payload.images.length, 5, "outbound bag == 5 not 6");
  assert.ok(payload.images.indexOf(shot.url) < 0, "成片 url not stuffed into outbound");
}

// Nano without 成片 → still exact 5
{
  const { api, state, els } = harness("nano-gpt");
  els.service.value = "nano/x";
  state.catalogById["nano/x"] = {
    id: "nano/x",
    backend: "nano-gpt",
    capabilities: { maxRefs: 5, image_to_image: true, refImagesField: "input_references" },
  };
  const shot = { id: "shot-1", kind: "shot", x: 0, y: 0 };
  state.nodes.push(shot);
  api.fillRefSlotsToCap(shot);
  assert.equal(api.countRefUrls(null, shot).length, 5);
  assert.equal(api.displayRefUrls(shot).length, 5);
  assert.equal(api.attachExtraImages({}, shot).images.length, 5);
}

// Already at cap + 成片 → add 0, outbound stays 5
{
  const { api, state, els } = harness("nano-gpt");
  els.service.value = "nano/y";
  state.catalogById["nano/y"] = {
    id: "nano/y",
    backend: "nano-gpt",
    capabilities: { maxRefs: 5, image_to_image: true, refImagesField: "input_references" },
  };
  const shot = { id: "shot-1", kind: "shot", url: "https://ex/done.png" };
  state.nodes.push(shot);
  for (let i = 1; i <= 5; i++) {
    const a = { id: "r" + i, kind: "character", url: "https://ex/r" + i + ".png" };
    state.nodes.push(a);
    state.edges.push({ from: a.id, to: shot.id });
  }
  const added = api.fillRefSlotsToCap(shot);
  assert.equal(added, 0, "no over-fill");
  assert.equal(api.countRefUrls(null, shot).length, 5);
}

console.log("PASS o40 fill-exact-cap + o41 real fixtures");
