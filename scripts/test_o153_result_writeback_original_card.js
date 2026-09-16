#!/usr/bin/env node
/** o153: generated /out writes to original shot card; import still cannot mask it; hydrate keeps /out; afterSrc from DOM. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

assert.ok(js.includes("v0821o153-result-writeback-original-card"), "js stamp");
assert.ok(
  html.includes("v0821o153-result-writeback-original-card") || html.includes("o153writeback"),
  "html stamp"
);
assert.ok(/storyboard\.js\?v=o153bcardpixels/.test(html) || /storyboard\.js\?v=o153writeback/.test(html), "cache bust o153bcardpixels or o153writeback");
assert.ok(js.includes("cardMediaSrcFromDom"), "afterSrc from real card DOM helper");
assert.ok(js.includes("patchShotCardMediaDom"), "immediate DOM patch");
assert.ok(js.includes("importSourceUrl"), "import reference field");
assert.ok(js.includes("localOut && !serverOut"), "hydrate keeps local /out over import CDN");
assert.ok(/import still = source\/reference metadata only/.test(js), "import not shot.url");
assert.ok(js.includes("patchShotCardMediaDom(live.id, cleanUrl"), "writeback patches DOM after renderCards");
assert.ok(/faceSrc = \(typeof displayMediaSrc/.test(js), "cardHTML uses displayMediaSrc");

const IMPORT =
  "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/85a7671c-82f4-4024-9758-06584a49d3c5/original=true/floral.jpeg";
const JOB = "/out/12100372-20260916150219332_0.jpg";

// --- minimal DOM mock (no jsdom) ---
function makeDom() {
  const cards = new Map();
  const world = {
    querySelector(sel) {
      const m = String(sel).match(/\.card\.shot\[data-id="([^"]+)"\]/);
      if (m) return cards.get(m[1]) || null;
      return null;
    },
    querySelectorAll() {
      return [];
    },
    _cards: cards,
  };
  function makeMedia(tag, src) {
    const m = {
      tagName: String(tag || "IMG").toUpperCase(),
      src: src || "",
      currentSrc: src || "",
      alt: "",
      dataset: {},
      getAttribute(k) {
        return k === "src" ? this.src : null;
      },
      removeAttribute(k) {
        if (k === "src") {
          this.src = "";
          this.currentSrc = "";
        }
      },
      setAttribute() {},
      decode() {
        return Promise.resolve();
      },
    };
    return m;
  }
  function ensureCard(id, src) {
    let card = cards.get(id);
    if (!card) {
      let media = makeMedia("IMG", src || "");
      const face = {
        style: { backgroundImage: "", background: "" },
        _media: null,
        querySelector(s) {
          if (/img|video/i.test(s)) return this._media;
          return null;
        },
        get innerHTML() {
          return this._media ? "<media>" : "";
        },
        set innerHTML(v) {
          if (v === "") this._media = null;
        },
        appendChild(el) {
          this._media = el;
        },
      };
      face._media = media;
      card = {
        dataset: { id },
        classList: { remove() {}, add() {} },
        setAttribute() {},
        querySelector(s) {
          if (s === ".face") return face;
          if (/img|video/i.test(s)) return face._media;
          return null;
        },
        get _media() {
          return face._media;
        },
        set _media(v) {
          face._media = v;
        },
        _face: face,
      };
      // sync getter via redefine
      Object.defineProperty(card, "_media", {
        get() {
          return face._media;
        },
        set(v) {
          face._media = v;
        },
      });
      cards.set(id, card);
    }
    if (src != null) {
      if (!card._face._media) card._face._media = makeMedia("IMG", src);
      card._face._media.src = src;
      card._face._media.currentSrc = src;
    }
    return card;
  }
  return { world, ensureCard, cards };
}

const { world, ensureCard } = makeDom();

const state = {
  nodes: [
    {
      id: "shot-1lirpr",
      kind: "shot",
      title: "分镜1",
      x: 100,
      y: 100,
      url: "",
      prompt: "singing with mic",
    },
  ],
  edges: [],
  history: [],
  selected: "shot-1lirpr",
  multi: [],
  groups: [],
  mode: "image",
};

function nodeById(id) {
  return state.nodes.find((n) => n && n.id === id);
}

const sandbox = {
  state,
  world,
  document: {
    createElement(tag) {
      const el = {
        tagName: String(tag).toUpperCase(),
        setAttribute() {},
        src: "",
        currentSrc: "",
        alt: "",
        dataset: {},
        getAttribute(k) {
          return k === "src" ? this.src : null;
        },
        removeAttribute(k) {
          if (k === "src") {
            this.src = "";
            this.currentSrc = "";
          }
        },
        decode() {
          return Promise.resolve();
        },
      };
      return el;
    },
  },
  requestAnimationFrame(cb) {
    return setTimeout(cb, 0);
  },
  setTimeout,
  Date,
  Number,
  String,
  Array,
  Object,
  JSON,
  console,
  nodeById,
  isVideoUrl(u) {
    return /\.(mp4|webm|mov)(\?|$)/i.test(u || "");
  },
  uid(prefix) {
    return prefix + "-test";
  },
  connectedAssets() {
    return [];
  },
  unlinkAssetFromShot() {},
  linkAssetToShot() {},
  removeUnpromotedFromShot() {},
  frameAsset() {
    return null;
  },
  pushHistoryItem(url, title) {
    state.history.unshift({ url, title });
  },
  renderRail() {},
  renderChatRail() {},
  renderDock() {},
  drawWires() {},
  persist() {},
  persistServer() {},
  persistActiveCanvas() {},
  clearPendingJob() {},
  renderCards() {
    const n = nodeById("shot-1lirpr");
    const src =
      typeof sandbox.displayMediaSrc === "function"
        ? sandbox.displayMediaSrc(n.url, n._urlUpdatedAt || n.urlUpdatedAt)
        : n.url;
    ensureCard(n.id, src || "");
  },
  shots() {
    return state.nodes.filter((n) => n && n.kind === "shot");
  },
  shotsHaveMedia() {
    return state.nodes.some((n) => n && n.kind === "shot" && String(n.url || "").trim());
  },
  isMainHouseGraph() {
    return false;
  },
  applyGraph() {
    return false;
  },
  _canvasAdopted: true,
  fetch: async () => ({ ok: true, json: async () => ({ graph: { nodes: [] } }) }),
};

const importStillStart = js.indexOf("  function importStillUrl(j) {");
const importStillEnd = js.indexOf("  /** Mount import still", importStillStart);
const mountStart = js.indexOf("  function mountImportStillOnShot(j, shot, op) {");
const mountEnd = js.indexOf("  function ensureActiveShotForImport()", mountStart);
const wbStart = js.indexOf("  function writebackResult(shot, url) {");
const wbEnd = js.indexOf("  function pickSavedUrl(data) {", wbStart);
const hydrateStart = js.indexOf("  function shotUrlMtime(n) {");
const hydrateEnd = js.indexOf("  function applyCam()", hydrateStart);

assert.ok(importStillStart >= 0 && mountStart > importStillStart, "import/mount seams");
assert.ok(wbStart >= 0 && wbEnd > wbStart, "writeback seam");
assert.ok(hydrateStart >= 0 && hydrateEnd > hydrateStart, "hydrate seam");

vm.createContext(sandbox);
vm.runInContext(
  js.slice(importStillStart, importStillEnd) +
    "\n" +
    js.slice(mountStart, mountEnd) +
    "\n" +
    js.slice(wbStart, wbEnd) +
    "\n" +
    js.slice(hydrateStart, hydrateEnd) +
    "\nglobalThis.writebackResult = writebackResult;" +
    "\nglobalThis.mountImportStillOnShot = mountImportStillOnShot;" +
    "\nglobalThis.cardMediaSrcFromDom = cardMediaSrcFromDom;" +
    "\nglobalThis.displayMediaSrc = displayMediaSrc;" +
    "\nglobalThis.hydrateFromServer = hydrateFromServer;" +
    "\nglobalThis.importStillUrl = importStillUrl;",
  sandbox
);

async function main() {
  const {
    writebackResult,
    mountImportStillOnShot,
    cardMediaSrcFromDom,
    displayMediaSrc,
    hydrateFromServer,
  } = sandbox;
  sandbox.displayMediaSrc = displayMediaSrc;

  const shot = nodeById("shot-1lirpr");

  // 1) Import = reference only — must not become card face
  const asset = mountImportStillOnShot(
    { mediaUrl: IMPORT, kind: "image", prompt: "floral shirt" },
    shot,
    "t2i"
  );
  assert.ok(asset && asset.url === IMPORT, "import asset mounted");
  assert.equal(shot.importSourceUrl, IMPORT, "importSourceUrl recorded");
  assert.equal(String(shot.url || ""), "", "t2i import must not set shot.url");
  sandbox.renderCards();
  assert.equal(cardMediaSrcFromDom(shot.id), "", "DOM empty before gen (afterSrc from DOM)");

  // 2) Immediate writeback → card src = /out/<job>_0.jpg and differs from import
  writebackResult(shot, JOB);
  assert.equal(shot.url, JOB, "shot.url is generated /out");
  assert.notEqual(shot.url, IMPORT, "generated differs from import");
  assert.equal(shot.importSourceUrl, IMPORT, "import stays reference metadata");
  const afterSrc = cardMediaSrcFromDom(shot.id);
  assert.ok(
    afterSrc.includes("12100372-20260916150219332_0.jpg"),
    "immediate card afterSrc is /out job file, got: " + afterSrc
  );
  assert.ok(!/civitai\.com|floral/i.test(afterSrc), "afterSrc is not import CDN");
  assert.notEqual(afterSrc, IMPORT, "afterSrc differs from import");

  // 3) Import must not win after generation
  mountImportStillOnShot({ mediaUrl: IMPORT, kind: "image" }, shot, "t2i");
  assert.equal(shot.url, JOB, "re-import does not clobber /out");
  writebackResult(shot, IMPORT);
  assert.equal(shot.url, JOB, "writeback of import CDN no-ops when importSourceUrl matches");

  // 4) Hydrate keeps /out even if server offers fresher import CDN
  shot.url = JOB;
  shot._urlUpdatedAt = 1000;
  sandbox.fetch = async () => ({
    ok: true,
    json: async () => ({
      graph: {
        nodes: [{ id: "shot-1lirpr", kind: "shot", url: IMPORT, _urlUpdatedAt: 999999 }],
      },
    }),
  });
  vm.runInContext(js.slice(hydrateStart, hydrateEnd) + "\nglobalThis.hydrateFromServer = hydrateFromServer;", sandbox);
  await sandbox.hydrateFromServer();
  assert.equal(shot.url, JOB, "hydrate preserves generated /out over import CDN");

  // 5) Refresh hydrate adopts /out onto empty shot and DOM shows it
  shot.url = "";
  delete shot._urlUpdatedAt;
  sandbox.fetch = async () => ({
    ok: true,
    json: async () => ({
      graph: {
        nodes: [{ id: "shot-1lirpr", kind: "shot", url: JOB, _urlUpdatedAt: Date.now() }],
      },
    }),
  });
  vm.runInContext(js.slice(hydrateStart, hydrateEnd) + "\nglobalThis.hydrateFromServer = hydrateFromServer;", sandbox);
  await sandbox.hydrateFromServer();
  assert.equal(shot.url, JOB, "hydrate adopts server /out");
  sandbox.renderCards();
  assert.ok(
    cardMediaSrcFromDom(shot.id).includes("12100372-20260916150219332_0.jpg"),
    "refresh hydrate DOM preserves generated URL"
  );

  assert.ok(displayMediaSrc(JOB, 42).includes("_wb=42"), "display cache-bust");
  assert.equal(displayMediaSrc(IMPORT, 42), IMPORT, "non-/out not busted");

  console.log("PASS o153_result_writeback_original_card");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
