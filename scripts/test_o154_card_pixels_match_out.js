#!/usr/bin/env node
/** o154: paint card face from /out blob ObjectURL + decode so visible pixels match out file. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "static/storyboard.js"), "utf8");
const html = fs.readFileSync(path.join(root, "static/storyboard.html"), "utf8");

// --- stamps ---
assert.ok(js.includes("v0821o154-card-pixels-match-out"), "js stamp o154");
assert.ok(
  html.includes("v0821o154-card-pixels-match-out") || html.includes("o154cardpixels"),
  "html stamp o154"
);
assert.ok(/storyboard\.js\?v=/.test(html), "cache bust present");
assert.ok(html.includes("o154cardpixels") || /storyboard\.js\?v=o154cardpixels/.test(html), "html lineage o154cardpixels");

// --- patchShotCardMediaDom fetch+blob+decode ---
const patchStart = js.indexOf("function patchShotCardMediaDom(");
assert.ok(patchStart >= 0, "patchShotCardMediaDom exists");
const patchEnd = js.indexOf("\n  function cardMediaSrcFromDom", patchStart);
assert.ok(patchEnd > patchStart, "patch body bounded");
const patchBody = js.slice(patchStart, patchEnd);

assert.ok(/\bfetch\s*\(/.test(patchBody), "patch fetch() /out bytes");
assert.ok(/createObjectURL/.test(patchBody), "patch createObjectURL blob");
assert.ok(/revokeObjectURL/.test(patchBody), "patch revokeObjectURL previous blob");
assert.ok(/_faceBlobUrl/.test(patchBody), "stores blob URL on shot._faceBlobUrl");
assert.ok(/\.decode\s*\(/.test(patchBody), "await img.decode() path");
assert.ok(/blob:/.test(patchBody) || /blobUrl/.test(patchBody), "blob URL paint path");
assert.ok(/backgroundImage\s*=\s*["']["']/.test(patchBody), "patch clears backgroundImage");
assert.ok(/face\.innerHTML\s*=\s*["']["']/.test(patchBody), "patch clears face.innerHTML");
assert.ok(/dataset\.faceUrl/.test(patchBody), "patch sets dataset.faceUrl");
assert.ok(/data-face-url/.test(patchBody), "patch sets data-face-url attr");
assert.ok(/_wb=/.test(patchBody) || /displayMediaSrc/.test(patchBody), "sync fallback /out?_wb= before blob");

// --- cardMediaSrcFromDom prefers dataset.faceUrl over blob: ---
const readStart = js.indexOf("function cardMediaSrcFromDom(");
assert.ok(readStart >= 0, "cardMediaSrcFromDom exists");
const readEnd = js.indexOf("\n  function pickSavedUrl", readStart);
const readBody = js.slice(readStart, readEnd);
assert.ok(/dataset\.faceUrl/.test(readBody), "reader checks dataset.faceUrl");
assert.ok(/blob:/.test(readBody), "reader ignores blob: currentSrc");
assert.ok(/data-face-url/.test(readBody), "reader checks data-face-url");

// --- cardHTML never paints importSourceUrl into face ---
const cardStart = js.indexOf("function cardHTML(n)");
const cardShot = js.indexOf('if (n.kind === "shot")', cardStart);
const cardBody = js.slice(cardShot, cardShot + 900);
assert.ok(/displayMediaSrc\(n\.url/.test(cardBody), "cardHTML face uses n.url via displayMediaSrc");
assert.ok(!/displayMediaSrc\(\s*n\.importSourceUrl/.test(cardBody), "cardHTML must not paint importSourceUrl");
assert.ok(/NEVER importSourceUrl/.test(js), "cardHTML comment forbids importSourceUrl");
assert.ok(/data-face-url/.test(cardBody), "cardHTML stamps data-face-url from n.url");

// --- o153b re-patch kept ---
assert.ok(/requestAnimationFrame/.test(js), "keeps rAF re-patch");
assert.ok(/setTimeout\([\s\S]*?,\s*50\s*\)/.test(js), "keeps setTimeout(50) re-patch");

const JOB = "/out/12100372-20260916154529603_0.jpg";

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
  };
  function makeMedia(tag, src) {
    const attrs = {};
    return {
      tagName: String(tag || "IMG").toUpperCase(),
      src: src || "",
      currentSrc: src || "",
      alt: "",
      dataset: {},
      complete: true,
      getAttribute(k) {
        if (k === "src") return this.src;
        if (k === "data-face-url") return this.dataset.faceUrl || attrs["data-face-url"] || null;
        return attrs[k] || null;
      },
      setAttribute(k, v) {
        attrs[k] = v;
        if (k === "data-face-url") this.dataset.faceUrl = v;
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
  }
  function ensureCard(id, src) {
    let card = cards.get(id);
    if (!card) {
      const face = {
        style: { backgroundImage: "url(import)", background: "url(import)" },
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
      const attrs = {};
      card = {
        dataset: { id },
        classList: { remove() {}, add() {} },
        setAttribute(k, v) {
          attrs[k] = v;
          if (k === "data-face-url") this.dataset.faceUrl = v;
        },
        getAttribute(k) {
          if (k === "data-face-url") return this.dataset.faceUrl || attrs[k] || null;
          return attrs[k] || null;
        },
        querySelector(s) {
          if (s === ".face") return face;
          if (/img|video/i.test(s)) return face._media;
          return null;
        },
        _face: face,
      };
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
  nodes: [{ id: "shot-1", kind: "shot", title: "分镜1", url: JOB, _urlUpdatedAt: 1 }],
};
function nodeById(id) {
  return state.nodes.find((n) => n && n.id === id);
}

const sandbox = {
  state,
  world,
  document: {
    createElement(tag) {
      const attrs = {};
      return {
        tagName: String(tag).toUpperCase(),
        setAttribute(k, v) {
          attrs[k] = v;
          if (k === "data-face-url") this.dataset.faceUrl = v;
        },
        src: "",
        currentSrc: "",
        alt: "",
        dataset: {},
        complete: true,
        getAttribute(k) {
          if (k === "src") return this.src;
          if (k === "data-face-url") return this.dataset.faceUrl || attrs[k] || null;
          return attrs[k] || null;
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
    },
  },
  nodeById,
  isVideoUrl(u) {
    return /\.(mp4|webm|mov)(\?|$)/i.test(u || "");
  },
  fetch: async (url) => ({
    ok: true,
    blob: async () => ({ size: 64, type: "image/jpeg", from: String(url) }),
  }),
  URL: {
    createObjectURL(blob) {
      assert.ok(blob && blob.size > 0, "createObjectURL from non-empty blob");
      return "blob:http://local/o154-out-bytes";
    },
    revokeObjectURL() {},
  },
  Date,
  Number,
  String,
  Array,
  Object,
  JSON,
  console,
  Promise,
};

const fnStart = js.indexOf("  function isStudioOutUrl(url) {");
const fnEnd = js.indexOf("  function pickSavedUrl(data) {", fnStart);
assert.ok(fnStart >= 0 && fnEnd > fnStart, "helper slice");

vm.createContext(sandbox);
vm.runInContext(
  js.slice(fnStart, fnEnd) +
    "\nglobalThis.patchShotCardMediaDom = patchShotCardMediaDom;" +
    "\nglobalThis.cardMediaSrcFromDom = cardMediaSrcFromDom;" +
    "\nglobalThis.displayMediaSrc = displayMediaSrc;" +
    "\nglobalThis.isStudioOutUrl = isStudioOutUrl;" +
    "\nglobalThis.studioOutPath = studioOutPath;",
  sandbox
);

async function main() {
  const { patchShotCardMediaDom, cardMediaSrcFromDom } = sandbox;

  // A) reader: blob: src + dataset.faceUrl → clean /out
  const card = ensureCard("shot-1", "blob:http://local/old-import");
  card.dataset.faceUrl = JOB;
  card._media.src = "blob:http://local/old-import";
  card._media.currentSrc = "blob:http://local/old-import";
  card._media.dataset.faceUrl = JOB;
  const fromDs = cardMediaSrcFromDom("shot-1");
  assert.equal(fromDs, JOB, "cardMediaSrcFromDom returns clean /out even if img.src is blob:, got: " + fromDs);
  assert.ok(!fromDs.startsWith("blob:"), "reader must not report blob:");

  // B) patch fetches /out, paints blob, decode, stamps faceUrl
  card._media.src = "https://image.civitai.com/import.jpg";
  card._media.currentSrc = "https://image.civitai.com/import.jpg";
  delete card.dataset.faceUrl;
  delete card._media.dataset.faceUrl;
  const shot = nodeById("shot-1");
  const ret = patchShotCardMediaDom("shot-1", JOB, 99);
  assert.ok(ret && typeof ret.then === "function", "patch returns Promise for /out blob paint");
  // sync fallback already stamped clean path
  const mid = cardMediaSrcFromDom("shot-1");
  assert.equal(mid, JOB, "sync fallback already reports clean /out via dataset.faceUrl");
  await ret;
  assert.equal(card._media.src, "blob:http://local/o154-out-bytes", "visible img.src is blob from /out bytes");
  assert.equal(cardMediaSrcFromDom("shot-1"), JOB, "after blob paint reader still reports clean /out");
  assert.equal(shot._faceBlobUrl, "blob:http://local/o154-out-bytes", "shot stores _faceBlobUrl");
  assert.equal(card._face.style.backgroundImage, "", "CSS backgroundImage cleared");
  assert.ok(card.dataset.faceUrl === JOB, "card dataset.faceUrl is clean /out");

  // C) re-patch must not wipe decoded blob
  const again = patchShotCardMediaDom("shot-1", JOB, 100);
  assert.equal(again, true, "already-blob re-patch is sync no-op");
  assert.equal(card._media.src, "blob:http://local/o154-out-bytes", "re-patch keeps blob pixels");

  console.log("PASS o154_card_pixels_match_out");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
