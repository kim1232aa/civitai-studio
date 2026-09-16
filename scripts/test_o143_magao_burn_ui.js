#!/usr/bin/env node
/** o143: Magao burn UI P0 — LoRA unknown+chips, t2i unused refs, orphan empty shells, import still, Hub warn in LoRA hint. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const o68 = fs.readFileSync(path.join(root, "static/o68-capability-hide.js"), "utf8");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");
const o134 = fs.readFileSync(path.join(root, "static/o134-lora-remap-hook.js"), "utf8");
const css = fs.readFileSync(path.join(root, "static/storyboard-ui.css"), "utf8");

assert.ok(js.includes("v0821o143-magao-burn-ui"), "js stamp");
// html stamp/cache may advance (o144+); o143 contracts live in js/o68/css
assert.ok(
  html.includes("v0821o143-magao-burn-ui") || html.includes("v0821o144-adv-default-open") || html.includes("v0821o145-smart-match"),
  "html stamp o143 or successor"
);
assert.ok(
  /storyboard\.js\?v=o143burn|storyboard\.js\?v=o144adv|storyboard\.js\?v=o145match/.test(html),
  "cache bust o143 or successor"
);
assert.ok(
  /o68-capability-hide\.js\?v=o143|o68-capability-hide\.js\?v=o144/.test(html),
  "cache bust o68 o143 or successor"
);
assert.ok(o68.includes("未知是否加载"), "o68 honest unknown+chips copy");
assert.ok(o68.includes("hasChips"), "o68 checks chips");
assert.ok(o68.includes("v0821o143-o68-lora-unknown-chips"), "o68 stamp");

assert.ok(js.includes("drivingChips"), "t2i drivingChips split");
assert.ok(js.includes("ref-unused"), "unused ref class");
assert.ok(js.includes("isOrphanEmptyShotShell"), "orphan empty helper");
assert.ok(js.includes("mountImportStillOnShot"), "import still mount");
assert.ok(js.includes("importStillUrl"), "importStillUrl");
assert.ok(css.includes("ref-unused"), "css demotes unused refs");

assert.ok(o134.includes("Do not stamp #msg"), "Hub warn not canvas sticker");
assert.ok(o134.includes("loraHint"), "Hub warn stays on loraHint");
assert.ok(!/msg\.textContent = blocked\[0\]\.chipReason/.test(o134), "no chipReason → #msg");

// --- o68 unit: unknown+chips → 未知是否加载; unknown alone → 未知; true/false unchanged ---
const code = `
function hide(el) { if (el) { el._hidden = true; el.classList && el.classList.add("hidden"); } }
function show(el) { if (el) { el._hidden = false; el.classList && el.classList.remove("hidden"); if (el.style) el.style.display = ""; } }
function run(supportsLora, be, chips) {
  be = be || "modelscope-ai";
  var item = { id: "Tongyi-MAI/Z-Image-Turbo", capabilities: {} };
  if (supportsLora !== undefined) item.capabilities.supportsLora = supportsLora;
  var caps = item.capabilities;
  var supports = caps.supportsLora;
  if (supports == null) supports = item.supportsLora;
  var unknownLora = (supports !== true && supports !== false);
  var hasModel = true;
  var hasChips = !!chips;
  var showLora = (be === "civitai" && hasModel)
    || (hasModel && supports === true)
    || (hasModel && be !== "civitai" && unknownLora)
    || hasChips;
  var loraBlock = { classList: { _s: new Set(), add: function(c){this._s.add(c)}, remove: function(c){this._s.delete(c)}, contains: function(c){return this._s.has(c)} }, style:{} };
  var hint = { textContent: "" };
  if (showLora) {
    show(loraBlock);
    loraBlock.classList.remove("param-lora-off");
    if (unknownLora && be !== "civitai") {
      loraBlock.classList.add("param-unknown");
      hint.textContent = hasChips ? "未知是否加载" : "未知";
    } else loraBlock.classList.remove("param-unknown");
  } else {
    hide(loraBlock);
    loraBlock.classList.add("param-lora-off");
    loraBlock.classList.remove("param-unknown");
  }
  return { show: !loraBlock._hidden, hint: hint.textContent, unknownCls: loraBlock.classList.contains("param-unknown"), off: loraBlock.classList.contains("param-lora-off") };
}
var results = {
  unknownNoChip: run(undefined, "modelscope-ai", false),
  unknownChips: run(undefined, "modelscope-ai", true),
  trueChips: run(true, "modelscope-ai", true),
  falseChips: run(false, "modelscope-ai", true),
  falseNoChip: run(false, "modelscope-ai", false)
};
results;
`;
const r = vm.runInNewContext(code, {}, { timeout: 2000 });
assert.equal(r.unknownNoChip.show, true, "unknown no-chip shows");
assert.equal(r.unknownNoChip.hint, "未知", "unknown no-chip keeps 未知 (o141)");
assert.equal(r.unknownChips.show, true, "unknown+chips shows");
assert.equal(r.unknownChips.hint, "未知是否加载", "unknown+chips honest label");
assert.notEqual(r.unknownChips.hint, "未知", "must not bare 未知 with chips");
assert.equal(r.trueChips.hint, "", "supported+chips no unknown label");
assert.equal(r.falseChips.show, true, "false+chips still show (o54 never silent-drop)");
assert.equal(r.falseNoChip.show, false, "false no-chip hides");

// --- storyboard string contracts for t2i / orphan / import ---
assert.ok(/const drivingChips = eats \? linked : \[\]/.test(js), "drivingChips = eats ? linked");
assert.ok(/unusedLinked\.map/.test(js), "unused linked demoted map");
assert.ok(/文生图不发送/.test(js), "unused title copy");
assert.ok(/if \(n\.kind === "shot" && isOrphanEmptyShotShell\(n\)\) return;/.test(js), "skip orphan in renderCards");
assert.ok(/mediaUrl \|\| j\.url \|\| j\.imageUrl/.test(js), "importStillUrl fields");
assert.ok(/opMount = \(famInfo && famInfo\.op\)/.test(js), "applyImport calls mount with op");

// orphan helper logic mirror
const orphanCode = `
function shots() { return state.nodes.filter(function(n){ return n.kind === "shot"; }); }
function isOrphanEmptyShotShell(n) {
  if (!n || n.kind !== "shot") return false;
  if (n.url || n._busy || n._error) return false;
  if (String(n.prompt || "").trim()) return false;
  if (String(n.firstFrameId || "").trim()) return false;
  var composeId = state.lastComposerShot || null;
  if (n.id === composeId || n.id === state.selected) return false;
  if (state.editor && state.editor.activeShotId === n.id) return false;
  var shotList = shots();
  if (shotList.length <= 1) return false;
  return true;
}
var state = {
  lastComposerShot: "shot-1",
  selected: "shot-1",
  editor: { activeShotId: "shot-1" },
  nodes: [
    { id: "shot-1", kind: "shot", title: "分镜1", url: "/out/a.png", prompt: "sitting girl" },
    { id: "shot-empty-a", kind: "shot", title: "空", url: "", prompt: "" },
    { id: "shot-empty-b", kind: "shot", title: "空2", url: "", prompt: "" },
    { id: "asset-vase", kind: "asset", url: "/out/vase.png" }
  ]
};
({
  active: isOrphanEmptyShotShell(state.nodes[0]),
  orphanA: isOrphanEmptyShotShell(state.nodes[1]),
  orphanB: isOrphanEmptyShotShell(state.nodes[2]),
  asset: isOrphanEmptyShotShell(state.nodes[3]),
  sole: (function(){
    state.nodes = [{ id: "shot-1", kind: "shot", title: "分镜1", url: "", prompt: "" }];
    state.lastComposerShot = "shot-1";
    return isOrphanEmptyShotShell(state.nodes[0]);
  })()
});
`;
const o = vm.runInNewContext(orphanCode, {}, { timeout: 2000 });
assert.equal(o.active, false, "active painted shot not orphan");
assert.equal(o.orphanA, true, "empty mid-row orphan");
assert.equal(o.orphanB, true, "second empty orphan");
assert.equal(o.asset, false, "asset not shot orphan");
assert.equal(o.sole, false, "sole empty intentional");

// import still: t2i unlinks leftovers, does not link; i2i links
const mountCode = `
var edges = [];
var nodes = [];
function uid(p){ return p + "-1"; }
function connectedAssets(shotId) {
  return edges.filter(function(e){ return e.to === shotId; }).map(function(e){
    return nodes.find(function(n){ return n.id === e.from; });
  }).filter(Boolean);
}
function unlinkAssetFromShot(a, shot) {
  edges = edges.filter(function(e){ return !(e.from === a.id && e.to === shot.id); });
}
function linkAssetToShot(a, shot) {
  if (!edges.some(function(e){ return e.from === a.id && e.to === shot.id; }))
    edges.push({ from: a.id, to: shot.id });
  return true;
}
function importStillUrl(j) {
  j = j || {};
  return String(j.mediaUrl || j.url || j.imageUrl || j.previewUrl || j.sourceUrl || "").trim();
}
function mountImportStillOnShot(j, shot, op) {
  if (!shot || shot.kind !== "shot") return null;
  var url = importStillUrl(j);
  var keepUrl = url || "";
  connectedAssets(shot.id).slice().forEach(function (a) {
    if (keepUrl && a && a.url === keepUrl) return;
    unlinkAssetFromShot(a, shot);
  });
  if (!url) return null;
  if (!/^https?:\\/\\//i.test(url) && url.indexOf("/out/") !== 0 && url.indexOf("data:") !== 0) return null;
  var asset = nodes.find(function (n) {
    return n && n.kind !== "shot" && n.kind !== "text" && n.url === url;
  });
  if (!asset) {
    asset = { id: uid("import-still"), kind: "asset", title: "导入原图", url: url, source: "import" };
    nodes.push(asset);
  }
  var wantsRef = (op === "i2i" || op === "i2v" || j.kind === "video");
  if (wantsRef) linkAssetToShot(asset, shot);
  return asset;
}
var shot = { id: "shot-1", kind: "shot", prompt: "sitting girl" };
var vase = { id: "vase", kind: "asset", url: "/out/vase.png" };
nodes.push(shot, vase);
edges.push({ from: "vase", to: "shot-1" });
var still = "https://image.civitai.com/x/abc/original=true/abc.jpeg";
var a1 = mountImportStillOnShot({ mediaUrl: still, kind: "image", prompt: "sitting" }, shot, "t2i");
var t2iLinked = connectedAssets("shot-1").map(function(x){ return x.id; });
var a2 = mountImportStillOnShot({ mediaUrl: still, kind: "image" }, shot, "i2i");
var i2iLinked = connectedAssets("shot-1").map(function(x){ return x.id; });
({
  t2iAsset: !!(a1 && a1.url === still),
  t2iNoLink: t2iLinked.length === 0,
  vaseCleared: !t2iLinked.includes("vase"),
  i2iLinked: i2iLinked.includes(a2.id),
  stillUrl: importStillUrl({ mediaUrl: still })
});
`;
const m = vm.runInNewContext(mountCode, {}, { timeout: 2000 });
assert.equal(m.stillUrl.startsWith("https://"), true, "mediaUrl extracted");
assert.equal(m.t2iAsset, true, "t2i creates still asset");
assert.equal(m.t2iNoLink, true, "t2i does not link as driving ref");
assert.equal(m.vaseCleared, true, "t2i clears unrelated leftover ref");
assert.equal(m.i2iLinked, true, "i2i links still on same shot");

console.log("PASS o143_magao_burn_ui");
