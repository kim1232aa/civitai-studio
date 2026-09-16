// o79: 6-house × t2i/i2i/i2v smart match
// Run: node scripts/test_o79_smart_match_six.js
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(/storyboard\.js\?v=o(13[67]|145|147|148)/.test(html) || /storyboard\.js\?v=o148magao/.test(html), "html cache bust o136+/o148");
assert.ok(!source.includes("pageSize: '100'"), "fetchCatalogId must not send pageSize 100");
assert.ok(!source.includes("!serviceId && be !== \"civitai\""), "Fal catch-all gone");
assert.ok(/!serviceId && be === "nano-gpt"/.test(source), "nano-gpt empty branch");

function section(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start + from.length);
  assert.ok(start >= 0 && end > start, "VM seam exists: " + JSON.stringify(from));
  return source.slice(start, end);
}

function seed(state, rows) {
  rows.forEach(function (row) {
    state.catalogById[row.id] = row;
    state.catalog.unshift(row);
    state._catalogRoster.unshift(row);
  });
}

const FIX = {
  civitai: {
    t2i: { id: "image/comfy/krea2/turbo/createImage", name: "Krea2 Turbo", operation: "createImage", category: "image", backend: "civitai" },
    i2i: { id: "image/flux2/klein/editImage/9b", name: "Flux2 Klein Edit", operation: "editImage", category: "image", backend: "civitai" },
    i2v: { id: "video/minimax-h3-comfy/imageToVideo", name: "MiniMax H3", operation: "imageToVideo", category: "video", backend: "civitai" },
  },
  fal: {
    t2i: { id: "fal-ai/flux/schnell", name: "Flux Schnell", backend: "fal", category: "image" },
    i2i: { id: "fal-ai/flux-pro/kontext", name: "Flux Kontext", backend: "fal", falCategory: "image-to-image", needsSource: true, category: "image" },
    i2v: { id: "fal-ai/minimax/video-01/image-to-video", name: "MiniMax I2V", backend: "fal", needsFirstFrame: true, category: "video" },
  },
  huggingface: {
    t2i: { id: "krea/Krea-2-Turbo", name: "Krea 2 Turbo", task: "text-to-image", tags: ["t2i"], backend: "huggingface", category: "image" },
    i2i: { id: "Qwen/Qwen-Image-Edit", name: "Qwen Image Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, backend: "huggingface", category: "image" },
    i2v: { id: "Wan-AI/Wan2.2-TI2V-5B", name: "Wan TI2V", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, backend: "huggingface", category: "video" },
  },
  "modelscope-ai": {
    t2i: { id: "krea/Krea-2-Turbo", name: "Krea 2 Turbo", task: "text-to-image", tags: ["t2i"], backend: "modelscope-ai", category: "image" },
    i2i: { id: "Qwen/Qwen-Image-Edit", name: "Qwen Image Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, backend: "modelscope-ai", category: "image" },
    i2v: { id: "Wan-AI/Wan2.1-I2V-14B-720P", name: "Wan I2V", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, backend: "modelscope-ai", category: "video" },
  },
  "modelscope-cn": {
    t2i: { id: "krea/Krea-2-Turbo", name: "Krea 2 Turbo", task: "text-to-image", tags: ["t2i"], backend: "modelscope-cn", category: "image" },
    i2i: { id: "Qwen/Qwen-Image-Edit", name: "Qwen Image Edit", task: "image-to-image", tags: ["i2i"], needsSource: true, backend: "modelscope-cn", category: "image" },
    i2v: { id: "Wan-AI/Wan2.1-I2V-14B-720P", name: "Wan I2V", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, backend: "modelscope-cn", category: "video" },
  },
  "nano-gpt": {
    t2i: { id: "z-image-turbo", name: "Z-Image Turbo", task: "text-to-image", tags: ["t2i"], backend: "nano-gpt", category: "image" },
    i2i: { id: "z-image-turbo-image-to-image", name: "Z-Image I2I", task: "image-to-image", tags: ["i2i"], needsSource: true, backend: "nano-gpt", category: "image" },
    i2v: { id: "minimax/h3-max/multi-angle/image-to-video", name: "MiniMax H3 I2V", task: "image-to-video", tags: ["i2v"], needsFirstFrame: true, backend: "nano-gpt", category: "video" },
  },
};

function makeSandbox(be) {
  const els = {
    backend: { value: be },
    service: { value: "", options: [] },
    msg: { textContent: "", cls: "" },
  };
  const state = {
    mode: "image",
    nodes: [{ id: "shot-1", kind: "shot", serviceId: "" }],
    edges: [],
    selected: "shot-1",
    catalogById: {},
    catalog: [],
    _catalogRoster: [],
    _serviceItems: [],
    loras: [],
  };
  const sandbox = {
    console,
    URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ items: [] }) }),
    state,
    els,
    $(id) { return els[id] || null; },
    currentBackend() { return els.backend.value; },
    catalogItemForService() {
      const sid = els.service && els.service.value;
      return (sid && state.catalogById[sid]) || null;
    },
    connectedAssets() { return state.edges || []; },
    nodeById(id) { return (state.nodes || []).filter(function (n) { return n.id === id; })[0] || null; },
    setMsg(t) { els.msg.textContent = String(t || ""); },
    ensureSelectOpt(sel, value) {
      if (!sel.options) sel.options = [];
      if (!sel.options.some(function (o) { return o.value === value; })) {
        sel.options.push({ value: String(value), textContent: String(value) });
      }
    },
    syncParamChrome() {},
    renderDock() {},
    catalogImageFields() { return []; },
    SINGULAR_FIRST_FIELDS: [],
    looksCivitaiServiceId(id) {
      const s = String(id || "");
      return /^(image|video|audio|3d|utility)\//.test(s) || /\/comfy\//.test(s);
    },
    looksFalServiceId(id) {
      const s = String(id || "").trim();
      return /^fal-ai\//i.test(s) || /^fal\.ai\//i.test(s);
    },
    hfHasLoras() { return false; },
    MS_LORA_PREF_SERVICE: "krea/Krea-2-Turbo",
    HF_LORA_PREF_SERVICE: "krea/Krea-2-Turbo",
    HF_I2I_PREF_SERVICE: "Qwen/Qwen-Image-Edit",
    FAL_I2V_DEFAULT: "fal-ai/minimax/video-01/image-to-video",
    FAL_T2I_DEFAULT: "fal-ai/flux/schnell",
    CATALOG_PAGE_SIZE: 50,
  };
  vm.createContext(sandbox);
  const code = [
    "function catalogImageFields(){ return []; }",
    section("  const HF_LORA_PREF_SERVICE =", "  const HF_ROUTER_FAL_LORA_MSG ="),
    "const MS_LORA_PREF_SERVICE = 'krea/Krea-2-Turbo';",
    "const CATALOG_PAGE_SIZE = 50;",
    section("  function catalogItemSupportsI2v(", "    // Provider defaults"),
    section("  function rematchCandidatePool(", "  function capacityRematchId("),
    "function pinMsLoraServiceId(sid, op) {\n" +
      "  op = op || (typeof currentGraphOp === 'function' ? currentGraphOp() : 't2i');\n" +
      "  const s = String(sid || '').trim();\n" +
      "  if (op === 'i2i' || op === 'i2v') {\n" +
      "    if (!s || s === MS_LORA_PREF_SERVICE || looksFalServiceId(s) || looksCivitaiServiceId(s)) {\n" +
      "      return (typeof pickSmartServiceId === 'function' && pickSmartServiceId(op)) || '';\n" +
      "    }\n" +
      "    return s;\n" +
      "  }\n" +
      "  if (s && !looksFalServiceId(s) && !looksCivitaiServiceId(s)) return s;\n" +
      "  return MS_LORA_PREF_SERVICE;\n" +
      "}",
  ].join("\n");
  vm.runInContext(code, sandbox, { filename: "o79-smart-match.vm.js" });
  return sandbox;
}

async function runHouse(be) {
  const sb = makeSandbox(be);
  const rows = FIX[be];
  seed(sb.state, Object.values(rows));
  sb.els.service.value = rows.t2i.id;
  sb.state.nodes[0].serviceId = rows.t2i.id;
  sb.state.mode = "image";
  sb.state.edges = [];
  await sb.smartMatchService({ announce: true });
  assert.equal(sb.serviceFitsOp(sb.state.catalogById[sb.els.service.value], "t2i"), true, be + " t2i fits");

  sb.state.edges = [{ from: "asset-1", to: "shot-1" }];
  await sb.smartMatchService({ announce: true });
  assert.ok(sb.els.msg.textContent.indexOf("图生图") >= 0, be + " i2i msg: " + sb.els.msg.textContent);
  assert.equal(sb.els.service.value, rows.i2i.id, be + " i2i id");

  sb.state.edges = [];
  await sb.smartMatchService({ announce: true });
  assert.equal(sb.els.service.value, rows.t2i.id, be + " unlink back to t2i");

  sb.state.mode = "video";
  await sb.smartMatchService({ announce: true });
  assert.ok(sb.els.msg.textContent.indexOf("图生视频") >= 0, be + " i2v msg: " + sb.els.msg.textContent);
  assert.equal(sb.els.service.value, rows.i2v.id, be + " i2v id");
  return sb;
}

(async function main() {
  const houses = ["civitai", "fal", "nano-gpt", "huggingface", "modelscope-ai", "modelscope-cn"];
  for (const be of houses) await runHouse(be);

  const pinSb = makeSandbox("modelscope-ai");
  seed(pinSb.state, Object.values(FIX["modelscope-ai"]));
  assert.notEqual(pinSb.pinMsLoraServiceId("krea/Krea-2-Turbo", "i2v"), "krea/Krea-2-Turbo", "pinMs leftover turbo");

  const inj = makeSandbox("huggingface");
  inj.fetch = async () => ({
    ok: true,
    json: async () => ({
      items: [{
        id: "Qwen/Qwen-Image-Edit",
        name: "Qwen Image Edit",
        task: "image-to-image",
        tags: ["i2i"],
        backend: "huggingface",
        needsSource: true,
        category: "image",
      }],
    }),
  });
  const got = await inj.ensureSmartPrefInPool("i2i");
  assert.equal(got, "Qwen/Qwen-Image-Edit", "inject exact id");
  assert.ok(inj.state.catalogById["Qwen/Qwen-Image-Edit"], "inject landed in catalogById");

  console.log("PASS o79_smart_match_six");
})().catch(function (err) {
  console.error(err);
  process.exit(1);
});
