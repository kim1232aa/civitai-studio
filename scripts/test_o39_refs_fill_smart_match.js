// o39: fill-to-cap slots + smart Edit sibling + outbound bag length == cap
// Run: node scripts/test_o39_refs_fill_smart_match.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

assert.ok(html.includes("v0821o49-harness-stamp-o48"), "html stamp o39");
assert.ok(html.includes("storyboard.js?v=20260911-o49harnessstampo48"), "cache bust o39");
assert.ok(html.includes("storyboard-ui.css?v=20260911-o49harnessstampo48"), "css bust o39");
assert.ok(source.includes("v0821o39:"), "js header o39");
assert.ok(source.includes("function editSiblingId"), "editSiblingId");
assert.ok(source.includes("function applyEditSibling"), "applyEditSibling");
assert.ok(source.includes("function fillRefSlotsToCap"), "fillRefSlotsToCap");
assert.ok(source.includes("ref-slot-empty"), "empty slot class");
assert.ok(source.includes('data-act="apply-edit-sibling"'), "one-click act");
assert.ok(source.includes('data-act="fill-refs-cap"'), "灌满 act");
assert.ok(source.includes("for (let si = 0; si < remain; si++)"), "loop empty slots to remain");
assert.ok(css.includes("ref-slot-empty"), "css empty slot");

const attachStart = source.indexOf("function attachExtraImages");
const attachBody = source.slice(attachStart, source.indexOf("function setShotBusy", attachStart));
assert.ok(attachBody.includes("urls.slice(0, cap)"), "slice to cap");
assert.ok(attachBody.includes("payload.images = sliced"), "images bag");

function extractHelpers() {
  const start = source.indexOf("const PROVIDER_REF_CAPS = {");
  const end = source.indexOf("\n  function setShotBusy", start);
  assert.ok(start >= 0 && end > start, "helper block seam");
  return source.slice(start, end);
}

class FakeEl {
  constructor(id) {
    this.id = id;
    this.value = "";
    this.options = [];
    this.attrs = {};
  }
  getAttribute(k) { return this.attrs[k] || null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  appendChild(o) { this.options.push(o); }
}

function harness(backend) {
  const els = {
    backend: new FakeEl("backend"),
    service: new FakeEl("service"),
    msg: new FakeEl("msg"),
  };
  els.backend.value = backend || "nano-gpt";
  const state = {
    mode: "image",
    nodes: [],
    edges: [],
    selected: "shot-1",
    catalogById: {},
    dockMode: "expanded",
    loras: [],
  };
  const box = {
    state,
    $: (id) => els[id] || null,
    connectedAssets(id) {
      return state.edges
        .filter((e) => e.to === id)
        .map((e) => state.nodes.find((n) => n.id === e.from))
        .filter(Boolean);
    },
    connectedNodes(id) { return box.connectedAssets(id); },
    frameAsset() { return null; },
    isVideoUrl() { return false; },
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
    ensureSelectOpt(sel, value) {
      if (!sel.options.some((o) => o.value === value)) {
        sel.options.push({ value: String(value), textContent: String(value) });
      }
    },
    renderDock() {},
    syncParamSurface() {},
    setMsg() {},
    Event: function Event() {},
    document: {
      createElement: () => ({ value: "", textContent: "" }),
    },
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
    const ensureSelectOpt = this.ensureSelectOpt.bind(this);
    const renderDock = this.renderDock;
    const syncParamSurface = this.syncParamSurface;
    const setMsg = this.setMsg;
    const Event = this.Event;
    const document = this.document;
    ${extractHelpers()}
    return {
      resolveRefCaps, maxRefCount, catalogEatsRefs, editSiblingId, applyEditSibling,
      refUnusedGateMessage, countRefUrls, attachExtraImages, fillRefSlotsToCap
    };
  })`);
  const ctx = vm.createContext({ console });
  const api = script.runInContext(ctx).call(box);
  return { api, state, els };
}

// Nano maxRefs=5 → bag length 5
{
  const { api, state, els } = harness("nano-gpt");
  els.service.value = "nano/banana";
  state.catalogById["nano/banana"] = {
    id: "nano/banana",
    name: "Banana",
    backend: "nano-gpt",
    capabilities: { maxRefs: 5, image_to_image: true, refImagesField: "input_references" },
  };
  assert.equal(api.maxRefCount(state.catalogById["nano/banana"]), 5, "nano cap 5");
  const shot = { id: "shot-1", kind: "shot", x: 0, y: 0 };
  state.nodes.push(shot);
  for (let i = 1; i <= 5; i++) {
    const a = { id: "a" + i, kind: "character", url: "https://ex/" + i + ".png", title: "r" + i };
    state.nodes.push(a);
    state.edges.push({ from: a.id, to: shot.id });
  }
  const payload = api.attachExtraImages({}, shot);
  assert.equal(payload.images.length, 5, "nano images bag == 5");
  assert.equal(payload.input_references.length, 5, "nano input_references == 5");
}

// Magao maxRefs=1 → bag/singular length 1 (never claim 5)
{
  const { api, state, els } = harness("modelscope-cn");
  els.service.value = "Qwen/Qwen-Image-Edit";
  state.catalogById["Qwen/Qwen-Image-Edit"] = {
    id: "Qwen/Qwen-Image-Edit",
    name: "Qwen Image Edit",
    backend: "modelscope-cn",
    needsSource: true,
    capabilities: { maxRefs: 1, image_to_image: true, refImagesField: "image_url", imageFields: ["image_url"] },
  };
  assert.equal(api.maxRefCount(state.catalogById["Qwen/Qwen-Image-Edit"]), 1, "magao edit cap 1");
  const shot = { id: "shot-1", kind: "shot" };
  state.nodes.push(shot);
  for (let i = 1; i <= 3; i++) {
    const a = { id: "m" + i, kind: "character", url: "https://ex/m" + i + ".png" };
    state.nodes.push(a);
    state.edges.push({ from: a.id, to: shot.id });
  }
  const payload = api.attachExtraImages({}, shot);
  assert.equal(payload.images.length, 1, "magao bag len 1");
  assert.equal(payload.image_url, payload.images[0], "magao singular image_url");
}

// t2i + refs → hard block + one-click Edit sibling
{
  const { api, state, els } = harness("fal");
  els.service.value = "fal-ai/flux/dev/text-to-image";
  state.catalogById["fal-ai/flux/dev/text-to-image"] = {
    id: "fal-ai/flux/dev/text-to-image",
    name: "Flux Dev T2I",
    backend: "fal",
    capabilities: { image_to_image: false, maxRefs: 1 },
  };
  state.catalogById["fal-ai/flux/dev/edit"] = {
    id: "fal-ai/flux/dev/edit",
    name: "Flux Dev Edit",
    backend: "fal",
    capabilities: { image_to_image: true, maxRefs: 9, refImagesField: "image_urls", imageFields: ["image_urls"] },
  };
  const shot = { id: "shot-1", kind: "shot" };
  state.nodes.push(shot);
  const a = { id: "r1", kind: "character", url: "https://ex/r1.png" };
  state.nodes.push(a);
  state.edges.push({ from: a.id, to: shot.id });
  assert.equal(api.catalogEatsRefs(state.catalogById["fal-ai/flux/dev/text-to-image"]), false);
  const msg = api.refUnusedGateMessage(shot);
  assert.ok(msg && msg.includes("文生图"), "hard block: " + msg);
  assert.ok(msg.includes("不静默"), "no silent");
  assert.equal(api.editSiblingId(state.catalogById["fal-ai/flux/dev/text-to-image"]), "fal-ai/flux/dev/edit");
  assert.equal(api.applyEditSibling(), true);
  assert.equal(els.service.value, "fal-ai/flux/dev/edit");
}

// 灌满至 cap
{
  const { api, state, els } = harness("nano-gpt");
  els.service.value = "nano/x";
  state.catalogById["nano/x"] = {
    id: "nano/x",
    backend: "nano-gpt",
    capabilities: { maxRefs: 5, image_to_image: true, refImagesField: "input_references" },
  };
  const shot = { id: "shot-1", kind: "shot", x: 10, y: 20 };
  state.nodes.push(shot);
  const added = api.fillRefSlotsToCap(shot);
  assert.equal(added, 5, "added 5");
  assert.equal(api.countRefUrls(null, shot).length, 5);
  assert.equal(api.attachExtraImages({}, shot).images.length, 5);
}

// no sibling → no invent
{
  const { api, state, els } = harness("fal");
  els.service.value = "fal-ai/only-t2i";
  state.catalogById["fal-ai/only-t2i"] = {
    id: "fal-ai/only-t2i",
    name: "Only T2I",
    backend: "fal",
    capabilities: { image_to_image: false },
  };
  assert.equal(api.editSiblingId(state.catalogById["fal-ai/only-t2i"]), "");
  assert.equal(api.applyEditSibling(), false);
}

console.log("PASS o39 refs-fill-smart-match");
