#!/usr/bin/env node
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(ROOT, "static/storyboard.js"), "utf8");
if (src.indexOf("/api/generate") >= 0 && /fetch\(\s*["']\/api\/generate/.test(src) === false) {
  /* storyboard itself posts generate — fine */
}
function slice(startNeedle, endNeedle) {
  const a = src.indexOf(startNeedle);
  if (a < 0) throw new Error("missing start " + startNeedle.slice(0, 60));
  const b = src.indexOf(endNeedle, a + startNeedle.length);
  if (b < 0) throw new Error("missing end " + endNeedle.slice(0, 60));
  return src.slice(a, b);
}

const extracted = [
  "const FAL_T2I_DEFAULT = \"fal-ai/flux/schnell\";",
  "const FAL_I2V_DEFAULT = \"fal-ai/minimax/video-01/image-to-video\";",
  "const HF_LORA_PREF_SERVICE = \"krea/Krea-2-Turbo\";",
  "const HF_I2I_PREF_SERVICE = \"Qwen/Qwen-Image-Edit\";",
  "const MS_LORA_PREF_SERVICE = \"krea/Krea-2-Turbo\";",
  "const CATALOG_PAGE_SIZE = 50;",
  slice("  const SMART_PREF = {", "  let _svcChunkHandle"),
  slice("  function catalogItemSupportsI2v(it) {", "  function catalogItemSupportsImage(it) {"),
  slice("  function catalogItemSupportsImage(it) {", "  function catalogItemSupportsI2i(it) {"),
  slice("  function catalogItemSupportsI2i(it) {", "  function selectedShotWantsI2i() {"),
  slice("  function catalogItemSupportsT2i(it) {", "  function filterCatalogForMode(items) {"),
  slice("  function catalogEatsRefs(it) {", "  function editSiblingId(it) {"),
  slice("  function pinHfLoraServiceId(sid, op) {", "  function ensureHfLoraServiceSelected() {"),
  slice("  function pinMsLoraServiceId(sid, op) {", "  function msLoraOptionLabel(want, currentText) {"),
].join("\n");

const applyLog = [];
const els = {
  backend: { value: "fal" },
  service: { value: "", options: [] },
  msg: { textContent: "", className: "" },
};
function $(id) { return els[id] || null; }
const state = {
  mode: "image",
  nodes: [{ id: "shot-1", kind: "shot", serviceId: "", backend: "fal", composer: { backend: "fal", service: "" } }],
  edges: [],
  selected: "shot-1",
  catalogById: {},
  catalog: [],
  _catalogRoster: [],
  _serviceItems: [],
};

const sandbox = {
  console,
  URLSearchParams,
  SMART_PREF: undefined,
  state,
  els,
  $,
  shots: function () { return state.nodes; },
  nodeById: function (id) { return (state.nodes || []).filter(function (n) { return n.id === id; })[0] || null; },
  connectedAssets: function (id) {
    return (state.edges || []).filter(function (e) { return e.to === id; }).map(function () { return { id: "asset-1", url: "x.jpg", kind: "image" }; });
  },
  currentBackend: function () { return els.backend.value; },
  catalogItemForService: function () {
    const sid = els.service.value;
    return (sid && state.catalogById[sid]) || null;
  },
  ensureSelectOpt: function (sel, value) {
    if (!sel.options) sel.options = [];
    if (!sel.options.some(function (o) { return o.value === value; })) sel.options.push({ value: value, textContent: value });
  },
  syncParamChrome: function () {
    const item = sandbox.catalogItemForService();
    applyLog.push(item && item.id);
    if (sandbox.ComposerFieldAdapt && sandbox.ComposerFieldAdapt.applyToSurface) {
      sandbox.ComposerFieldAdapt.applyToSurface({ item: item, backend: els.backend.value });
    }
  },
  setMsg: function (t) { els.msg.textContent = String(t || ""); },
  looksCivitaiServiceId: function (id) { return String(id || "").indexOf("image/") === 0 || String(id || "").indexOf("video/") === 0; },
  looksFalServiceId: function (id) { return String(id || "").indexOf("fal-ai/") === 0; },
  looksHfServiceId: function (id) { return String(id || "").indexOf("krea/") === 0 || String(id || "").indexOf("Qwen/") === 0 || String(id || "").indexOf("Wan-AI/") === 0 || String(id || "").indexOf("black-forest") === 0; },
  hfHasLoras: function () { return false; },
  catalogImageFields: function () { return []; },
  SINGULAR_FIRST_FIELDS: ["image_url", "start_image_url", "first_frame_url", "image"],
  fetch: async function () { return { ok: true, json: async function () { return { items: [] }; } }; },
  ComposerFieldAdapt: { applyToSurface: function (ctx) { applyLog.push("adapt:" + ((ctx.item && ctx.item.id) || "")); } },
};
sandbox.window = sandbox;

vm.createContext(sandbox);
vm.runInContext(extracted + "\nthis.SMART_PREF = SMART_PREF; this.serviceFitsOp = serviceFitsOp; this.pickSmartServiceId = pickSmartServiceId; this.smartMatchService = smartMatchService; this.injectCatalogRow = injectCatalogRow; this.pinMsLoraServiceId = pinMsLoraServiceId; this.pinHfLoraServiceId = pinHfLoraServiceId; this.catalogEatsRefs = catalogEatsRefs; this.writeSmartMatchToShot = writeSmartMatchToShot;", sandbox);

function seed(be, rows) {
  els.backend.value = be;
  state.catalogById = {};
  state.catalog = [];
  state._catalogRoster = [];
  state.edges = [];
  state.mode = "image";
  state.nodes[0].backend = be;
  state.nodes[0].composer.backend = be;
  state.nodes[0].serviceId = "";
  els.service.value = "";
  els.msg.textContent = "";
  rows.forEach(function (row) {
    row.backend = be;
    sandbox.injectCatalogRow(row);
  });
}

const FIX = {
  civitai: [
    { id: "image/comfy/krea2/turbo/createImage", operation: "createImage", category: "image", task: "text-to-image", tags: ["t2i"] },
    { id: "image/flux2/klein/editImage/9b", operation: "editImage", category: "image", task: "image-to-image", tags: ["i2i"], needsSource: true },
    { id: "video/minimax-h3-comfy/imageToVideo", operation: "imageToVideo", category: "video", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, supportsI2v: true },
  ],
  fal: [
    { id: "fal-ai/flux/schnell", category: "image", task: "text-to-image", tags: ["t2i"] },
    { id: "fal-ai/flux-pro/kontext", category: "image", falCategory: "image-to-image", needsSource: true, task: "image-to-image", tags: ["i2i"] },
    { id: "fal-ai/minimax/video-01/image-to-video", category: "video", needsFirstFrame: true, supportsI2v: true, task: "image-to-video", tags: ["i2v"] },
  ],
  huggingface: [
    { id: "krea/Krea-2-Turbo", task: "text-to-image", tags: ["t2i"], category: "image" },
    { id: "Qwen/Qwen-Image-Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, category: "image" },
    { id: "Wan-AI/Wan2.2-TI2V-5B", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, category: "video" },
  ],
  "modelscope-ai": [
    { id: "krea/Krea-2-Turbo", task: "text-to-image", tags: ["t2i"], category: "image" },
    { id: "Qwen/Qwen-Image-Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, category: "image" },
  ],
  "modelscope-cn": [
    { id: "krea/Krea-2-Turbo", task: "text-to-image", tags: ["t2i"], category: "image" },
    { id: "MusePublic/Qwen-Image-Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, category: "image" },
  ],
  "nano-gpt": [
    { id: "z-image-turbo", task: "text-to-image", tags: ["t2i"], category: "image", backend: "nano-gpt" },
    { id: "z-image-turbo-image-to-image", task: "image-to-image", tags: ["i2i"], needsSource: true, category: "image" },
    { id: "minimax/h3-max/multi-angle/image-to-video", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, category: "video" },
  ],
};

async function main() {
  const houses = Object.keys(FIX);
  const fail = [];
  for (const be of houses) {
    seed(be, FIX[be]);
    applyLog.length = 0;
    const t2i = await sandbox.smartMatchService({ op: "t2i" });
    if (!t2i || !sandbox.serviceFitsOp(state.catalogById[t2i], "t2i")) fail.push(be + " t2i=" + t2i);
    if (applyLog.indexOf(t2i) < 0 && applyLog.join(",").indexOf(t2i) < 0) fail.push(be + " adapt-miss-t2i");

    state.edges = [{ from: "asset-1", to: "shot-1" }];
    const i2i = await sandbox.smartMatchService({ op: "i2i" });
    if (!i2i || !sandbox.serviceFitsOp(state.catalogById[i2i], "i2i")) fail.push(be + " i2i=" + i2i);

    state.mode = "video";
    state.edges = [];
    const i2v = await sandbox.smartMatchService({ op: "i2v" });
    if (be === "modelscope-ai" || be === "modelscope-cn") {
      if (i2v) fail.push(be + " i2v should miss without Wan row, got " + i2v);
      if (String(els.msg.textContent).indexOf("没有可匹配") < 0) fail.push(be + " i2v msg=" + els.msg.textContent);
      if (els.service.value === "krea/Krea-2-Turbo") fail.push(be + " leftover turbo");
    } else {
      if (!i2v || !sandbox.serviceFitsOp(state.catalogById[i2v], "i2v")) fail.push(be + " i2v=" + i2v);
    }
  }
  const dropped = sandbox.pinMsLoraServiceId("krea/Krea-2-Turbo", "i2v");
  if (dropped === "krea/Krea-2-Turbo") fail.push("pinMs leftover turbo");
  const eats = sandbox.catalogEatsRefs({ id: "Wan-AI/Wan2.2-TI2V-5B", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, category: "video" });
  if (!eats) fail.push("catalogEatsRefs i2v false");

  if (fail.length) {
    console.error("FAIL\n" + fail.join("\n"));
    process.exit(1);
  }
  console.log("PASS o82 cap-adapt 6-house t2i/i2i + honest magao i2v + adapt hook");
}
main().catch(function (e) { console.error(e); process.exit(1); });
